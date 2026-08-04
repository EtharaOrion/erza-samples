# Process verifier — flight-duty-period-legality

Grades the PROCESS a run followed, not the numbers it produced. The reward is
`../test.sh`; nothing here touches it.

```
./run.sh <erza-run-dir> [--offline] [--judges N]
```

## Layout

| file | what it is |
|---|---|
| `TRUTH.md` | the answer-free golden trajectory. Safe to hand the judge. |
| `rubrics.json` | 18 criteria: 15 deterministic, 3 judged. Weights in {5,3,1,0}, guardrails negative, narration capped at 1, one gate. |
| `verifier/trajectory.py` | normalises an Erza run directory into turns, commands, file writes, authored code and prose. |
| `verifier/checks.py` | the detectors. Positive detectors return True when satisfied; `failure_*` detectors return True when the failure mode occurred. |
| `verifier/test_trajectory.py` | one `test_<criterion_id>` per deterministic criterion. `score.py` joins junit test names to criteria by stripping `test_`. |
| `judge/judge.py` | the judged channel: a panel of N judges over the trajectory plus `TRUTH.md`. `--offline` abstains without credentials. |
| `score.py` | blends the two channels by weight mass, applies the gate and the coverage floor, and reports CONTINUOUS beside `final`. |
| `verification/` | the instrument's own tests: the negative-fixture matrix, the re-derivation suite and the truth-reference check. |

## Running the instrument's own tests

```
python3 -m pytest verification/ -q          # 96 collected, all must pass
python3 verification/check_refs.py          # every truth_ref resolves
python3 verification/negative_fixtures_test.py   # human-readable firing table
```

`verification/` collects 96 tests. The fixture matrix is parametrized so that
**every** deterministic criterion is a collected test in both halves — quiet on a
clean run, firing on a planted defect — rather than hidden inside a `main()`.
Each of the four guardrails additionally has a benign near-miss fixture and a
test that names its detector while asserting it stays quiet, because a guardrail
carries negative weight and a false fire subtracts from an innocent run.

`rederivation_test.py` re-derives all 51 goldens through the independent route
(`verifier/reg_reparse.py`, which parses the published regulation XML) and
compares the oracle's hand transcription against that parse over every minute of
the day. It takes no arguments and resolves every path relative to the bundle, so
it runs unchanged from `harness/tasks/<slug>/` and from `dataset/<uuid>/`.

## The gate

One criterion gates: `d_indexes_matrix_on_both_axes`, the crux this task exists
to measure. When it scores 0, `score.py` caps `final` at 0.5 and labels the run
CRUX-FAILED, rather than printing a near-pass for a run that never held the
matrix. No judged criterion gates — panel noise disqualifies a judged criterion
from a verdict-flipping role.

## Known limits of the deterministic channel

The channel pattern-matches the source the agent authored. That is strictly
weaker than executing the agent's solver, and it is the largest source of false
negatives on unseen runs: a run that computes the right thing in a spelling no
matcher anticipated abstains rather than scores. Two consequences worth stating:

* the crux detector requires at least six distinct published cells to appear in
  the authored source, at least two of them half-hour values. A run that holds
  the matrix but never writes more than a handful of its cells — because it only
  needed those — will not satisfy it. That is a deliberate false-negative bias:
  the alternative, accepting a single cell, would accept a guess.
* detector precision has not been measured against real runs, because no pilot
  has run. The fixture matrix shows each detector firing on its own failure mode
  and staying quiet on a clean run and on a near miss; that is the tightest
  evidence available before a pilot, and it is not the same as precision.
