#!/usr/bin/env python3
"""Recompute every bundle's canonical_content_hash and check it against task.toml.

CONSTRUCTION (unchanged from the original seal, as documented by the now-removed
uuid_provenance.json):

    canonical_content_hash = sha256(
        "\\n".join(f"{relpath}:{sha256_of_file_bytes}"
                   for relpath in sorted(manifest))
    )

The joined text is UTF-8 encoded with no trailing newline; relpath is POSIX-style
and relative to the bundle directory, so the hash is path-independent.

SCOPE — what the manifest covers:
  * every regular file shipped inside the bundle directory, recursively,
  * EXCEPT `trajectories/` in full (run records; evidence about the task, not the
    task itself, and they change every time the grid is re-run),
  * EXCEPT `task.toml` itself (it carries the hash, so including it would make the
    field self-referential and unverifiable),
  * EXCEPT transient artifacts that are never shipped: `__pycache__/`, `*.pyc`,
    `.DS_Store`.

NOT re-derived here: the task id. `[task] id`, the bundle directory name and
`tests/rubrics.json` `task_id` were minted once from the ORIGINAL v1 content hash
and are stable identifiers referenced across the repo and inside run records.
uuid5(namespace, canonical_content_hash) does not equal the task id for the
re-sealed bundles and is not meant to. See the comment in each task.toml.

Usage:
    python3 verify_seal.py [--verbose] [bundle ...]

Exits non-zero if any bundle carrying the field fails to verify. Bundles with no
`[provenance]` table are reported and skipped (they never carried the field).
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    tomllib = None

ROOT = os.path.dirname(os.path.abspath(__file__))
BUNDLE_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

EXCLUDED_DIRS = {"trajectories", "__pycache__"}
EXCLUDED_ROOT_FILES = {"task.toml"}
EXCLUDED_NAMES = {".DS_Store"}
EXCLUDED_SUFFIXES = (".pyc",)

HASH_RE = re.compile(r'^\s*canonical_content_hash\s*=\s*"([0-9a-f]{64})"', re.M)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest(bundle_dir: str) -> list[tuple[str, str]]:
    """The in-scope file set as sorted (relpath, sha256) pairs."""
    entries: list[tuple[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(bundle_dir):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDED_DIRS)
        for name in filenames:
            if name in EXCLUDED_NAMES or name.endswith(EXCLUDED_SUFFIXES):
                continue
            full = os.path.join(dirpath, name)
            if not os.path.isfile(full) or os.path.islink(full):
                continue
            rel = os.path.relpath(full, bundle_dir).replace(os.sep, "/")
            if rel in EXCLUDED_ROOT_FILES:
                continue
            entries.append((rel, sha256_file(full)))
    return sorted(entries)


def canonical(entries: list[tuple[str, str]]) -> str:
    lines = "\n".join(f"{rel}:{digest}" for rel, digest in entries)
    return hashlib.sha256(lines.encode("utf-8")).hexdigest()


def compute(bundle_dir: str) -> tuple[str, list[tuple[str, str]]]:
    entries = manifest(bundle_dir)
    return canonical(entries), entries


def recorded_hash(bundle_dir: str) -> str | None:
    """The canonical_content_hash written in this bundle's task.toml, if any."""
    path = os.path.join(bundle_dir, "task.toml")
    if not os.path.exists(path):
        return None
    if tomllib is not None:
        with open(path, "rb") as fh:
            doc = tomllib.load(fh)
        prov = doc.get("provenance")
        if not isinstance(prov, dict):
            return None
        value = prov.get("canonical_content_hash")
        return value if isinstance(value, str) else None
    with open(path, "r", encoding="utf-8") as fh:  # pragma: no cover
        match = HASH_RE.search(fh.read())
    return match.group(1) if match else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify bundle content seals.")
    ap.add_argument("bundles", nargs="*", help="bundle directories (default: all)")
    ap.add_argument("--verbose", action="store_true", help="list the files covered")
    args = ap.parse_args(argv)

    names = args.bundles or sorted(
        d for d in os.listdir(ROOT)
        if BUNDLE_RE.match(d) and os.path.isdir(os.path.join(ROOT, d))
    )

    rc = 0
    checked = skipped = 0
    for name in names:
        name = name.rstrip("/")
        bundle_dir = os.path.join(ROOT, name)
        want = recorded_hash(bundle_dir)
        if want is None:
            skipped += 1
            print(f"{name[:8]}  SKIP      no [provenance] canonical_content_hash in task.toml")
            continue
        got, entries = compute(bundle_dir)
        checked += 1
        if got == want:
            print(f"{name[:8]}  OK        {len(entries):3d} files  {got}")
        else:
            rc = 1
            print(f"{name[:8]}  MISMATCH  {len(entries):3d} files")
            print(f"          recorded  {want}")
            print(f"          computed  {got}")
        if args.verbose:
            for rel, digest in entries:
                print(f"            {digest[:12]}  {rel}")

    print(f"\n{checked} verified, {skipped} without the field, "
          f"{'all seals valid' if rc == 0 else 'SEAL FAILURES PRESENT'}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
