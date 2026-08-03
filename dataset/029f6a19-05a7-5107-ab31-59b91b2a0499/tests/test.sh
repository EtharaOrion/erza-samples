#!/bin/bash
# Deterministic grading: one pytest per graded record. Score = passed/31,
# pass@1 = all pass. The pass count is read from the JUnit XML, never a text
# scan, and is filtered to the graded prefix so a passing grader self-check can
# never stand in for a failed graded case.
#
# This entrypoint GATES: if any grader self-check fails or is skipped, the run
# scores 0 rather than being graded by a verifier that has failed its own audit.
mkdir -p /logs/verifier
echo "0.0000" > /logs/verifier/reward.txt
echo "0.0000" > /logs/verifier/Score.txt
echo 0 > /logs/verifier/pass_at_1.txt

python3 -m pytest /tests/test_outputs.py -v --tb=short \
  -p no:cacheprovider \
  --junitxml=/logs/verifier/results.xml \
  > /logs/verifier/pytest_output.txt 2>&1

TOTAL=31
READ=$(python3 - "$TOTAL" <<'PYEOF'
import sys, xml.etree.ElementTree as ET
total = int(sys.argv[1])
try:
    root = ET.parse("/logs/verifier/results.xml").getroot()
except Exception:
    print("0 1"); raise SystemExit
passed, selfcheck_failed, seen = 0, 0, set()
for c in root.iter("testcase"):
    name = c.get("name", "")
    key = (c.get("classname", ""), name)
    if key in seen:
        continue
    seen.add(key)
    bad = any(c.find(t) is not None for t in ("failure", "error"))
    skipped = c.find("skipped") is not None
    if name.startswith("test_graded_case"):
        if not bad and not skipped:
            passed += 1
    else:
        # a grader self-check that fails OR is skipped invalidates the audit
        if bad or skipped:
            selfcheck_failed += 1
print("%d %d" % (min(passed, total), selfcheck_failed))
PYEOF
)
PASSED=$(echo "$READ" | cut -d' ' -f1); PASSED=${PASSED:-0}
SELFCHECK_FAILED=$(echo "$READ" | cut -d' ' -f2); SELFCHECK_FAILED=${SELFCHECK_FAILED:-1}

if [ "$SELFCHECK_FAILED" -gt 0 ]; then
  echo "GATED: $SELFCHECK_FAILED grader self-check(s) failed or skipped; scoring 0"
  echo 0 > /logs/verifier/pass_at_1.txt
  echo "0.0000" > /logs/verifier/reward.txt
  echo "0.0000" > /logs/verifier/Score.txt
  tail -40 /logs/verifier/pytest_output.txt
  exit 0
fi

SCORE=$(python3 -c "print(f'{min($PASSED,$TOTAL)/$TOTAL:.4f}')")
echo "$SCORE" > /logs/verifier/reward.txt
echo "$SCORE" > /logs/verifier/Score.txt
if [ "$PASSED" -ge "$TOTAL" ]; then
  echo 1 > /logs/verifier/pass_at_1.txt; PASS1=1
else
  echo 0 > /logs/verifier/pass_at_1.txt; PASS1=0
fi
echo "test cases passed : $PASSED/$TOTAL"
echo "Score             : $SCORE"
echo "pass@1            : $PASS1"
tail -40 /logs/verifier/pytest_output.txt
exit 0
