# verifier/process — grading the trajectory, not just the answer

`../test_outputs.py` grades the **answer**: it re-derives all five graded figures
from the baked ledger through the independent formulation and scores
`/root/results.json`. This directory grades the **process** — what the run
actually did on the way there: whether it noticed that the energy in a barrel
depends on which class of customer burned it, whether it used each book's *own*
published series for each row's *own* year, and whether it mapped the two
awkward coal books onto the partition the publisher actually uses.

## ⚠️ Grader-side only. Never mounted, never shipped to the agent.
`environment/Dockerfile` copies only `environment/data`, and `/verifier` is in
`sandbox_locked_paths`, so nothing here reaches the container. Nested at
`verifier/process/` (not `verifier/`) so the pytest that runs the outcome
verifier never loads this directory.

## Contents
| Path | What it is |
|---|---|
| `TRUTH.md` | answer-free golden trajectory (Steps 0–7, crux marked at Step 3), derived from `oracle/solve.sh` with every produced value stripped |
| `rubrics.json` | 17 process criteria (14 deterministic, 3 judged), each traced to a TRUTH.md heading and carrying `weight_evidence` |
| `verifier/trajectory.py` | normaliser: an Erza run dir → turns / commands / file writes / agent code / transcript |
| `verifier/checks.py` | the deterministic detectors, one per deterministic criterion |
| `verifier/test_trajectory.py` | deterministic channel — one `test_<criterion_id>` each (`--run-dir`), plus a meta test asserting the name↔id join in both directions |
| `judge/judge.py` | non-deterministic channel — LLM judge panel over the answer-free TRUTH.md + transcript |
| `score.py` | combines both by **weight mass**; gate → CRUX-FAILED caps `final` at 0.5; coverage floor; CONTINUOUS |
| `report.py` | per-run breakdown across every `results/*.score.json` |
| `verification/negative_fixtures_test.py` | the fire-side matrix: both halves of all 14 deterministic criteria, plus one benign near-miss test per guardrail calling that guardrail's detector by name — **all collected** |
| `verification/rederivation_test.py` | a third, independent transcription reproducing every frozen golden, the cell-by-cell audit of the skill's tables against the bundled EIA slice, the answer-free audit of TRUTH.md and the placeholder audit of task.md |
| `verification/check_refs.py` | every `truth_ref` resolves to a heading in the **current** TRUTH.md |

Run: `./run.sh <run-dir> [--offline]`. Verify:
`python -m pytest verifier/process/verification/ -q` (59 collected, green) and
`python verifier/process/verification/check_refs.py`.

## What "deterministic" means here — read this before trusting the numbers
The deterministic channel does **not** execute the agent's solver. It
**pattern-matches the source the agent wrote** (`agent_code` = file writes plus
the commands it ran). That is strictly weaker than running the code and is the
single largest source of false negatives on unseen runs: every detector in
`checks.py` is a *hypothesis about how a correct run is spelled*.

The crux detector is the exception in one useful respect: it is **numeric**, not
lexical. It asks whether at least three distinct years of *each* of the five
published series appear, and whether at least one of them appears somewhere it
can act (multiplied, divided, or bound into a table entry). A run cannot satisfy
it by narrating; a run that applied one constant per fuel fails it, and so does a
run that found the table and reused one row across classes — which is exactly the
discrimination the task is built on. That is why it is the criterion that gates.

The name↔id join is the known trap: `score.py` pairs a junit testcase to a
criterion by stripping the leading `test_`, and a mismatch makes the criterion
abstain **silently**, which can drag the channel under its coverage floor and
report INVALID for no visible reason.
`test_zz_meta_every_detector_pairs_with_a_rubric_id` asserts the join in both
directions, and `verification/` asserts it again from the other side.

## The weight doctrine, in one paragraph
Every weight magnitude is in `{5, 3, 1, 0}`; guardrails are negative; narration —
a speech act any style-tuned model can emit — is capped at `1`. A `5` is the crux:
pricing every row from its own book's published series
(`d_applies_class_year_value`), traced to four measured controls in
`../expected_values.json:control_gaps`, none of which clears a single graded case.
A `3` is a work product with real blast radius or a grading-integrity guardrail. A
`1` is hygiene or narration. Every weight records its receipt in
`rubrics.json:weight_evidence`.

**One criterion gates**, `d_applies_class_year_value`, and the caveat is stated in
`rubrics.json:gate_doctrine`: a gate properly wants a detector precision measured
near 1 and no pilot has run. The numeric detector plus a fixture matrix exercising
it in both directions is the tightest evidence available before a pilot, and the
alternative — a run that skipped the only step the task exists to measure still
printing an uncapped number — is worse. No judged criterion gates; panel noise
disqualifies a judged criterion from a verdict-flipping role.

## Why the ordering criterion is weighted 3 and not 5
`d_converts_per_row_then_sums` looks like a crux surface and was drafted at 5.
Then it was measured. `control_gaps.sum_quantities_then_convert_once` — total each
book's quantities and convert once with the arithmetic mean of that book's own
published series — lands **inside** the graded band on 4 of the 5 cases, worst gap
1.82x, because the published value moves only a few percent across the window
inside any one book. The ordering is still the right method and a reviewer should
mark a run that gets it wrong, but the receipt has to be the measurement, not the
intuition, and the weight follows the receipt. `rederivation_test.py` re-measures
it on every run and fails if it ever clears *every* case, which would mean the
criterion had stopped measuring anything.

## Why TRUTH.md withholds five rows of a table it otherwise describes
§6.11 sets two requirements that pull against each other on this task: keep
constants inside a relation, and make sure prompt + TRUTH.md **without** the skill
cannot score 1. Here the withheld lever *is* a value set, so printing the five
graded books' series would make TRUTH.md a second answer key outright. TRUTH.md
therefore carries the whole method — the indexing, the two partition traps, the
ordering argument, the unit chain, and the two published identities that bind the
values — plus three years of two *other* rows of the same published table, for
sectors this ledger does not carry, so the eleven-percent spread between sectors
is concrete rather than gestured at. `rederivation_test.py` asserts both halves of
that decision mechanically: no graded value appears in TRUTH.md at any rounding,
and neither does any of the five graded series.

## Scores this instrument reports
- **FINAL** — the doctrine-weighted process score, blended by weight mass.
  Secondary to the per-criterion vector.
- **CONTINUOUS** — the task's own outcome metric: graded cases within tolerance
  / 5, outcome cases only. No `results.json` in the run dir → INVALID, never
  zero: an unwritten answer is not a wrong one.
- A run showing CONTINUOUS `0.0` beside a healthy FINAL is the two numbers doing
  their job: *how much of the answer was right* versus *whether the run did the
  load-bearing selection on the way there*.

## Validity domain
This is a Bucket-N research instrument over honest, frozen, rubric-unaware runs.
The scores are cheaply satisfiable under optimisation pressure (name the classes,
narrate a conversion, emit a plausible number) and **must not be used as a
training or selection signal** without adversarial hardening this method does not
provide. The outcome verifier (`../test_outputs.py`) remains the only Bucket-D
instrument.
