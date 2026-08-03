# PROVENANCE — tidal-harmonic-prediction (`e9474235-0323-5e54-9171-c5b80089ad7e`)

> # ⛔ SUPERSEDED 2026-07-28 — NOT PART OF THE DELIVERABLE SET. DO NOT QUOTE ITS Δ.
>
> The two arms were **not single-variable**: `no-skill` ran at `agent_timeout_sec=900`
> and `with-skill` at `1200`, so the curated arm had 33% more wall-clock. Two no-skill
> runs then died BUDGET_EXHAUSTED, leaving n=3 scored. The reported Δ is confounded with
> the time budget and is not a measurement of skill efficacy.
>
> Superseded by `dcf94db0-cec4-52c9-9532-4170e8981646`, which declares 1800 s for both
> arms so the comparison is symmetric by construction. The runs below are retained as
> evidence of the defect, per ERZA-OTS §3 (measurements are labelled, never dropped).
>
> **The successor is not published.** As of 2026-07-28 `dcf94db0-…` exists only at
> `harness/tasks-salvage/`, which is not pushed to either repo, so a reader of
> `dataset/` or `trajectories/` cannot resolve that id. Until it is piloted and
> pushed, **there is no delivered tidal-harmonics task** and no Δ for this family.

Paired skill-efficacy pilot for the RFP phase. Model under test: **Claude Opus 4.8**
(`claude-opus-4-8`). Authored 2026-07-25. Disposition: **PASS** (erzaqc clean;
draft-maturity RFP pilot, n=5 per arm).

## Task
Predict the tide height (metres above chart datum) at **three coastal tide gauges** for
**four UTC instants** each — a 12-item grid — by harmonic tide prediction (NOAA CO-OPS /
Schureman). One test case per (gauge, instant); a case passes iff |reported − reference|
≤ 0.10 m; Score = cases passed / 12.

## Result (the headline)
| arm | n | rewards | mean | pass@1 |
|---|---|---|---|---|
| no-skill  | 5 | 0.0833, 0.0833, 0.0833, 0.0833, 0.0833 | **0.083** | **0 / 5** |
| with-skill | 5 | 1.0, 1.0, 1.0, 1.0, 1.0 | **1.000** | **5 / 5** |

**Δ = 0.917** (mean) · **Δ(pass@1) = 1.0**. No-skill fails on every run (mean well below
the 0.5 floor); with-skill is perfect on every run. All ten runs share one frozen
`task_digest` — `sha256:eb41043a186e09d5871762ca6d64c1fd8437d2260795951c58b0c41acbd47d01`.

## Identity and hashes
- `task_id` = `e9474235-0323-5e54-9171-c5b80089ad7e` = `uuid5(FORGE_NAMESPACE, canonical_content_hash)`.
- `canonical_content_hash` = `9393265ba58e03e1f2ce3b48ee2ed83955b7dc8d9c0b235488b588d858e711de`
  (sha256 over sorted `relpath:sha256` manifest, excluding `uuid_provenance.json`; see the bundle's `uuid_provenance.json`).
- **Quasi-paired digest note:** benchflow's `task_digest` (`eb41043a…`) hashes every regular file
  under the task dir and therefore differs from `canonical_content_hash` (the manifest construction).
  Both arms share the SAME `eb41043a…`, so the paired comparison is on identical frozen bytes.

## The lever (Gate A: real, cited, non-recallable AND non-fetchable)
The withheld quantity is each gauge's **harmonic-constant table** — per-constituent amplitude
`H_i` and Greenwich phase lag `g_i` — carried only in the skill
(`environment/skills/schureman-tide-harmonics/references/harmonic_constants.json`, cited to
NOAA CO-OPS). These are empirical, station-specific (no closed form; set by local bathymetry
and resonance) and differ completely gauge to gauge. The gauges are the real NOAA stations
8413320 (Bar Harbor ME), 9432780 (Charleston OR), 9459450 (Sand Point AK); their identities
are withheld grader-side (`build/station_map.json`) and the agent sees only **opaque labels**
(TG-A/B/C) with no id, name, or coordinate. So the constants are neither recallable NOR
fetchable: a no-skill agent has no key to look them up.

## Gate B — no-skill genuinely fails (real wrong answers, no recall, no fetch)
Every no-skill run produced a well-formed `results.json` and failed on value (1/12 — the one
item that happens to sit near the orientation distractor). It is a real wrong answer, not a
stall. The trajectories show the agent (22 tool calls, `curl`, exhaustive filesystem search)
explicitly concluding it **cannot** obtain the constants: *"each gauge's tidal constituent
table … NOT present anywhere in the container … cannot fit harmonics from a single
instantaneous sample … this is a fallback, not a genuine harmonic prediction."* No run
reconstructed the constants from memory or fetched them.

**Egress note (important for reviewers):** the agent sandbox is NOT network-isolated —
benchflow re-enables outbound network for LLM-agent runs (`sandbox/setup.py`), and
`disallow_web_tools` only disables the built-in web-search *tool*, not bash `curl`. Verified:
an accepted task's no-skill run (`stream-discharge-rating`) issued live `bing.com` searches
from the sandbox. This task's separability therefore does NOT rely on network isolation; it
relies on the withheld station identity (anonymization), so it holds even with full egress.

## Gate C — with-skill passes (skill discovered + used)
Every with-skill run read `harmonic_constants.json` + `tidal_constituents.json`, implemented
the Schureman synthesis (Doodson arguments, nodal factors), and scored 12/12. The prompt
never names the skill (`task.md` body references only the method, "harmonic tide prediction").

## Gate D — trustworthy golden
Golden derived by `oracle/tide_predict.py` (`oracle/generate.py`), never hand-typed; oracle
scores **1.000** on the frozen bytes (twice; `erzaqc gate1 --twice`). Cross-checked three ways
(`build/independent_check.py`): (1) a distinct speed-propagation code path reproduces it to
0.000 m; (2) **utide** (Codiga 2011), an independent implementation, re-analyses two years of
oracle output and recovers the shipped constants to 0.006 m amplitude / 0.14° phase (dominant
constituents); (3) NOAA CO-OPS published predictions agree to ≤ 0.168 m (documented residual =
NOAA's operational seasonal-Sa handling vs a pure published-constituent harmonic sum). The
rederivation gate (`verifier/process/verification/rederivation_test.py`) is BIT-IDENTICAL.

## Gate E — no leakage
`environment/Dockerfile` copies only `data`. No NOAA id/name/coordinate and no harmonic
constant appears in `task.md` or `environment/data`; the constants live only under
`environment/skills` (with-skill mount). The `task.md` placeholder is `9.999` (≫ tolerance
from every golden). Grader-side files (`oracle/`, `verifier/`, `build/`, `truth.md`) are
unreachable by the agent. erzaqc leak checks: clean.

## Gate F — distractor present and effective
`question.json.decoy_reference` gives one recent observed water level per gauge, framed
"for orientation only." Reporting it (or the mean level) at every instant misses by 8.4× /
7.3× tolerance on average (control-gap ledger, `verifier/expected_values.json`); the no-skill
runs took exactly this route and scored 1/12.

## erzaqc QC
Deterministic bundle layer: **PASS**, 0 findings. `gate1 --twice`: oracle reward 1.0 + determinism.
(0 BLOCKER / INVALIDATING / MAJOR; no L-01/L-02 — the constants are real and cited.)

## Caveats
- **n = 5 per arm** (RFP pilot bar). Not the larger statistical / paired-bootstrap bar; that is
  out of scope for this phase.
- The oracle vs NOAA operational residual (≤ 0.168 m) is documented above; the golden is the
  harmonic synthesis (utide-verified), not the operational product.
- The task is robust regardless of sandbox network policy (non-fetchable lever); it does not
  depend on `network_mode: no-network` being enforced.

## Reproduction
```
cd harness
bench eval run --tasks-dir tasks/tidal-harmonic-prediction --agent oracle --sandbox docker   # 1.000
# no-skill (x5) then with-skill (x5), phase-separated, bridge on 127.0.0.1:8765:
bench eval run --tasks-dir tasks/tidal-harmonic-prediction --agent claude-agent-acp \
  --model claude-opus-4-8 --sandbox docker --skill-mode no-skill
bench eval run --tasks-dir tasks/tidal-harmonic-prediction --agent claude-agent-acp \
  --model claude-opus-4-8 --sandbox docker --skill-mode with-skill \
  --skills-dir tasks/tidal-harmonic-prediction/environment/skills
python3 tasks/tidal-harmonic-prediction/build/independent_check.py   # utide + NOAA cross-checks
```
