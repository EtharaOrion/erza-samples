"""Traceability check: every truth_ref in rubrics.json must resolve to a real
heading in the CURRENT TRUTH.md.

Exists because a TRUTH.md rewrite on an earlier bundle left every truth_ref
pointing at deleted section names and nothing caught it. Run it alongside
negative_fixtures_test.py whenever TRUTH.md or rubrics.json changes.

A truth_ref is one or more targets separated by ';'. Each target must be
"Step N", "Step Na" (a lettered sub-step) or the verbatim title of a ##
section. Sub-steps are headings in their own right: a resolver that knows only
"Step N" reports false rot on every bundle whose crux is split.

    python3 verification/check_refs.py        # exit 0 when every ref resolves

Deliberately NOT named *_test.py: it takes no arguments, it is a script, and a
module under this directory that reads sys.argv would be collected by pytest
and error at COLLECTION, taking the fixture matrix down with it.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.normpath(os.path.join(HERE, ".."))
BUNDLE = os.path.normpath(os.path.join(TESTS, ".."))

RUBRICS = os.path.join(TESTS, "rubrics.json")
# The judge grades against the TRUTH.md beside the rubric; in this layout that
# is the bundle-root copy.
TRUTH = os.path.join(TESTS, "TRUTH.md")
if not os.path.exists(TRUTH):
    TRUTH = os.path.join(BUNDLE, "TRUTH.md")


def resolve_all(truth: str, spec: dict):
    """(dangling, steps, substeps, sections) for this TRUTH.md / rubrics.json pair."""
    steps = set(re.findall(r"^#+ Step (\d+)\b", truth, re.M))
    substeps = set(re.findall(r"^#+ (\d+[a-z])\b", truth, re.M))
    sections = {
        m.strip().rstrip("*").strip()
        for m in re.findall(r"^## (?!Step )(.+)$", truth, re.M)
    }

    def resolves(target: str) -> bool:
        target = target.strip()
        m = re.fullmatch(r"Step (\d+)([a-z])?", target)
        if m:
            if m.group(2):
                return m.group(1) + m.group(2) in substeps
            return m.group(1) in steps
        return target in sections

    dangling = []
    for crit in spec["criteria"]:
        for target in str(crit.get("truth_ref", "")).split(";"):
            if not resolves(target):
                dangling.append((crit["id"], target.strip()))
    return dangling, steps, substeps, sections


def main() -> int:
    with open(TRUTH) as fh:
        truth = fh.read()
    with open(RUBRICS) as fh:
        spec = json.load(fh)

    dangling, steps, substeps, sections = resolve_all(truth, spec)
    if dangling:
        for cid, target in dangling:
            print("  DANGLING  %s: %r" % (cid, target))
        print("\n%d truth_ref target(s) do not resolve to a TRUTH.md heading"
              % len(dangling))
        return 1
    print("  all %d truth_refs resolve to TRUTH.md headings "
          "(%d steps, %d sub-steps, %d sections)"
          % (len(spec["criteria"]), len(steps), len(substeps), len(sections)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
