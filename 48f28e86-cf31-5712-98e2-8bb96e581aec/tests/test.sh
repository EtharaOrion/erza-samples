#!/bin/bash
# In-container grading entrypoint.
#
#  * Reward artifacts are PRE-SEEDED to 0, so a crash, a collection error or a
#    missing report grades 0 - never a missing file, never a crash that reads
#    as success.
#  * The score is parsed from the STRUCTURED report (JUnit XML), never from the
#    exit code and never from a text scan of the human-readable log.
#  * Scored tests are identified by the `test_reward_` prefix. Everything else
#    in the module is either a process-channel test (not selected here) or an
#    unscored grader self-check excluded from the denominator, so adding a
#    self-check can never inflate the reward.
#  * SELF-CHECK KILL-SWITCH: a failing or skipped self-check means the bundle
#    failed its own audit; the run scores 0 fail-closed and is INVALID for
#    training composition (a BUNDLE DEFECT, not an agent failure).
#  * The script always exits 0. The reward file is the verdict.
#
# Reward family: BINARY
set -u
mkdir -p /logs/verifier
echo "0" > /logs/verifier/reward.txt
echo "0" > /logs/verifier/Score.txt
echo "0" > /logs/verifier/pass_at_1.txt

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ERZA_BUNDLE_DIR="${ERZA_BUNDLE_DIR:-$(dirname "$TESTS_DIR")}"

# Markers are registered inline so the bundle needs no conftest.py and no
# pytest.ini; the harness registers the same three for post-hoc process runs.
MARKERS=$'outcome: in-container outcome tests, scored into the reward
process: post-hoc tests over a recorded trajectory
selfcheck: unscored grader audit; a failure trips the kill-switch'

python3 -m pytest "$TESTS_DIR/test_pytest.py" -m "outcome or selfcheck" \
  -v --tb=short -p no:cacheprovider -o markers="$MARKERS" \
  --junitxml=/logs/verifier/results.xml \
  > /logs/verifier/pytest_output.txt 2>&1

READ=$(python3 - <<'PYEOF'
import xml.etree.ElementTree as ET
try:
    root = ET.parse("/logs/verifier/results.xml").getroot()
except Exception:
    print("0 0 1"); raise SystemExit
passed = total = selfcheck_failed = 0
seen = set()
for c in root.iter("testcase"):
    name = c.get("name", ""); key = (c.get("classname", ""), name)
    if key in seen:
        continue
    seen.add(key)
    bad = any(c.find(t) is not None for t in ("failure", "error"))
    skipped = c.find("skipped") is not None
    if name.startswith("test_reward_"):
        total += 1
        if not bad and not skipped:
            passed += 1
    elif name.startswith("test_selfcheck_") and (bad or skipped):
        selfcheck_failed += 1
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
  tail -60 /logs/verifier/pytest_output.txt
  exit 0
fi

if [ "$TOTAL" -le 0 ]; then
  echo "no scored tests found in the report - grading 0 fail-closed"
  tail -40 /logs/verifier/pytest_output.txt
  exit 0
fi

# BINARY family: reward is 1 iff every scored test passed, else 0.
if [ "$PASSED" -ge "$TOTAL" ]; then SCORE=1; PASS1=1; else SCORE=0; PASS1=0; fi

echo "$SCORE" > /logs/verifier/reward.txt
echo "$SCORE" > /logs/verifier/Score.txt
echo "$PASS1" > /logs/verifier/pass_at_1.txt
echo "test cases passed  : $PASSED/$TOTAL"
echo "self-check failures: $SELFCHECK_FAILED"
echo "Score              : $SCORE"
echo "pass@1             : $PASS1"
tail -40 /logs/verifier/pytest_output.txt
exit 0
