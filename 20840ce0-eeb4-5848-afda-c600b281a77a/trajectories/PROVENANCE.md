# Provenance — 20840ce0 run records

State of this bundle's measurement evidence, recorded 2026-08-05. This file exists because
the runs carry **no `source` block**, and a reader who did not know that would reasonably
assume their provenance had been checked. It has not been. Everything below separates what
is established from what is not.

`trajectories/` sits outside this bundle's content seal, so this file does not affect any
hash. (This bundle carries no `[provenance]` block at all — see VERDICT item 4.)

## What the records contain

| | |
|---|---|
| Model | `claude-opus-4-8`, single model across both arms |
| Arms | `no-skill` 3 runs, `with-skill` 3 runs |
| `task_digest` | `sha256:8e537ab56382a101d01f108d6fa1fe51f51870bb7cad13d73c721e2f50162f25` |
| Errors | none — no run carries an `error` or `error_category` |
| Run span | 2026-08-04 00:13:14 → 2026-08-04 01:38:45 |

Scores: no-skill `0.7742, 0.4516, 0.7742` (mean 0.6667); with-skill `1.0, 1.0, 1.0`.

## Established

**Both arms ran on the same frozen bytes, relative to each other.** All six runs record one
identical `task_digest`, in both `config.json` and `result.json`, and those two fields agree
within every run. Re-derived directly from committed bytes on 2026-08-05, independently of
`repackage_trajectories.py` — whose cross-arm digest guard reads raw `jobs/` output and is
inert against this committed layout, so it never certified this bundle either way. Verifiable
at any time with:

    python repackage_trajectories.py --verify-packaged <this bundle>/trajectories

**No run failed.** Every zero-or-partial score is an agent outcome, not a harness fault; no
error category is set on any run.

## NOT established

**These runs cannot be bound to the bytes this bundle ships.** benchflow's `result.json`
`source` block — repo, resolved sha, `dirty` flag, per-file hashes — is absent from all six
runs, so there is no recorded statement of what source tree the harness loaded.

The `task_digest` does not close that gap. Recomputing it with benchflow's own recipe
(`benchflow/_utils/task_authoring/__init__.py:task_digest`) against these committed bytes
yields `sha256:13ad686402df63e9…`, not the recorded `sha256:8e537ab56382a101…`. The recorded
value was not reproduced by any variant tried: shipped bytes with and without `trajectories/`,
with and without `TRUTH.md`, and the pre-pin tree at samples commit `573b1bd` in both forms.

Note that the base-image pin landed on 2026-08-05, after these runs, and moved
`environment/Dockerfile`; but the pre-pin variants do not reproduce the digest either, so the
pin is not the explanation and the divergence predates it.

## What may and may not be claimed

The measured difference is **+0.3333** (with-skill 1.0000 − no-skill 0.6667). It is a
digest-paired comparison: the arms are provably a single frozen-bytes cohort with respect to
one another, which is what a skill-delta claim actually requires.

What must **not** be claimed is that this delta was measured on the bundle as shipped. That
binding is unrecorded and unreproducible. Anyone re-running should re-derive the digest from a
clean checkout first and treat these numbers as a prior measurement of a predecessor tree, not
as a certified measurement of these bytes.
