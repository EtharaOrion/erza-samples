# Provenance — 3c4a9e2d run records

State of this bundle's measurement evidence, recorded 2026-08-05, the day the bundle was migrated into this sample set from `dataset/3c4a9e2d-9ac7-5281-866b-c25c151097e9`. `trajectories/` sits outside the bundle's content seal, so nothing here affects any hash.

**Read `SUPERSEDED.md` in this directory first. These runs measure the pre-repair prompt, not the bytes this bundle ships.** That notice travelled here verbatim with the runs it governs, and this file only adds the migration-specific facts around it.

## What the records contain

| | |
|---|---|
| Model | `claude-opus-4-8`, single model across both arms |
| Arms | `no-skill` 3 runs, `with-skill` 3 runs |
| `task_digest` | `sha256:795f9d491801f7d0ec54465fce97d496084c4cb957e4c20c9d813fe09cc27a74`, one digest across both arms and all six runs |
| Errors | none — no run carries an `error` or `error_category` |
| Scores | no-skill `0.0714, 0.0, 0.0` (mean 0.0238); with-skill `1.0, 1.0, 1.0` |

The score records were converted from the producing harness's `rewards` naming (`rewards.jsonl`, `result.json` `rewards.reward`) to this set's `scores` naming (`scores.jsonl`, `result.json` `scores.score`) at migration. Values, timestamps and every other byte of the run records are unchanged.

## What is established

**Both arms ran on the same frozen bytes, relative to each other.** All six runs record one `task_digest`, so the paired comparison is internally valid: the +0.976 delta is computed over identical task bytes and is not confounded by a byte change between arms.

**The pre-repair prompt leak was symmetric**, per the analysis in `SUPERSEDED.md`: `prompts.json` is byte-identical across arms, so the leaked rule cancels in the difference. The delta is a sound measurement of the skill's effect on the pre-repair task.

## What is not established

**These runs do not measure the bundle as shipped here.** Between the recording and this migration, the repair in dataset commit `e512b11` changed the agent-visible surface: the prompt had stated the crux rule (bind each ledger line to its own reporting period's factor edition) and the repair withdrew it, replacing it with "the specification is not reproduced in this prompt: determine it and apply it correctly", and added a scoring-transparency paragraph. The shipped prompt is therefore strictly harder for an unaided run than the one these runs measured.

Consequences, stated exactly:

* The recorded no-skill mean `0.0238` is an **upper bound** on the shipped bundle's unaided score, because the repair only removed help. The bundle's true unaided level under the shipped bytes is unmeasured and can only be established by a fresh paired pilot.
* The difficulty-tier placement of this bundle in the README is **provisional** on that upper bound: the recorded band is Hard (`0 < A < 0.3`), and the shipped bytes can only sit there or lower (Expert). It cannot be easier than recorded.
* The recorded runs carry no `source` block; their tree provenance rests on the recorded `task_digest` alone. The digest hashes the pre-repair task directory, which no longer exists as a directory anywhere; the recorded prompt bytes inside each run are the primary evidence of what the agent saw.

## Zero-and-partial scoring runs, attributed

No run scores an unattributed zero: `no-skill/run_2` and `run_3` score `0.0` with the outcome verifier's archived per-case report present (`verifier/`), showing graded cases failing on value, and `run_1` scores `0.0714` = 1/14 cases within tolerance. All three are agent failures on the graded values, not harness failures. The with-skill runs score `1.0` with all 14 cases within tolerance.

## What replaces this

A fresh paired pilot against the shipped bytes, run through the current harness. Until it exists, quote the delta as a measurement of the pre-repair task and the no-skill level only as an upper bound for the shipped one.
