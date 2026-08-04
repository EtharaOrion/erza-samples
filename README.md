<p align="center">
  <img src="assets/hero.png" alt="Erza-Samples — agent-skills efficacy, measured in paired runs" width="880">
</p>

<p align="center">
  <a href="#summary"><img alt="Built by Ethara.AI" src="https://img.shields.io/badge/built%20by-Ethara.AI-ee00ee.svg"></a>
  <a href="#metric-skill-efficacy-δ"><img alt="Metric: paired skill efficacy" src="https://img.shields.io/badge/metric-paired_skill_efficacy-35d0ba.svg"></a>
  <a href="#scoring-methodology"><img alt="Verifier: network-sealed" src="https://img.shields.io/badge/verifier-network--sealed-845EF7.svg"></a>
  <a href="#verification-and-quality-assurance"><img alt="Efficacy: measured, never claimed" src="https://img.shields.io/badge/efficacy-measured%2C_never_claimed-ff6b6b.svg"></a>
</p>

<p align="center"><sub>
  <a href="#summary">Summary</a> · <a href="#repository-layout">Layout</a> · <a href="#metric-skill-efficacy-δ">Metric</a> · <a href="#the-tasks">Tasks</a> · <a href="#difficulty-tiers">Tiers</a> · <a href="#results">Results</a> · <a href="#analysis">Analysis</a> · <a href="#task-structure">Structure</a> · <a href="#scoring-methodology">Scoring</a> · <a href="#reproduction">Reproduction</a> · <a href="#verification-and-quality-assurance">Verification</a>
</sub></p>

# Erza: Agent-Skills Efficacy Sample

**Erza measures whether a curated Skill changes what an agent can actually do, not whether a model
is good at a domain.** Every task is run twice under identical conditions — same container, same
prompt, same verifier — differing only in whether a curated, domain-specific Skill is mounted. The
headline measurement is **Skill efficacy (Δ)**: the paired difference the Skill makes on the same
task.

A task earns its place in Erza only when it is hard enough to defeat the no-Skills arm **and**
separable enough that the Skill recovers it. A task the model already passes unaided is below the
bar; a task neither arm can solve measures difficulty, not Skill efficacy.

This is a **10-task orientation sample**: ten complete task bundles and **60 graded agent
trajectories** (Claude Opus 4.8). Every task carries the full paired grid of 2 conditions × 3 runs.
The dataset format, trajectory format, and scoring are identical to the production Erza harness.

> **Scope.** This sample exists to show the *shape* of an Erza deliverable end-to-end. Three runs
> per arm cannot establish an efficacy estimate — see [Limitations](#limitations).

## Summary

| Property            | Value                                                                          |
| :------------------ | :----------------------------------------------------------------------------- |
| Tasks               | **10**, all fully paired                                                        |
| Domains             | natural-science (7) · office-white-collar (3), across 10 subcategories         |
| Difficulty          | `hard` declared on all 10; **5 outcome-based tiers** measured on this sample (see [Tiers](#difficulty-tiers)) |
| Models evaluated    | Claude Opus 4.8 (`claude-opus-4-8`)                                            |
| Conditions per task | no-Skills (A) · curated-Skills (B)                                             |
| Runs & grid         | **60 graded runs** — full 2 × 3 on all 10 tasks, no gaps                       |
| Graded cases        | 1 to 51 per task (180 in total)                                                |
| Score               | graded cases passed / total, per run                                           |
| Network             | `no-network` on all 10; verifier is deterministic `pytest`, no LLM judge       |

**Measured on this sample**, over all 10 paired tasks:

| Metric                                   |     10 tasks | Excl. `48f28e86` (see [Known issues](#known-issues)) |
| :--------------------------------------- | -----------: | ---------------------------------------------------: |
| no-Skills mean score (A)                 |    **0.299** |                                            **0.258** |
| curated-Skills mean score (B)            |    **1.000** |                                            **1.000** |
| **Skill efficacy (Δ = B − A)**           | **+70.1 pp** |                                         **+74.2 pp** |
| Normalized gain `g = Δ / (1 − A)`        |     **100%** |                                             **100%** |
| no-Skills pass rate (all cases passed)   | 13.3% (4/30) |                                          7.4% (2/27) |
| curated-Skills pass rate                 | 100% (30/30) |                                         100% (27/27) |
| Mean agent cost, no-Skills               |      $1.1677 |                                              $1.1715 |
| Mean agent cost, curated-Skills          |      $0.3484 |                                              $0.3500 |

## Repository layout

```text
erza-samples/
├── README.md                 # this document
├── assets/                   # figures
└── dataset/                  # one self-contained directory per task-id
    └── <task-id>/
        ├── task.toml         # metadata, resource and network policy
        ├── instruction.md    # the prompt presented to the agent
        ├── environment/      # sandbox image, mounted inputs, curated Skill
        ├── oracle/           # reference solution + generator, never mounted
        ├── tests/            # deterministic verifier + process rubrics
        └── trajectories/     # the graded agent runs for this task
            └── claude-opus-4-8/<condition>/run_N/ ...
```

`condition ∈ {no-skill, with-skill}`, `N ∈ {1, 2, 3}`. **Each task directory is self-contained**:
the bundle and every run that measures it live together, so a task can be read, rebuilt and
audited without reference to anything outside its own folder.

## Metric: Skill efficacy (Δ)

Because both conditions run the **same** task in the **same** container from a byte-identical
prompt, Δ is a paired difference at the (task, condition) level, not an unpaired-pool comparison:

```text
per-run score:    r = graded cases passed / graded cases total
per-task score:   s_{t,c} = mean over k runs of r
condition mean:   Score(c) = (1/N) Σ_t s_{t,c}
efficacy:         Δ = Score(curated) − Score(no-Skills)
normalized gain:  g = Δ / (1 − Score(no-Skills))
```

`g` expresses Δ as a fraction of the headroom the Skill could possibly recover.

**Graded cases, not all test cases.** Each verifier ships two kinds of test: **graded cases**,
which check the answer, and **guards** (plausibility, isomorphic-invariance, frozen-golden
recompute), which check the *grader*. Only graded cases enter the score. A guard passes for free
whenever the output is well-formed, so counting guards inflates the floor — see
[Known issues](#known-issues) for a run where the shipped header does exactly that.

## The tasks

| Task-id    | Domain / subcategory                              | Graded cases | What the Skill supplies                                      |
| :--------- | :------------------------------------------------ | -----------: | :----------------------------------------------------------- |
| `6f76812f` | natural-science / ionospheric-physics             |           12 | GNSS signal-bias referencing for arc-mean vertical TEC        |
| `c59f8b2a` | natural-science / geodesy                         |           12 | antenna phase-centre correction                               |
| `d427488f` | natural-science / metrology                       |            2 | ERZA-RB1 robust interlaboratory consensus                     |
| `029f6a19` | office-white-collar / official-population-statistics |        31 | NHIS primary-race bridging                                    |
| `e9474235` | natural-science / oceanography                    |           12 | tide-gauge height reduction                                   |
| `446e76fe` | natural-science / seismology                      |            1 | IASPEI Wood-Anderson local magnitude                          |
| `903d6f33` | natural-science / astronomy                       |           16 | source-position / astrometric reduction                       |
| `48f28e86` | natural-science / geomagnetism                    |           12 | IGRF spherical-harmonic declination reduction                 |
| `20840ce0` | office-white-collar / tax-information-reporting   |           31 | fixed-width filing-record emission                            |
| `c7faca71` | office-white-collar / aviation-regulatory-compliance |        51 | flight-duty-period legality                                   |

Every task follows the same shape: a domain-specific **house procedure** the agent must execute
exactly, and a plausible **decoy** in the inputs that a competent but unaided run tends to fall
into. `d427488f`, for example, hands the agent a naive plain-mean scale of `0.468704` labelled
"for orientation ONLY", where the graded answer is the robust clamped scale `0.250368`.

## Difficulty tiers

The 10 tasks are stratified into five tiers by **observed difficulty on this sample**: each task's
unaided mean score A, binned at fixed cut-points. This is an outcome-based stratification computed
from the runs shipped here — the tiers describe what the model actually experienced, not a property
claimed in advance (`task.toml` declares all 10 `hard`).

| Tier        | Rule (unaided A) |   n | Tasks                              | mean A | mean Δ |
| :---------- | :--------------- | --: | :--------------------------------- | -----: | -----: |
| **Expert**  | A = 0 exactly    |   3 | `6f76812f` `c59f8b2a` `d427488f`   |  0.000 | +1.000 |
| **Hard**    | 0 < A < 0.3      |   2 | `029f6a19` `e9474235`              |  0.052 | +0.948 |
| **Medium**  | 0.3 ≤ A < 0.6    |   2 | `446e76fe` `903d6f33`              |  0.333 | +0.667 |
| **Easy**    | 0.6 ≤ A < 0.8    |   2 | `20840ce0` `48f28e86`              |  0.667 | +0.333 |
| **Trivial** | A ≥ 0.8          |   1 | `c7faca71`                         |  0.882 | +0.118 |

![Mean score by difficulty tier](assets/score_by_tier.png)

The green connectors are the per-tier Δ. Two reading notes: the no-Skills line falls across tiers
*by construction* (the tiers are binned on it); the measured content is the curated line sitting at
100% in every tier — the Skill closes the entire remaining gap wherever the unaided model lands.
And with 1–3 tasks per tier, tier means are descriptive, not estimates. `48f28e86` sits in the Easy
tier but its runs are not a valid paired comparison (see [Known issues](#known-issues)); the tier
figure includes it for completeness.

## Results

Per-run score is **graded cases passed / total**, recovered from each run's own
`verifier/pytest_output.txt`. Sorted by no-Skills score:

| Task       | Cases |  no-skill run_1 |  run_2 |  run_3 |     **A** | with-skill (3 runs) | **B** |     **Δ** |
| :--------- | ----: | --------------: | -----: | -----: | --------: | ------------------: | ----: | --------: |
| `6f76812f` |    12 |           0.000 |  0.000 |  0.000 | **0.000** |          1.000 × 3  | 1.000 | **+1.000** |
| `c59f8b2a` |    12 |           0.000 |  0.000 |  0.000 | **0.000** |          1.000 × 3  | 1.000 | **+1.000** |
| `d427488f` |     2 |           0.000 |  0.000 |  0.000 | **0.000** |          1.000 × 3  | 1.000 | **+1.000** |
| `029f6a19` |    31 |           0.000 |  0.065 |  0.000 | **0.022** |          1.000 × 3  | 1.000 | **+0.978** |
| `e9474235` |    12 |           0.083 |  0.083 |  0.083 | **0.083** |          1.000 × 3  | 1.000 | **+0.917** |
| `446e76fe` |     1 |           0.000 |  0.000 |  1.000 | **0.333** |          1.000 × 3  | 1.000 | **+0.667** |
| `903d6f33` |    16 |           0.000 |  0.000 |  1.000 | **0.333** |          1.000 × 3  | 1.000 | **+0.667** |
| `20840ce0` |    31 |           0.774 |  0.452 |  0.774 | **0.667** |          1.000 × 3  | 1.000 | **+0.333** |
| `48f28e86` |    12 |           0.000 |  1.000 |  1.000 | **0.667** |          1.000 × 3  | 1.000 | **+0.333** |
| `c7faca71` |    51 |           0.843 |  0.863 |  0.941 | **0.882** |          1.000 × 3  | 1.000 | **+0.118** |

**Cost and effort, by arm** (means over the 3 runs of each arm):

| Task       |  cost A |  cost B | output tokens A | output tokens B | tool calls A | tool calls B |
| :--------- | ------: | ------: | --------------: | --------------: | -----------: | -----------: |
| `6f76812f` | $3.1790 | $0.4902 |          95,494 |           7,737 |         21.0 |          8.7 |
| `c7faca71` | $2.4758 | $0.4749 |          81,346 |          11,086 |          8.3 |          6.0 |
| `48f28e86` | $1.1331 | $0.3339 |          27,257 |           4,804 |         17.0 |          7.0 |
| `d427488f` | $1.0781 | $0.1395 |          31,752 |           1,516 |          8.0 |          3.0 |
| `e9474235` | $1.0210 | $0.3287 |          23,916 |           3,562 |         12.3 |          5.7 |
| `c59f8b2a` | $0.7639 | $0.3412 |          11,864 |           3,662 |         11.0 |          7.7 |
| `029f6a19` | $0.7629 | $0.5710 |          22,603 |          10,045 |          8.0 |          9.3 |
| `20840ce0` | $0.6844 | $0.2816 |          19,300 |           4,020 |          5.3 |          5.3 |
| `446e76fe` | $0.4427 | $0.2281 |          10,523 |           2,692 |          8.0 |          6.0 |
| `903d6f33` | $0.1365 | $0.2946 |           1,921 |           3,786 |          4.0 |          7.3 |

## Analysis

**The Skill moves accuracy and cost in the same direction.** The curated arm scores 1.000 on every
one of the 30 curated runs while costing **3.4× less** per run ($0.348 vs $1.168). On nine of ten
tasks the no-Skills arm also emits far more output — `6f76812f` burns 95k output tokens and $3.18
per run to arrive at 0/12, and `c7faca71` spends $2.48 per run re-deriving duty-limit tables the
Skill simply contains. This is the signature of a Skill that supplies *procedure* rather than
capability: the unaided arm re-derives a house method it half-remembers, while the curated arm
reads the SOP and executes it. `903d6f33` is the one inversion, and it is the cheapest task in the
set either way.

**Failures land on the documented levers.** The no-Skills failures are not random — they land on
the exact mistakes each SOP is designed to reject. `d427488f`'s unaided runs report `0.255886`, the
value a *mean* rather than *median* within-lab reduction produces. `446e76fe`'s land on `4.390`,
which the bundle identifies as the one-zero velocity-form Wood-Anderson path. `20840ce0`'s unaided
runs place the opening fields correctly and then drift at the reserved position runs the published
layout hides mid-record. Each failing run is a well-formed, confidently-wrong answer of the kind a
domain sanity-check waves through.

**The science tasks are near-binary; the office tasks carry real partial credit.** On the eight
natural-science tasks only 4 of 24 unaided runs score strictly between 0 and 1: each turns on a
single procedural decision applied to one computation, the verifiers require every named wrong path
to miss by **≥ 2× tolerance** (recorded per task as `control_gaps`), and so one wrong choice fails
every graded case together. The two office tasks behave differently — all 6 of their unaided runs
land strictly between 0 and 1, because their graded cases decompose into genuinely separable units
(field groups of a fixed-width record; per-pairing legality findings), and an unaided run gets some
units right. That contrast is why the tier figure can show a graded slope at the easy end while the
hard end is all-or-nothing.

**Read the direction, not the magnitude.** With n = 3 per arm and one model, `Δ = +70.1 pp` carries
a wide interval, and `g = 100%` is an artifact of a small denominator. The finding this sample
supports is directional: the Skill helped, decisively, and did so while spending ~3× less. Treat
the point estimates as illustration, not measurement.

## Task structure

Each task lives under `dataset/<task-id>/` and is fully self-contained:

```text
dataset/<task-id>/
├── task.toml                 # metadata, resource + network policy, reward family
├── instruction.md            # the prompt presented to the agent
├── uuid_provenance.json      # content-addressed integrity manifest (sha256 per file)
├── graded_cases.json         # which tests are graded and which are guards
├── TRUTH.md                  # answer-free golden procedure (grader-side)
├── environment/
│   ├── Dockerfile            # pinned sandbox
│   ├── data/                 # inputs mounted at /root/data
│   └── skills/               # mounted ONLY in the curated-Skills arm
├── oracle/                   # deterministic generator + reference solution; never mounted
├── tests/
│   ├── test.sh               # entry point; pre-seeds reward 0, parses JUnit XML
│   ├── test_pytest.py        # outcome assertions + guards + process rubric
│   ├── expected_values.json  # references, tolerances, and the control ledger
│   └── rubrics.json judge.py # process-channel criteria
└── trajectories/
    └── claude-opus-4-8/<condition>/run_N/
        ├── result.json       # config, agent metrics, reward, timing
        ├── config.json prompts.json timing.json rewards.jsonl
        ├── agent/            # ACP event stream, install log
        ├── trajectory/       # canonical ACP trace + raw LLM turns
        ├── trainer/          # trainer-format records
        └── verifier/
            ├── reward.txt pass_at_1.txt      # scalars
            ├── results.xml pytest_output.txt # structured + raw grader output
            ├── test-stdout.txt               # header + tail
            └── process/                      # process-channel panel and scores
```

During a run the agent sees only the built environment, the `instruction.md` prompt body, and — in
the curated arm — the mounted Skills directory. `oracle/`, `TRUTH.md` and `tests/` are used
exclusively by the verifier and are never exposed to the agent.

## Scoring methodology

A run's score is **graded cases passed / total**, computed inside the sealed container. Grading is
deterministic `pytest` — **no LLM-as-judge in the reward path**. Each `tests/test.sh` pre-seeds the
reward artifacts to 0 (so a crash grades 0, never a missing file), parses the score from the
**JUnit XML report** rather than scanning text, identifies scored tests by an explicit name prefix,
and excludes grader self-checks from the denominator. A failing self-check trips a kill-switch: the
run is a bundle defect, not an agent failure.

Every task also ships **anti-shortcut guards**, unscored but blocking. The most important is
isomorphic invariance: the reference is recomputed on a relabelled and reordered instance and
asserted unchanged, so a run cannot pass by keying on instance-specific names or positions. Nine of
the ten tasks carry one.

Tasks run `network_mode: no-network`, so the image bakes in `pytest` and the agent cannot look the
answer up. Each task ships a human-authored reference solution that passes by construction,
guaranteeing the grader is self-consistent. This is **not** an independent measure of real-world
solvability.

## Reproduction

No re-execution is needed to check the numbers in this document — read the shipped artifacts
directly:

```python
import glob, json, os, re, collections

GUARD = re.compile(r'plausib|isomorphic|invarian|guess_resist|frozen_golden|frozen_reference'
                   r'|tolerances_are|load_bearing|not_the_|wood_anderson_calib|golden_matches')
scores = collections.defaultdict(lambda: collections.defaultdict(list))

for run in glob.glob("dataset/*/trajectories/*/*/run_*"):
    task, cond = run.split("/")[1], run.split("/")[-2]
    spec = json.load(open(f"dataset/{task}/graded_cases.json"))["graded_tests"] \
        if os.path.exists(f"dataset/{task}/graded_cases.json") else None
    status = dict(re.findall(r'^(?:\S*::)?(\S+)\s+(PASSED|FAILED|ERROR|SKIPPED)\b',
                             open(f"{run}/verifier/pytest_output.txt", errors="ignore").read(), re.M))
    graded = {k for k in status
              if (k in {t.lstrip(':') for t in spec} if spec else k.startswith("test_graded_case"))
              and not GUARD.search(k)}
    scores[task][cond].append(sum(status[k] == "PASSED" for k in graded) / len(graded))

per_task = {t: {c: sum(v) / len(v) for c, v in arms.items()} for t, arms in scores.items()}
paired = [s for s in per_task.values() if "with-skill" in s]
A = sum(s["no-skill"] for s in paired) / len(paired)
B = sum(s["with-skill"] for s in paired) / len(paired)
print(f"A = {A:.3f}  B = {B:.3f}  delta = {B - A:+.3f}  g = {(B - A) / (1 - A):.3f}")
# -> A = 0.299  B = 1.000  delta = +0.701  g = 1.000   (over all 10 paired tasks)
```

The score is read from the **raw pytest record**, not from the `test cases passed` header in
`test-stdout.txt` — one shipped header disagrees with its own record (see
[Known issues](#known-issues)).

## Verification and quality assurance

- **Structure.** 10 self-contained task directories, each carrying a complete 2 × 3 grid. Every
  scoring-relevant file is present and non-empty in all 60 runs.
- **Provenance.** Every bundle carries a `uuid_provenance.json` sha256 manifest, every listed file
  matches it, and the manifest's canonical hash re-verifies on all 10 bundles. Three bundles
  (`029f6a19`, `20840ce0`, `c7faca71`) were re-sealed 2026-08-04 after standardisation to the
  common layout; their run grids are byte-identical to their upstream Erza delivery source.
- **Score integrity.** Every score is recomputed from the run's own raw pytest record;
  `verifier/reward.txt` agrees with `result.json` on all 60 runs, and with `pass_at_1.txt`.
- **Paired isolation.** `prompts.json` is **byte-identical across both arms on all 10 tasks** — the
  Skill is delivered by filesystem mount, never by prompt injection. Agent budgets are uniform
  (1800 s) across both arms on nine tasks (`48f28e86` is the exception — see
  [Known issues](#known-issues)), and each task's runs share a single `task_digest`, so both arms
  measured the same frozen bundle bytes. The two arms differ in exactly one variable.
- **The Skill was genuinely used.** All 30 curated runs record an explicit launch of their task's
  Skill in `trajectory/acp_trajectory.jsonl`; all 30 no-Skills runs record none. (Do not use
  `agent_result.n_skill_invocations` — see [Known issues](#known-issues).)
- **Fair play.** Each curated `SKILL.md` is class-level procedure — the reduction rule, the house
  constants, the uncertainty definitions — not an answer key. The agent never accesses the oracle
  or the verifier.
- **Anti-memorization.** Nine of ten tasks assert isomorphic invariance under relabelling and
  reordering, so the answer depends on the content of the records, not on instance-specific names
  or positions.
- **Tolerances are engineered, not guessed.** Every graded quantity carries an explicit tolerance
  whose separation from each named wrong path is recorded as `control_gaps`, and which is proven
  not to false-fail a defensible reading of the same published inputs.

### Known issues

- **One shipped header is wrong.** `48f28e86` no-skill/run_1 reports `test cases passed : 2/12` in
  `verifier/test-stdout.txt`, but its own pytest record shows **0 of 12 graded cases passed**; the
  two passes are guards (`test_plausibility_guess_resistance`, `test_isomorphic_invariance`) that
  the header counted into a graded denominator. Its `reward.txt`, `pass_at_1.txt` and `result.json`
  all correctly read 0. This is the only such disagreement across all 60 runs. **Score from the
  pytest record, not the header.**
- **`48f28e86` is a screening bundle.** Its own `trajectories/PROVENANCE.md` states that its runs
  are *not a valid paired comparison* — the agent budget differs across runs (700 s / 900 s /
  1200 s), so the arms are not single-variable and **no Δ should be quoted from it**. Its single
  no-Skills failure is also its only 700 s run. It is shipped for completeness and reported
  separately in [Summary](#summary); the nine-task column is the honest one.
- **`029f6a19` runs are a prefix, not the full set.** Its source carries 6 no-Skills and 5 curated
  runs; this sample ships `run_1..3` of each arm — the first three by index, not selected on score.
  The two runs omitted from the no-Skills arm score 0.000 and 0.065, so the shipped prefix is
  representative rather than favourable.
- **`20840ce0` and `c7faca71` sit high unaided.** At A = 0.667 and A = 0.882 the model largely
  solves both without the Skill, and their Δ (+0.333, +0.118) are the smallest in the sample.
  Under Erza's own bar — "a task the model already passes unaided is below the bar" — their
  inclusion is a judgment call; they are shipped because their pairing is clean (uniform budgets,
  one prompt, one `task_digest` across all 6 runs) and they are the sample's only source of graded
  partial credit. Their current grids replaced an earlier superseded single-run generation
  (2026-07-29 bundle bytes; `c7faca71`'s superseded run scored 0.765 against different frozen
  bytes). Neither task ships `egress/probe.txt` — that network-seal capture does not exist for
  this run cohort in any source.
- **`n_skill_invocations` is unreliable.** `result.json` reports
  `agent_result.n_skill_invocations: 0` for every run, including curated runs that demonstrably
  launched the Skill. Use the trajectory, not this field.
- **`agent/claude_agent_acp.txt` is empty** in a subset of runs; the harness did not write it.
  Nothing scoring-relevant is lost — full agent behaviour is in `trajectory/`.
- **`d427488f` verifier artifacts were re-serialised.** Its runs were graded by an older harness
  that emitted CTRF; `verifier/results.xml` is a JUnit re-serialisation of those same recorded
  results, and `pytest_output.txt` is the original raw capture. No score changed. It ships without
  `egress/probe.txt` because that network-seal capture does not exist for this task in any source.
- **`graded_cases.json` quality varies by generation.** On the seven older tasks it is
  name-pattern derived and self-flags `needs_review: true`; on at least one it lists a guard among
  the graded tests. On the three newer tasks (`029f6a19`, `20840ce0`, `c7faca71`) the graded set
  is exact — parametrized `test_graded_case[...]` entries — and flags `needs_review: false`. The
  reproduction snippet above filters guard names explicitly for this reason.

### Limitations

- **Sample size.** 10 tasks, 3 runs per arm, one model. The Erza delivery standard is ≥ 5 trials
  per arm with paired-bootstrap confidence intervals; this sample sits **below that bar by
  design** — it demonstrates format and method, and is not a powered efficacy estimate.
- **Single model.** Only Claude Opus 4.8 was run. Δ is not established to generalize across models.
- **Domain concentration.** Seven of ten tasks are natural-science. Δ is not established across
  the domain distribution.
- **Little score variance.** All 30 curated runs score exactly 1.000, and 20 of 30 unaided runs
  score exactly 0 or 1. Partial credit is concentrated in the two office tasks (see
  [Analysis](#analysis)), so the difficulty tiers rest on a handful of distinct score values and
  the tier means carry no dispersion estimates.
- **Tiers are outcome-based on the same runs they describe.** The [tier](#difficulty-tiers)
  assignment uses the unaided scores, so the no-Skills slope across tiers is circular by
  construction; only the curated line and the Δ column are findings.
- **Selection.** Tasks were drawn from an existing measured pool rather than sampled at random, and
  every task here has positive Δ. Erza's charter keeps and labels zero- and negative-Δ tasks; none
  are represented in this sample, so it is not evidence about the Δ distribution.
- **Model nondeterminism.** The same model produces different outputs for the same task; the
  unaided arm's differing answers at identical scores are themselves evidence of that.

## License

`cc-by-nc-nd-4.0`. Each bundled `SKILL.md` carries its own header.
