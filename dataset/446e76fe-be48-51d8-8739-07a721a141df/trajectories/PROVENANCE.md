# PROVENANCE — 446e76fe-be48-51d8-8739-07a721a141df

**Label: POSITIVE — ABOVE-FLOOR, not a clean keeper.** Δ = **+0.800**, 95% paired-bootstrap
CI **[+0.400, +1.000]**, Fisher exact one-sided **p = 0.0238**, n = 5/5.

> **Why the qualifier.** `GATE2-PILOT-PROCEDURE.md` §4 makes SHIP-eligibility conditional on
> three things: oracle = 1.0, **no-skill below floor** (for a binary task: 0 on *every*
> scored run), and Δ > 0. This task meets the first and third. It does **not** meet the
> second — `no-skill/run_4` scored 1.0. §4 covers that case explicitly: *"If the no-skill
> floor is borderline (one of three no-skill runs passes), the task is above-floor — record
> it but do not count it as a clean keeper unless it clears the floor."* So the Δ sign is
> sound and the task ships, but it must not be quoted as a clean floor result.
>
> **The pass is a genuine solve, not catalogue recall** — which is the honest reading, and
> the check this bundle's own control ledger asked for (*"Watch the re-pilot for a no-skill
> pass with no amplitude measurement in its trajectory"*). Evidence, from
> `claude-opus-4-8/no-skill/run_4/trajectory/llm_trajectory.jsonl`: the run drives `obspy`
> (9 hits), calls `remove_response` (7), simulates a Wood-Anderson (7), reasons explicitly
> about *"**zeros** at the origin (it's a displacement seismometer…)"*, uses the IASPEI
> magnification `2080` (7) and the Hutton & Boore distance term (7), and reports
> ML = 5.15 against reference 5.2179 (tol 0.3). The strings `5.25` and `catalog` appear
> **zero** times. The residual recall risk recorded in `control_gaps` did not materialise.

**Task.** Local magnitude (ML) of a real earthquake from one broadband station record
(`local-magnitude-seismology`). Supersedes `999a91d3-22b0-5514-9e36-0d41ddcef6d4`, whose
golden was wrong by 0.80 ML — see `.omo/DEFECT-999a91d3-wrong-golden.md` and the withdrawal
banner on that task's PROVENANCE.md.

## The lever

The Wood-Anderson instrument responds to ground **displacement** through
`H(s) = G·s²/(s² + 2hω₀s + ω₀²)` — **two** zeros at the origin. The trace has already been
deconvolved to displacement, so both factors of `s` must be supplied. The **one-zero** form
is the response to *velocity* and is what most circulated obspy code contains; applied to a
displacement trace it understates the amplitude by |2πf| ≈ 6.26 at this record's 0.996 Hz,
i.e. **0.796 ML = 2.654× the graded tolerance**.

The Skill teaches the two-zero form *and* the three-line check that settles it without
seismological judgement: drive the paz with a 1 mm displacement sinusoid and confirm a
~2080 mm deflection (the Wood-Anderson's defining static magnification). One zero gives ~65.

## Result (claude-opus-4-8, benchflow, Docker, egress-firewalled)

| arm | n | per-run reward | mean | Wilson 95% |
|---|---|---|---|---|
| no-skill | 5 | 0, 0, 0, **1**, 0 | 0.200 | [0.04, 0.62] |
| with-skill | 5 | 1, 1, 1, 1, 1 | 1.000 | [0.57, 1.00] |

**Δ = +0.800 · 95% CI [+0.400, +1.000] · Fisher one-sided p = 0.0238 · g = 1.000**

`g` is **degenerate** here: the curated arm saturates, so g = 1.000 for any Δ that closes
the headroom. It says the Skill closed the gap, not how large the effect was. Quote Δ.

The CI is a percentile bootstrap over 5 trials per arm; it cannot resolve below 1/5 and
should be read as a coarse floor on uncertainty, not a precision claim.

## Attribution — verified run by run, not assumed

| | with-skill | no-skill |
|---|---|---|
| opened the Skill | 5/5 (7–9 references each) | **0/5** |
| wrote `zeros=[0j, 0j]` | 5/5 | 1/5 |
| wrote the one-zero form | 0/5 | 4/5 |

The four no-skill failures each used the one-zero velocity paz and landed on 2.21–4.39
against a golden of 5.2179. Every with-skill run opened the Skill and used two zeros. This
is the designed lever operating, not a correlation.

**The one no-skill pass is real and is kept.** `no-skill/run_4` tried both paz forms,
reasoned about the 2080 static magnification (64 mentions of it), submitted 5.15, made zero
network calls and never mentioned a catalogue magnitude. The base model *can* reach the
convention unaided by running the same check the Skill teaches — it just usually does not.
That is why Δ is 0.800 and not 1.000, and the task is more informative for it.

## Frozen-bytes binding

All 10 packaged runs share `task_digest`
`sha256:cff6ab13598f28febbc61fc3d1b6d1463b5aca502f6c1345849cb95cd95fd216` (erzaqc X-01).
Arms differ in `--skill-mode` and nothing else; `agent.timeout_sec = 1800` is read from
`task.md` by both, so the asymmetric-budget defect that confounded `e9474235` cannot occur
by construction.

**Gate 1:** oracle reward 1.0, twice, deterministic (O-03/O-04).

## Network conditions

Every run carries `egress/probe.txt` recording `inet=BLOCKED:URLError` with the bridge
gateway reachable. This is the first task in the set with egress evidence on **every** run,
and it is not cosmetic: an earlier attempt at this pilot ran without the firewall, reached
SCEDC over FDSN, and the same no-skill run_1 scored **1.0** instead of **0.0**. See
`.omo/DEFECT-run-one-no-egress-firewall.md`.

## Exclusions (R-10 — recorded, never silent)

| run | reason | disposition |
|---|---|---|
| ns/run_1, ws/run_1 (first attempt) | ran without the egress firewall; reached the live internet | quarantined, re-run |
| ws/run_5 (first attempt) | docker refused the network: "all predefined address pools have been fully subnetted"; 0 tool calls | excluded, re-run |

No run was excluded for its score. Each carries a `WHY.txt` under `harness/jobs/`.

## Why the catalogue magnitude was removed from `question.json`

The predecessor handed the agent `catalog_magnitude: 5.25` as a decoy. That was defensible
only while the golden was wrong: the corrected ML is 5.2179, which is **0.107× tolerance**
from 5.25, and an answer of exactly 5.25 was verified against the live verifier to score
**reward 1**. The decoy had become a free pass, so the field is no longer supplied.

**Residual risk, recorded not hidden.** The event is real and catalogued, so a model could
recall Mw ≈ 5.25 from the origin time and location and land inside tolerance without
measuring. Measured counter-evidence: none of the 5 no-skill runs mentioned 5.25, and the
one that passed did so by computation. The guardrail
`verifier/process/rubrics.json#R15` carries weight **−5** for this
reason — it is the only channel that can see a run which measured nothing, because the
outcome verifier cannot distinguish a recalled 5.25 from a measured 5.2179.

## Verifier

`verifier/test_outputs.py` **recomputes** ML from the baked `waveform.mseed` and
`station.xml` and asserts the cached `ref_ml` against that derivation
(`test_golden_matches_independent_recompute`); the graded comparison uses the derived
value. This is the root-cause fix for the predecessor's defect — a stored answer key cannot
catch an error it inherited. It also asserts the instrument's own definition
(`test_wood_anderson_calibration`: 1 mm in → ~2080 mm out), names the dominant wrong path
(`test_not_the_velocity_form`), and checks procedure-definedness under a pure amplitude
rescale (`test_isomorphic_invariance`). Degenerate inputs — missing file, empty, malformed
JSON, NaN, Infinity, null, string, wrong key, array — all score 0 without crashing.
