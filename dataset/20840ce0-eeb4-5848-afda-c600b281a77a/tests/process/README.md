# verifier/process — grading the trajectory, not just the answer

`../test_outputs.py` grades the **answer**: it slices every submitted line apart
at the published positions and decodes each field back to a semantic value,
scoring 31 cases. This directory grades the **process** — what the run actually
did on the way there: whether it treated the layout as a map of absolute
positions, whether it placed the payee identification block where the
specification puts it, whether it emitted the reserved runs rather than closing
them, and whether it checked its own output by reading the record back.

## ⚠️ Grader-side only. Never mounted, never shipped to the agent.
`environment/Dockerfile` copies only `environment/data`, and `/verifier` is in
`sandbox_locked_paths`, so nothing here reaches the container. Nested at
`verifier/process/` (not `verifier/`) so the pytest that runs the outcome
verifier never loads this directory.

## Contents
| Path | What it is |
|---|---|
| `TRUTH.md` | answer-free golden trajectory (Steps 0–7, crux marked at Step 5), derived from `oracle/solve.py` with every produced value **and every field position** stripped |
| `rubrics.json` | 18 process criteria (15 deterministic, 3 judged), each traced to a TRUTH.md heading and carrying `weight_evidence` |
| `verifier/trajectory.py` | normaliser: an Erza run dir → turns / commands / file writes / agent code / transcript |
| `verifier/checks.py` | the deterministic detectors, one per deterministic criterion |
| `verifier/test_trajectory.py` | deterministic channel — one `test_<criterion_id>` each (`--run-dir`), plus a meta test asserting the name↔id join in both directions |
| `judge/judge.py` | non-deterministic channel — LLM judge panel over the answer-free TRUTH.md + transcript |
| `score.py` | combines both by **weight mass**; gate → CRUX-FAILED caps `final` at 0.5; coverage floor; CONTINUOUS |
| `report.py` | per-run breakdown across every `results/*.score.json` |
| `verification/negative_fixtures_test.py` | the fire-side matrix: both halves of all 15 deterministic criteria, plus one benign near-miss test per guardrail calling that guardrail's detector by name — **all collected** |
| `verification/rederivation_test.py` | a third, independent transcription of the field table — lengths only, starts computed — reproducing every frozen golden, plus the answer-free audit of TRUTH.md |
| `verification/check_refs.py` | every `truth_ref` resolves to a heading in the **current** TRUTH.md |

Run: `./run.sh <run-dir> [--offline]`. Verify:
`python -m pytest verifier/process/verification/ -q` (78 collected, green) and
`python verifier/process/verification/check_refs.py`.

## What "deterministic" means here — read this before trusting the numbers
The deterministic channel does **not** execute the agent's emitter. It
**pattern-matches the source the agent wrote** (`agent_code` = file writes plus
the commands it ran). That is strictly weaker than running the code and is the
single largest source of false negatives on unseen runs: every detector in
`checks.py` is a *hypothesis about how a correct run is spelled*.

The crux detector is the exception in one useful respect: it is **numeric**, not
lexical. It asks whether a literal reading as the first payee name line's
published start *and* one reading as the payee city's published start both
appear where they can act — or, for a run that wrote the whole position column
out, whether at least six of the published late start positions are present. A
run cannot satisfy it by narrating, and a run that packed the fields on with the
reserved runs closed fails it, which is exactly the discrimination the task is
built on.

**The known false negative, stated rather than buried.** A correct run that
concatenates fields by LENGTH and never writes an absolute offset satisfies the
task and fails this detector, which would print CRUX-FAILED beside a perfect
CONTINUOUS. That spelling is uncommon for a fifty-row table and the alternative
— a run that skipped the only step the task exists to measure printing an
uncapped number — is worse. A reviewer seeing CRUX-FAILED beside a high
CONTINUOUS should check for it by hand. The same caveat is recorded in
`rubrics.json:gate_doctrine`.

The name↔id join is the known trap: `score.py` pairs a junit testcase to a
criterion by stripping the leading `test_`, and a mismatch makes the criterion
abstain **silently**, which can drag the channel under its coverage floor and
report INVALID for no visible reason.
`test_zz_meta_every_detector_pairs_with_a_rubric_id` asserts the join in both
directions, and `verification/` asserts it again from the other side.

## The weight doctrine, in one paragraph
Every weight magnitude is in `{5, 3, 1, 0}`; guardrails are negative; narration —
a speech act any style-tuned model can emit — is capped at `1`. A `5` is the
crux: placing the payee identification block at its published offsets
(`d_places_payee_block_at_published_offsets`) and emitting the reserved runs
rather than closing them (`d_reserves_the_interior_runs`), each traced to the
measured `shifted_name_and_address_block` control in
`../expected_values.json:control_gaps`. A `3` is an outcome-breaking placement
or convention error. A `1` is hygiene or narration. Note in particular that the
payment-amount convention is weighted `3`, not `5`: it is the part of this
specification a model reproduces unaided, and
`../test_outputs.py::test_amount_convention_alone_does_not_carry_the_task`
asserts that it cannot carry the separation. Every weight records its receipt in
`rubrics.json:weight_evidence`.

**One criterion gates**, `d_places_payee_block_at_published_offsets`, with the
caveat above.

## Why TRUTH.md withholds the table it otherwise describes
§6.11 sets two requirements that pull against each other on this task: keep
constants inside a relation, and make sure prompt + TRUTH.md **without** the
skill cannot score 1. Here the withheld lever *is* a position table, so printing
even part of it would make TRUTH.md a second answer key. TRUTH.md therefore
carries the whole method — the field classes and their justification and fill
rules, the self-consistency check a position table must survive, the ordering,
the read-back that catches an off-by-one a forward emitter cannot see — and no
field position at all. `rederivation_test.py` asserts that mechanically:
`test_truth_md_withholds_the_field_positions` fails if any field boundary
between position 20 and the declared record length appears as a numeral, and
`test_truth_md_carries_no_assembled_record` fails if any line reads as an
assembled record.

## Scores this instrument reports
- **FINAL** — the doctrine-weighted process score, blended by weight mass.
  Secondary to the per-criterion vector.
- **CONTINUOUS** — the task's own outcome metric: graded cases within tolerance
  / 31, outcome cases only. No `results.json` in the run dir → INVALID, never
  zero: an unwritten answer is not a wrong one.
- A run showing CONTINUOUS near zero beside a healthy FINAL is the two numbers
  doing their job: *how much of the record landed* versus *whether the run
  treated the layout as a map of absolute positions on the way there*.

## Validity domain
This is a Bucket-N research instrument over honest, frozen, rubric-unaware runs.
The scores are cheaply satisfiable under optimisation pressure (write some
plausible-looking offsets, narrate a read-back, emit a line of the right length)
and **must not be used as a training or selection signal** without adversarial
hardening this method does not provide. The outcome verifier
(`../test_outputs.py`) remains the only Bucket-D instrument.
