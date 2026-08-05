#!/bin/bash
# In-container grading entrypoint.
#
#  * Score artifacts are PRE-SEEDED to 0, so a crash, a collection error or a
#    missing report grades 0 - never a missing file, never a crash that reads
#    as success.
#  * The score is parsed from the STRUCTURED report, never from the exit code
#    and never from a text scan of the human-readable log. pytest still writes
#    JUnit to a scratch path; this script converts it to `process.json` and the
#    XML never ships.
#  * Scored tests are identified by the `test_score_` prefix. Everything else
#    in the module is either a process-channel test (not selected here) or an
#    unscored grader self-check excluded from the denominator, so adding a
#    self-check can never inflate the score.
#  * SELF-CHECK KILL-SWITCH: a failing or skipped self-check means the bundle
#    failed its own audit; the run scores 0 fail-closed and is INVALID for
#    training composition (a BUNDLE DEFECT, not an agent failure).
#  * The script always exits 0. The score file is the verdict.
#
# Score family: FRACTIONAL
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

# Markers are registered inline so the bundle needs no conftest.py and no
# pytest.ini; the harness registers the same three for post-hoc process runs.
MARKERS=$'outcome: in-container outcome tests, scored into the score
process: post-hoc tests over a recorded trajectory
selfcheck: unscored grader audit; a failure trips the kill-switch'

python3 -m pytest "$TESTS_DIR/test_output.py" -m "outcome or selfcheck" \
  -v --tb=short -p no:cacheprovider -o markers="$MARKERS" \
  --junitxml="$JUNIT" \
  > "$PYLOG" 2>&1

READ=$(JUNIT="$JUNIT" python3 - <<'PYEOF'
import json, os
import xml.etree.ElementTree as ET

OUT = "/logs/verifier/process.json"
cases, passed, total, selfcheck_failed = [], 0, 0, 0
try:
    root = ET.parse(os.environ["JUNIT"]).getroot()
except Exception:
    json.dump({"outcome": {"score": 0.0, "cases_passed": 0, "cases_total": 0,
                           "cases": [], "note": "no parseable report"}},
              open(OUT, "w"), indent=1)
    print("0 0 1")
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
    cases.append({"name": name, "classname": c.get("classname", ""),
                  "status": "skipped" if skipped else ("failed" if bad else "passed"),
                  "time": float(c.get("time") or 0.0)})
    if name.startswith("test_score_"):
        total += 1
        if not bad and not skipped:
            passed += 1
    elif name.startswith("test_selfcheck_") and (bad or skipped):
        selfcheck_failed += 1

score = (min(passed, total) / total) if (total > 0 and selfcheck_failed == 0) else 0.0
# FRACTIONAL family: graded cases passed / total; 0.0 fail-closed if a self-check tripped.
json.dump({"outcome": {"score": score, "cases_passed": passed, "cases_total": total,
                       "selfcheck_failed": selfcheck_failed, "cases": cases}},
          open(OUT, "w"), indent=1)
print("%d %d %d" % (passed, total, selfcheck_failed))
PYEOF
)
PASSED=$(printf '%s' "$READ" | awk '{print $1+0}')
TOTAL=$(printf '%s' "$READ" | awk '{print $2+0}')
SELFCHECK_FAILED=$(printf '%s' "$READ" | awk 'NF>2{print $3+0; f=1} END{if(!f) print 1}')

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

if [ "$TOTAL" -le 0 ]; then
  echo "no scored tests found in the report - grading 0 fail-closed"
  cat "$PYLOG"
  exit 0
fi

# FRACTIONAL family: score is graded cases passed / graded cases total.
SCORE=$(python3 -c "print(f'{min($PASSED,$TOTAL)/$TOTAL:.4f}')")

echo "$SCORE" > /logs/verifier/score.md
echo "test cases passed  : $PASSED/$TOTAL"
echo "self-check failures: $SELFCHECK_FAILED"
echo "Score              : $SCORE"
cat "$PYLOG"
exit 0
