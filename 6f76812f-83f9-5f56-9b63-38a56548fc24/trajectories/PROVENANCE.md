# Provenance — 6f76812f run records

State of this bundle's measurement evidence, recorded 2026-08-05. It separates what the records establish from what they do not. `trajectories/` sits outside this bundle's content seal, so nothing here affects any hash.

## What the records contain

| | |
|---|---|
| Model | claude-opus-4-8 |
| Arms | `no-skill` 3 runs, `with-skill` 3 runs |
| `task_digest` | one digest across both arms |
| Scores `no-skill` | 0.0000, 0.0000, 0.0000 |
| Scores `with-skill` | 1.0000, 1.0000, 1.0000 |

## Source tree: reconstructed, not recovered

All 6 runs record `Ethara-Ai/erza-harness` at `a45214b569b4`, path `tasks/ionosphere-arc-vtec-calibration`, with `source.dirty: true` on 6 of 6.

That path **does not exist at that commit and was never committed at any point in that repository's history**. The tree was an uncommitted working directory. Its provenance is therefore not recoverable, and no `source` block was invented to suggest otherwise.

The *bytes* are reconstructed content-addressed at `harness/tasks-archive/6f76812f-83f9-5f56-9b63-38a56548fc24/`, rebuilt from the sha256 values these records carry and re-verified against them: **64 of 64 files**. See its `MANIFEST.json`.

## Zero-scoring runs, attributed

3 of 6 runs score exactly zero. The run records carry no machine-readable reason, so each is attributed below from that run's own committed verifier artifacts.

| Run | Verdict | Evidence |
|---|---|---|
| `no-skill/run_1` | **AGENT_FAILURE** | 0/12 graded cases passed |
| `no-skill/run_2` | **AGENT_FAILURE** | 0/12 graded cases passed |
| `no-skill/run_3` | **AGENT_FAILURE** | 0/12 graded cases passed |

3 of 3 are attributable to the agent rather than the harness: the grader ran, produced a report, and the submission failed its graded cases. This is a derived attribution recorded by audit, not a value the producing harness wrote.
