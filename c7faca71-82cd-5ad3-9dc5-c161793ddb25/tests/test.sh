#!/bin/bash
# In-container grading entrypoint.
#
#  * Score artifacts are PRE-SEEDED to 0, so a crash, a collection error or a
#    missing report grades 0 - never a missing file, never a crash that reads
#    as success.
#  * The score is parsed from the STRUCTURED report, never from the exit code
#    and never from a text scan of the human-readable log. The text-scan route
#    is not merely inelegant, it is a known exploit on this fleet. pytest still
#    writes JUnit, but to a scratch path; this script converts it to
#    `process.json` in-script with the standard library, and the XML never ships.
#  * Graded cases are identified by the `test_graded_case` prefix - and this is
#    the single place that prefix is written. Everything else the module
#    collects is an unscored grader self-check, excluded from the denominator,
#    so adding a self-check can never inflate the score.
#  * SELF-CHECK KILL-SWITCH: a failing or skipped self-check means the bundle
#    failed its own audit; the run scores 0 fail-closed and is INVALID for
#    training composition (a BUNDLE DEFECT, not an agent failure).
#  * The script always exits 0. The score file is the verdict.
#
# Score family: FRACTIONAL - score = graded cases passed / 51, pass@1 = all pass.
# The denominator is FIXED at 51: a graded case that fails to collect must
# lower the score, not shrink the denominator.
#
# Emits, matching the reference sample layout:
#   /logs/verifier/score.md      the scalar verdict
#   /logs/verifier/process.json  outcome block; the post-hoc scorer adds the
#                                deterministic and judged blocks to this file
# The full pytest log goes to stdout, which the harness archives as test-stdout.md.
set -u
mkdir -p /logs/verifier
echo "0.0000" > /logs/verifier/score.md

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ERZA_BUNDLE_DIR="${ERZA_BUNDLE_DIR:-$(dirname "$TESTS_DIR")}"

JUNIT="$(mktemp -t erza_junit.XXXXXX)"
PYLOG="$(mktemp -t erza_pytest.XXXXXX)"
trap 'rm -f "$JUNIT" "$PYLOG"' EXIT

# This module registers no pytest markers and its graded set is the whole file,
# so there is no -m selection here and no conftest.py is required for it.
python3 -m pytest "$TESTS_DIR/test_outcome.py" -v --tb=short \
  -p no:cacheprovider \
  --junitxml="$JUNIT" \
  > "$PYLOG" 2>&1

TOTAL=51
READ=$(JUNIT="$JUNIT" TOTAL="$TOTAL" python3 - <<'XMLCONV'
import json, os
import xml.etree.ElementTree as ET

OUT = "/logs/verifier/process.json"
PREFIX = "test_graded_case"
TOTAL = int(os.environ["TOTAL"])
cases, selfchecks, passed, selfcheck_failed = [], [], 0, 0
try:
    root = ET.parse(os.environ["JUNIT"]).getroot()
except Exception:
    json.dump({"outcome": {"score": 0.0, "cases_passed": 0, "cases_total": TOTAL,
                            "selfchecks_passed": 0, "selfchecks_total": 0,
                            "selfcheck_failed": 1,
                            "cases": [], "selfchecks": [],
                            "note": "no parseable report"},
                "pass_at_1": 0},
              open(OUT, "w"), indent=1)
    print("0 1 0")
    raise SystemExit

seen = set()
for c in root.iter("testcase"):
    name = c.get("name", "")
    key = (c.get("classname", ""), name)
    if key in seen:
        continue
    seen.add(key)
    bad = any(c.find(t) is not None for t in ("failure", "error"))
    skipped = c.find("skipped") is not None
    row = {"name": name, "classname": c.get("classname", ""),
            "status": "skipped" if skipped else ("failed" if bad else "passed"),
            "time": float(c.get("time") or 0.0)}
    if name.startswith(PREFIX):
        cases.append(row)
        if not bad and not skipped:
            passed += 1
    else:
        # a grader self-check that fails OR is skipped invalidates the audit
        selfchecks.append(row)
        if bad or skipped:
            selfcheck_failed += 1

passed = min(passed, TOTAL)
score = 0.0 if selfcheck_failed else round(passed / TOTAL, 4)
pass_at_1 = 1 if (not selfcheck_failed and passed >= TOTAL) else 0
json.dump({"outcome": {"score": score, "cases_passed": passed, "cases_total": TOTAL,
                        "selfchecks_passed": len(selfchecks) - selfcheck_failed,
                        "selfchecks_total": len(selfchecks),
                        "selfcheck_failed": selfcheck_failed,
                        "cases": cases, "selfchecks": selfchecks},
            "pass_at_1": pass_at_1},
          open(OUT, "w"), indent=1)
print("%d %d %d" % (passed, selfcheck_failed, pass_at_1))
XMLCONV
)
PASSED=$(printf '%s' "$READ" | awk '{print $1+0}')
SELFCHECK_FAILED=$(printf '%s' "$READ" | awk 'NF>2{print $2+0; f=1} END{if(!f) print 1}')
PASS1=$(printf '%s' "$READ" | awk 'NF>2{print $3+0; f=1} END{if(!f) print 0}')

if [ "$SELFCHECK_FAILED" -gt 0 ]; then
  echo "=============================================================="
  echo "BUNDLE DEFECT - GRADER SELF-CHECK FAILED ($SELFCHECK_FAILED)"
  echo "This verifier has failed its own audit, so it is not fit to grade."
  echo "Scoring 0 fail-closed. This run is INVALID for training composition"
  echo "(a bundle defect, NOT an agent failure). Pull the bundle for repair."
  echo "=============================================================="
  cat "$PYLOG"
  exit 0
fi

# FRACTIONAL family: the score is the share of the 51 graded cases that passed.
SCORE=$(python3 -c "print(f'{min($PASSED,$TOTAL)/$TOTAL:.4f}')")
echo "$SCORE" > /logs/verifier/score.md
echo "test cases passed  : $PASSED/$TOTAL"
echo "self-check failures: $SELFCHECK_FAILED"
echo "Score              : $SCORE"
echo "pass@1             : $PASS1"
cat "$PYLOG"
exit 0
