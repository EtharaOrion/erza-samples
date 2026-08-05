# Provenance — 903d6f33 run records

State of this bundle's measurement evidence, recorded 2026-08-05. It separates what the records establish from what they do not. `trajectories/` sits outside this bundle's content seal, so nothing here affects any hash.

## What the records contain

| | |
|---|---|
| Model | claude-opus-4-8 |
| Arms | `no-skill` 3 runs, `with-skill` 3 runs |
| `task_digest` | **differs across arms** |
| Scores `no-skill` | 0.0000, 0.0000, 1.0000 |
| Scores `with-skill` | 1.0000, 1.0000, 1.0000 |

## Source tree: reconstructed, not recovered

These runs carry **no `source` block**, so there is no record of which tree they executed against. A reader who did not know that would reasonably assume provenance had been checked. It has not been.

## Arms did not run on the same bytes

The two arms record different `task_digest` values:

* `sha256:5890a37e767da9c6d378c71c6a271f85429f034160509e867e38662e38deb492`
* `sha256:5f06cce33b2cfcab1a2b5353cbb0752e70190f151646400339f375fbf6967148`

Any difference between the arms therefore confounds the skill under test with the change in task bytes. **The delta from this bundle is not quotable as a measurement of the skill.**

## Zero-scoring runs, attributed

2 of 6 runs score exactly zero. The run records carry no machine-readable reason, so each is attributed below from that run's own committed verifier artifacts.

| Run | Verdict | Evidence |
|---|---|---|
| `no-skill/run_1` | **AGENT_FAILURE** | 0/16 graded cases passed; This run shipped no JUnit report; the cases were read from the archived pytest log, which carries per-case verdicts but no timings |
| `no-skill/run_2` | **AGENT_FAILURE** | 0/16 graded cases passed; This run shipped no JUnit report; the cases were read from the archived pytest log, which carries per-case verdicts but no timings |

2 of 2 are attributable to the agent rather than the harness: the grader ran, produced a report, and the submission failed its graded cases. This is a derived attribution recorded by audit, not a value the producing harness wrote.
