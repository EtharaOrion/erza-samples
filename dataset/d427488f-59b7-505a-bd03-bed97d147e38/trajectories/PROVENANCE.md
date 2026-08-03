# PROVENANCE — d427488f-59b7-505a-bd03-bed97d147e38

**Label: POSITIVE.** Δ = **+1.000**, n = 30/30 per arm, Fisher exact two-sided
**p = 1.691e-17** (0/30 vs 30/30). This is the most powered result in the pushed set.

**Task.** Interlaboratory proficiency-testing consensus under the in-house **ERZA-RB1**
robust-consensus SOP (`erza-rb1-robust-consensus`). 22 laboratories each report 5 replicate
determinations of copper mass fraction in a leaded-bronze CRM. The agent writes
`robust_scale` and `zeta_prime` for nominated lab `L03` to `/root/results.json`.

Every figure below is recovered from the shipped artifacts named inline. Where a
`GATE2-PILOT-PROCEDURE.md` §5 field cannot be satisfied from those artifacts it is marked
**OPEN** rather than filled in.

## Result

| arm | n | passed | mean | pass@1 |
|---|---|---|---|---|
| no-skill | 30 | 0 | **0.000** | **0/30** |
| with-skill | 30 | 30 | **1.000** | **30/30** |

**Δ(pass@1) = +1.000.** Reward is binary {0,1}; read from each run's `result.json`
(`rewards.reward`) and cross-checked against `verifier/reward.txt`.

Both trial floors are met: `ERZA-OTS.md` §3 (≥5 per condition) and
`GATE2-PILOT-PROCEDURE.md` §1 (n≥3 per arm).

## The Δ-lever

**Gap type (b) — a distractor in the artifact the default grabs** (`ERZA-AUTHORING-STANDARD.md`
§2), carried on an **F2/F8** mechanism (formula selection + branch conditions, over a
multi-step routine with no droppable constraint).

`environment/data/question.json` hands the agent a `decoy_reference` block — a plain-mean
scale of `0.468704` and a standard-z of `-0.109806` — labelled "for orientation ONLY … do
not report these values." That is the classical grand-mean / sample-SD route: a *different
computation* from the robust one asked for. The withheld method is the ERZA-RB1 chain:
within-lab **median** reduction → Algorithm-A clamped robust location/scale iteration at
house clamp `c = 1.25` → closed-form **β(c) = 1.2288** Fisher-consistency debias (Φ/φ via
`math.erf`) → `u = 1.25·s*/√N` → `ζ' = (x_L* − x*)/u`.

**Δ-lever filter** (*"with the method undisclosed in the prompt, does the default approach
still get it right?"*): **No** — 0/30 no-skill runs passed.

## Competitor separation, in tolerance units

From `verifier/expected_values.json#control_gaps`. Tolerances: `robust_scale` ±0.004,
`zeta_prime` ±0.03.

| competing route | scale gap | ζ′ gap | discriminating? |
|---|---|---|---|
| `naive` (report the decoy) | 54.58× | 60.00× | yes |
| `no_beta_debias` | 23.71× | 36.14× | yes |
| `mean_reduction` (mean not median within lab) | **1.42×** | 64.74× | yes, but scale is the tight axis |
| `huber_clamp_c1p5` (c=1.5 instead of 1.25) | **1.30×** | **1.15×** | **marginal by design** |

**Recorded weakness.** The two nearest competitors clear the scale tolerance by only
1.30–1.42×, and `huber_clamp_c1p5` clears `zeta_prime` by 1.15× — the bundle's own ledger
calls it a *"WEAK/decorative lever; fails both outputs only marginally by design."* A ~15%
widening of either tolerance would admit a wrong method. The tolerances must not be relaxed
without re-measuring this table.

## Golden verification

- **Verifier derives.** `verifier/test_outputs.py` recomputes the ERZA-RB1 chain from the
  baked `measurements.json` at grade time and compares; it does not consult a stored key as
  its only authority. Graded tests: `test_robust_scale`, `test_zeta_prime`, gated by
  `test_plausible`.
- **Anti-memorisation control.** `test_isomorphic_invariance` permutes the lab identifiers,
  re-derives the reference on the relabelled instance, and asserts invariance — so the
  answer depends on the multiset of records, not on instance-specific names.
- **Independent recompute: OPEN.** `GATE2-PILOT-PROCEDURE.md` §5 requires the golden be
  confirmed by *a second formulation, not the oracle's own pipeline*. This bundle ships no
  `build/independent_check.py` and no second implementation. The golden is currently
  **single-anchored** on `oracle/generate.py`. This is the known weakness §5 names; it is
  recorded here rather than papered over.

## Data source and licence

**Synthetic**, and permitted as such: `ERZA-AUTHORING-STANDARD.md` §4 allows synthetic
where a real artifact is genuinely infeasible, provided it is seed-pinned, documented, and
recorded as synthetic in provenance — which this section does. `oracle/generate.py` emits
both the agent-visible tables and the hidden golden deterministically from **`SEED =
20260720`**; regenerating with that seed reproduces byte-identical inputs and reference
values. No third-party data is redistributed, so the Access and Licence gates of
`FAILURE-TASK-CURATION-GUIDE.md` §2 do not bind.

Caveat the standard itself raises: a synthesised artifact risks encoding the gap it tests.
ERZA-RB1 is an in-house SOP with no published counterpart, so recall from weights is not a
plausible route — consistent with 0/30 no-skill.

## Paired-design integrity

Verified across all 60 runs from `config.json`:

- **One frozen byte-set.** `source.file_hashes` yields exactly **1 distinct digest set
  across all 60 runs** — both arms read identical bundle bytes, as
  `GATE2-PILOT-PROCEDURE.md` §1 requires.
- **Single-variable arms.** The only `config.json` keys differing between arms are the
  skill-mounting keys (`skill_mode`, `skill_source`, `include_task_skills`,
  `requested_skills_dir`, `effective_skills_dir`, `skills_sandbox_dir`) plus `started_at`.
  No timeout, model, or sandbox asymmetry — the defect that invalidated `e9474235`.
- **Model:** `claude-opus-4-8` on both arms. Pilot dated 2026-07-20.

## Excluded runs

**None.** All 60 runs produced a scored answer. No run was dropped for no-output or
transport crash, so the `GATE2-PILOT-PROCEDURE.md` §3 zero-triage does not apply: every
scored 0.0 in the no-skill arm is a genuine wrong answer.

## Frozen content hash

- **Recorded** (`uuid_provenance.json#canonical_content_hash`):
  `c80c024feed46785b2f5fed9c7b9c8f8ebd9d87d123ca9fe3309c163a9777365`
- **Recomputed under `forge.task_id.v1`** (recipe: sorted
  `relpath:sha256`, newline-joined, excluding `uuid_provenance.json`, `.DS_Store`, `*.pyc`
  and cache dirs): `cc917a05bb1028339f32a3d662aeda8e19758b3213450c547b4bccae6babc6fd`,
  which derives `task_id 8ede7e33-44a5-5296-bac6-00c0fbf312b3`.

**These disagree, and the discrepancy is OPEN.** No manifested file has drifted — every one
of the 10 recorded `sha256` values matches the file on disk — so the bundle is internally
consistent and its bytes are intact. What does not reproduce is the digest-of-digests. The
same mismatch is reported by the third-party consistency audit (`C identity cch matches
record FAIL`) and by the QC toolkit (`I-01`). It affects `48f28e86` and `903d6f33`
identically; every other deliverable reproduces exactly, so the recipe itself is sound and
this is specific to these three bundles.

Do not "fix" this by rewriting `uuid_provenance.json`: that would mint a new `task_id` and
rename both this directory and `dataset/d427488f-…`, which cascades into `samples/`, a
published repository written around this id.

## Known gaps carried by this bundle

Recorded so they are not rediscovered as new.

1. **`verifier.hardening.cleanup_conftests` is absent** from `task.md` —
   `ERZA-AUTHORING-STANDARD.md` §4 lists it as a hard rule binding every authored task, so
   the agent is not blocked from overwriting the verifier. Fixing it edits the frozen
   surface and re-mints the id.
2. **`modality: tabular` is not in the committed `harness/taxonomy.yaml`** — present only in
   an uncommitted working-tree edit, so CI's `lint_taxonomy.py` rejects this bundle.
3. **No process verifier** (`verifier/process/` absent), so there is no trajectory-level
   channel for this task.
4. **`samples/README.md` under-reports this pilot** as "3 per condition = 6 graded runs"
   and describes itself as sitting below the ≥5 bar "by design". The `samples/` submodule
   ships a 3+3 subset; the evidence above is 30+30.
