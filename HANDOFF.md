# HANDOFF — erza-samples session, 2026-08-04

Working state for whoever picks this up. Supersedes the 2026-08-03/04 handoff. Records what was
done this session, what is open, and the traps that cost time across both sessions.

## Where things stand

| | |
| :--- | :--- |
| `erza-samples` | `main`, pushed to `EtharaOrion/erza-samples` — grids + layout commit, then README + figure commit |
| `erza` (knowledge repo) | `samples` submodule bumped to the new head and pushed; unrelated local edits to `DIRECTIVE.md`/`VERDICT.md`/`audit/*` were left untouched |
| Repo contents | **10 tasks, 60 runs, all fully paired**, uniform bundle layout |
| Headline | **A = 0.299, B = 1.000, Δ = +70.1 pp over all 10 tasks** (excl. `48f28e86`: +74.2 pp) |

Commit identity is `Agasthhya <agasthhya.sharma30@gmail.com>`, GitHub-linked. **No Claude
attribution in any commit message in either repo** — explicit standing requirement. Keep it that way.

## Done this session

1. **Verified the `20840ce0` / `c7faca71` 3+3 grids end-to-end** before shipping: uniform 1800 s
   budgets both arms, one `prompts.json` sha per task, one `task_digest` per cohort (distinct from
   the superseded 2026-07-29 generation they replace), no oracle runs, headers agree with the raw
   pytest records on all 12 runs, byte-identical to the source pack, `uuid_provenance` re-seals and
   `uuid5(namespace, hash)` re-derives both task ids. Their with-skill trajectories show real Skill
   launches; no-skill show none.
2. **Standardised the three newer-schema bundles** (`029f6a19`, `20840ce0`, `c7faca71`) to the
   house layout, mirroring exactly what the 2026-07-31 standardisation did to the older seven:
   `solution/TRUTH.md` → top-level `TRUTH.md`; `solution/` → `oracle/` (dropping
   `_truth_template.py`, `grounding.yaml`, `recompute.py`); `build/` deleted; `graded_cases.json`
   added (exact, `needs_review: false` — the parametrized `test_graded_case[...]` set);
   `uuid_provenance.json` re-sealed 2026-08-04 with the original task_id kept. All 10 seals verify;
   `graded_cases.json` is uniformly the only file outside each seal. `tests/` and `environment/`
   were deliberately untouched (frozen graded bytes).
3. **Built the difficulty-tier figure** `assets/score_by_tier.png` (regenerate with
   `uv run --with matplotlib python3 assets/score_by_tier.py`). Five outcome-based tiers on the
   unaided mean score A, user-fixed cut-points: Expert A=0 (3 tasks) / Hard 0–0.3 (2) /
   Medium 0.3–0.6 (2) / Easy 0.6–0.8 (2) / Trivial >0.8 (1). Two series (no-skill, with-skill) plus
   green per-tier Δ connectors. Palette is the house-validated trio from vega's `figures.py`.
4. **Rewrote README** for the fully-paired reality. The reproduction snippet prints the headline
   verbatim (`A = 0.299  B = 1.000  delta = +0.701  g = 1.000`) — run it before touching any
   number. Claims verified against artifacts before shipping: `result.json` `rewards.reward` ↔
   `reward.txt` agree on 60/60 runs; Skill launches 30/30 curated vs 0/30 unaided; isomorphic
   guards on 9/10 tasks (`903d6f33` is the one without); cost table from
   `agent_result.{cost_usd,n_output_tokens,n_tool_calls}` means.
5. **`20840ce0` / `c7faca71` inclusion decision: kept.** They fail the no-skill floor (A = 0.667,
   0.882) and the README's Known issues says so plainly; they ship because their pairing is clean
   and they carry the sample's only real partial credit. If they are ever dropped, the reason must
   be charter validity, not the (larger) headline that results.

## Open items

1. **Two unreferenced figures**: `assets/efficacy.png` and `assets/attractor.png` chart `d427488f`
   alone and are cited nowhere. Regenerate across 10 tasks or delete. User previously said ignore.
2. **Teammate not told**: the `054b4b8` restructure (by shraiykhaddar) was force-merged over on the
   user's instruction last session; they will see their layout reversed on next pull.
3. **`48f28e86` stays but is quarantined in prose** — screening bundle, budgets confounded
   (700/900/1200 s), no Δ quotable, wrong header on run_1. The README's excl-column is the honest one.
4. **`d427488f`** remains the weakest task (2 graded cases → scores only 0/0.5/1).
5. **Erza production bar** is ≥ 5 trials/arm with paired-bootstrap CIs; this sample is n=3 by design.

## Known defects in the shipped data (unchanged from last session unless noted)

- `48f28e86` no-skill/run_1 header says 2/12; the pytest record says 0/12. Only such disagreement
  in all 60 runs.
- `n_skill_invocations` is always 0, even on curated runs. Use the trajectory.
- `agent/claude_agent_acp.txt` is 0 bytes in a subset of runs.
- `d427488f` verifier artifacts re-serialised (CTRF→JUnit); no score changed; no `egress/probe.txt`
  exists for it anywhere.
- **New:** `20840ce0` and `c7faca71` also ship without `egress/probe.txt` — the 2026-08-04 run
  cohort was captured without egress probes; the only probes in the source pack for these tasks
  belong to quarantined superseded runs. Do not fabricate one.

## Traps — read before touching the data

**1. Score ONLY from `verifier/pytest_output.txt`.** The `test cases passed` header lied once
(`48f28e86`); `graded_cases.json` on the seven older tasks is name-pattern derived and
`needs_review: true` (on the three newer tasks it is exact); `verifier/results.xml` is absent on
some tasks and `verifier/process/results.xml` is the *process rubric* suite, not outcome cases.
Guard-name filter (older tasks): `plausib|isomorphic|invarian|guess_resist|frozen_golden|`
`frozen_reference|tolerances_are|load_bearing|not_the_|wood_anderson_calib|golden_matches`.
On the newer tasks graded = `test_graded_case[...]` prefix, denominators 31/31/51.

**2. A UUID does not locate a task.** Three non-agreeing ids per bundle; trajectory dirs named for
whichever id was current at recording. `grep -rl <uuid> --exclude-dir=.git` and the source pack's
`MANIFEST.json` `slug_by_task_id`.

**3. Check `task_digest` before trusting a run** (frozen-bytes binding in `result.json`). The
digest recipe is harness-internal — it is *not* the `uuid_provenance` canonical hash and could not
be recomputed locally; what is checkable is cohort uniformity and byte-identity to a sealed source.
The superseded `c7faca71` generation scored differently (39/51 vs 43/51) on the same prompt.

**4. The unpublished pack quarantines bad runs in `_`-prefixed dirs** (`_oracle_gate_runs/`,
`_stale_prompt_runs/`, `_superseded_generation_runs/`). Never glob them into an import.

**5. Layout changes require a re-seal.** `uuid_provenance.json` manifests cover every bundle file
(except `graded_cases.json` and itself). Moving or deleting a file breaks the seal; the established
procedure is: restructure, rebuild the manifest, keep the original `task_id`, and date the `format`
note ("re-sealed <date> after the format change; supersedes the pre-format seal"). Re-sealed
bundles no longer satisfy `uuid5(namespace, hash) == task_id` — that is the norm for all seven
older tasks and now all ten.

**6. Old macOS `rsync` (2.6.9) does not create intermediate directories** — `mkdir -p` first.

**7. `git -C samples …` runs against the PARENT repo if `samples/` does not exist.** This hard-reset
`~/erza` once. Verify the path exists first. Also: `~/erza` carries unrelated uncommitted edits
(`DIRECTIVE.md`, `VERDICT.md`, `audit/*`) — never sweep them into a submodule-bump commit; stage
`samples` only.

## Findings worth carrying forward

- **Near-binary scores are a science-task property, not a corpus property.** The 8 natural-science
  tasks: 4 of 24 unaided runs strictly in (0,1) — one procedural decision propagates into every
  graded case. The 2 office tasks: 6 of 6 unaided runs strictly in (0,1) — their graded cases
  decompose into separable units (fixed-width field groups; per-pairing legality). Multi-unit tasks
  are the route to graded difficulty, matching the earlier conclusion that a difficulty ladder
  cannot be built from single-lever tasks.
- **Difficulty must be measured, never claimed** — `task.toml` declares all 10 `hard`; observed A
  spans 0.000–0.882. Structural proxies (oracle LOC, case count, skill size) do not track observed
  difficulty in this corpus; checked and rejected for the tier axis.
- The research-verdict notes from the previous handoff (anti-shortcut controls ahead of market
  norms; benchmark-shape vs training-environment-shape; process verifier as diagnostic, not reward)
  remain valid and live in the previous handoff in git history (`HANDOFF.md` @ `10127b7`..).

## Memory

Notes in `~/.claude/projects/-Users-AgisSpectre-erza-samples/memory/` (auto-loaded):
`samples-import-source`, `partial-score-sources`, `erza-task-id-lineage`, `samples-readme-template`.
