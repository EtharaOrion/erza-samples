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
  <a href="#summary">Summary</a> · <a href="#repository-layout">Layout</a> · <a href="#metric-skill-efficacy-δ">Metric</a> · <a href="#the-tasks">Tasks</a> · <a href="#results">Results</a> · <a href="#analysis">Analysis</a> · <a href="#task-structure">Structure</a> · <a href="#scoring-methodology">Scoring</a> · <a href="#reproduction">Reproduction</a> · <a href="#verification-and-quality-assurance">Verification</a>
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

This is a **10-task orientation sample**: ten complete task bundles and 50 graded agent
trajectories (Claude Opus 4.8). Eight tasks carry the full paired grid of 2 conditions × 3 runs;
two (`20840ce0`, `c7faca71`) have a single no-Skills run and **no curated arm yet**, so they
contribute a baseline score and no Δ. The dataset format, trajectory format, and scoring are identical to the
production Erza harness.

> **Scope.** This sample exists to show the *shape* of an Erza deliverable end-to-end. Three runs
> per arm cannot establish an efficacy estimate — see [Limitations](#limitations).

## Summary

| Property            | Value                                                                          |
| :------------------ | :----------------------------------------------------------------------------- |
| Tasks               | **10** — 8 fully paired, 2 (`20840ce0`, `c7faca71`) baseline-only              |
| Domains             | natural-science (7) · office-white-collar (3), across 10 subcategories         |
| Difficulty          | `hard` on all 10 (declared in `task.toml`)                                     |
| Models evaluated    | Claude Opus 4.8 (`claude-opus-4-8`)                                            |
| Conditions per task | no-Skills (A) · curated-Skills (B)                                             |
| Runs & grid         | **50 graded runs** — 8 tasks at a full 2 × 3; 2 tasks at 1 × no-Skills only    |
| Graded cases        | 1 to 51 per task (180 in total)                                                |
| Score               | graded cases passed / total, per run                                           |
| Network             | `no-network` on all 10; verifier is deterministic `pytest`, no LLM judge       |

**Measured on this sample.** Δ is computed over the **8 paired tasks only** — `20840ce0` and
`c7faca71` have no curated arm and are excluded from every Δ figure below:

| Metric                                   |   8 paired tasks | Excl. `48f28e86` (see [Known issues](#known-issues)) |
| :--------------------------------------- | ---------------: | ---------------------------------------------------: |
| no-Skills mean score (A)                 |     **0.180**  |                                            **0.110** |
| curated-Skills mean score (B)            |     **1.000**  |                                            **1.000** |
| **Skill efficacy (Δ = B − A)**           |  **+82.0 pp**  |                                        **+89.0 pp**  |
| Normalized gain `g = Δ / (1 − A)`        |       **100%** |                                             **100%** |
| no-Skills pass rate (all cases passed)   |  16.7% (4/24)  |                                          9.5% (2/21) |
| curated-Skills pass rate                 | 100.0% (24/24) |                                        100.0% (21/21) |
| Mean agent cost, no-Skills               |      $1.0647   |                                              $1.0549 |
| Mean agent cost, curated-Skills          |      $0.3409   |                                              $0.3419 |

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
        ├── oracle/ solution/ # reference solution, never mounted
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
| `20840ce0` | office-white-collar / tax-information-reporting   |           31 | fixed-width filing-record emission (**no curated arm yet**)   |
| `c7faca71` | office-white-collar / aviation-regulatory-compliance |        51 | flight-duty-period legality (**no curated arm yet**)          |

Every task follows the same shape: a domain-specific **house procedure** the agent must execute
exactly, and a plausible **decoy** in the inputs that a competent but unaided run tends to fall
into. `d427488f`, for example, hands the agent a naive plain-mean scale of `0.468704` labelled
"for orientation ONLY", where the graded answer is the robust clamped scale `0.250368`.

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
| `48f28e86` |    12 |           0.000 |  1.000 |  1.000 | **0.667** |          1.000 × 3  | 1.000 | **+0.333** |

**Not paired** — reported separately because they have no curated arm:

| Task       | Cases |   no-skill run_1 |     **A** | with-skill | **Δ** |
| :--------- | ----: | ---------------: | --------: | :--------- | :---- |
| `20840ce0` |    31 | 0.774 (24/31)    | **0.774** | *not run*  | *n/a* |
| `c7faca71` |    51 | 0.765 (39/51)    | **0.765** | *not run*  | *n/a* |

**Cost and effort, by arm** (means over the 3 runs of each arm; `20840ce0` is a single run):

| Task       | cost A  | cost B  | output tokens A | output tokens B | tool calls A | tool calls B |
| :--------- | ------: | ------: | --------------: | --------------: | -----------: | -----------: |
| `6f76812f` | $3.1790 | $0.4902 |          95,494 |           7,737 |         21.0 |          8.7 |
| `48f28e86` | $1.1331 | $0.3339 |          27,257 |           4,804 |         17.0 |          7.0 |
| `d427488f` | $1.0781 | $0.1395 |          31,752 |           1,516 |          8.0 |          3.0 |
| `e9474235` | $1.0210 | $0.3287 |          23,916 |           3,562 |         12.3 |          5.7 |
| `c59f8b2a` | $0.7639 | $0.3412 |          11,864 |           3,662 |         11.0 |          7.7 |
| `029f6a19` | $0.7629 | $0.5710 |          22,603 |          10,045 |          8.0 |          9.3 |
| `446e76fe` | $0.4427 | $0.2281 |          10,523 |           2,692 |          8.0 |          6.0 |
| `903d6f33` | $0.1365 | $0.2946 |           1,921 |           3,786 |          4.0 |          7.3 |
| `20840ce0` | $0.8710 |   *n/a* |          21,647 |           *n/a* |          6.0 |        *n/a* |
| `c7faca71` | 2.6968 |   *n/a* |         85,373 |           *n/a* |       5.0 |        *n/a* |

## Analysis

**The Skill moves accuracy and cost in the same direction.** The curated arm scores 1.000 on every
one of the 48 runs while costing **3.1× less** per run ($0.341 vs $1.065). On seven of eight tasks
the no-Skills arm also emits far more output — `6f76812f` burns 95k output tokens and $3.18 per run
to arrive at 0/12. This is the signature of a Skill that supplies *procedure* rather than
capability: the unaided arm re-derives a house method it half-remembers, while the curated arm
reads the SOP and executes it. `903d6f33` is the one inversion, and it is the cheapest task in the
set either way.

**Failures land on the documented levers.** The no-Skills failures are not random — they land on
the exact mistakes each SOP is designed to reject. `d427488f`'s unaided runs report `0.255886`, the
value a *mean* rather than *median* within-lab reduction produces. `446e76fe`'s land on `4.390`,
which the bundle identifies as the one-zero velocity-form Wood-Anderson path. Each failing run is a
well-formed, confidently-wrong answer of the kind a domain sanity-check waves through.

**Scores are near-binary, and that is by construction.** Of 24 no-Skills runs, only **4** score
strictly between 0 and 1. Each task turns on a single procedural decision applied to one
computation, and the verifiers require every named wrong path to miss by **≥ 2× tolerance**
(recorded per task as `control_gaps`). So one wrong choice propagates into every graded case at
once and they fail together. The runs themselves are *not* identical — on `d427488f` the three
unaided runs submit three different answers and all score 0.000 — so the invariance is in the
scoring, not the sampling. Partial credit appears only where a wrong method lands unusually close
to tolerance: `029f6a19` (2/31) and `e9474235` (1/12) are the only two tasks that show it.

**Read the direction, not the magnitude.** With n = 3 per arm and one model, `Δ = +82.0 pp` carries
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
├── oracle/ or solution/      # deterministic generator + reference solution; never mounted
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
the curated arm — the mounted Skills directory. `oracle/`, `solution/`, `TRUTH.md` and `tests/` are
used exclusively by the verifier and are never exposed to the agent.

## Scoring methodology

A run's score is **graded cases passed / total**, computed inside the sealed container. Grading is
deterministic `pytest` — **no LLM-as-judge in the reward path**. Each `tests/test.sh` pre-seeds the
reward artifacts to 0 (so a crash grades 0, never a missing file), parses the score from the
**JUnit XML report** rather than scanning text, identifies scored tests by an explicit name prefix,
and excludes grader self-checks from the denominator. A failing self-check trips a kill-switch: the
run is a bundle defect, not an agent failure.

Every task also ships **anti-shortcut guards**, unscored but blocking. The most important is
isomorphic invariance: the reference is recomputed on a relabelled and reordered instance and
asserted unchanged, so a run cannot pass by keying on instance-specific names or positions. Seven
of the eight tasks carry one.

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
paired = [s for s in per_task.values() if "with-skill" in s]   # 20840ce0 has no curated arm
A = sum(s["no-skill"] for s in paired) / len(paired)
B = sum(s["with-skill"] for s in paired) / len(paired)
print(f"A = {A:.3f}  B = {B:.3f}  delta = {B - A:+.3f}  g = {(B - A) / (1 - A):.3f}")
# -> A = 0.180  B = 1.000  delta = +0.820  g = 1.000   (over the 8 paired tasks)
```

The score is read from the **raw pytest record**, not from the `test cases passed` header in
`test-stdout.txt` — one shipped header disagrees with its own record (see
[Known issues](#known-issues)).

## Verification and quality assurance

- **Structure.** 10 self-contained task directories. Eight carry a complete 2 × 3 grid;
  `20840ce0` and `c7faca71` each ship a single no-Skills run and an intentionally empty curated
  arm. Every scoring-relevant file is present and non-empty in all 50 runs.
- **Provenance.** Every bundle carries a `uuid_provenance.json` sha256 manifest and every listed
  file matches it. Seven of the eight bundles are byte-identical to their source in the upstream
  Erza delivery repository.
- **Score integrity.** Every score is recomputed from the run's own raw pytest record;
  `verifier/reward.txt` agrees with `result.json` on all 50 runs, and with `pass_at_1.txt`.
- **Paired isolation.** `prompts.json` is **byte-identical across both arms on all 8 paired tasks** — the
  Skill is delivered by filesystem mount, never by prompt injection. The two arms differ in exactly
  one variable.
- **The Skill was genuinely used.** All 24 curated runs record an explicit launch of their task's
  Skill in `trajectory/acp_trajectory.jsonl`; all 26 no-Skills runs record none. (Do not use
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
  all correctly read 0. Every other header in the sample agrees with its record. **Score from the
  pytest record, not the header.**
- **`48f28e86` is a screening bundle.** Its own `trajectories/PROVENANCE.md` states that its runs
  are *not a valid paired comparison* — the agent budget differs across runs (700 s / 900 s /
  1200 s), so the arms are not single-variable and **no Δ should be quoted from it**. Its single
  no-Skills failure is also its only 700 s run. It is shipped for completeness and reported
  separately in [Summary](#summary); the seven-task column is the honest one.
- **`029f6a19` runs are a prefix, not the full set.** Its source carries 6 no-Skills and 5 curated
  runs; this sample ships `run_1..3` of each arm — the first three by index, not selected on score.
  The two runs omitted from the no-Skills arm score 0.000 and 0.065, so the shipped prefix is
  representative rather than favourable.
- **`20840ce0` and `c7faca71` are baseline-only.** Each ships one no-Skills run and no curated
  arm, so each yields a score and no Δ, and both are excluded from every Δ figure in this
  document. Their curated-arm directories are kept with a placeholder so the gap is visible
  rather than silently absent. At n = 1, their scores (0.774 and 0.765) carry no dispersion
  estimate whatsoever, and both sit high enough that the unaided model may be close to solving
  these tasks outright — which the curated arm, once run, would have to be read against.
- **`n_skill_invocations` is unreliable.** `result.json` reports
  `agent_result.n_skill_invocations: 0` for every run, including curated runs that demonstrably
  launched the Skill. Use the trajectory, not this field.
- **`agent/claude_agent_acp.txt` is empty** in a subset of runs; the harness did not write it.
  Nothing scoring-relevant is lost — full agent behaviour is in `trajectory/`.
- **`d427488f` verifier artifacts were re-serialised.** Its runs were graded by an older harness
  that emitted CTRF; `verifier/results.xml` is a JUnit re-serialisation of those same recorded
  results, and `pytest_output.txt` is the original raw capture. No score changed. It ships without
  `egress/probe.txt` because that network-seal capture does not exist for this task in any source.
- **`graded_cases.json` is name-pattern derived** and self-flags `needs_review: true`; on at least
  one task it lists a guard among the graded tests. The reproduction snippet above filters guard
  names explicitly for this reason.

### Limitations

- **Sample size.** 10 tasks, 3 runs per arm (1 for `20840ce0` and `c7faca71`), one model. The Erza delivery standard is ≥ 5 trials per
  arm with paired-bootstrap confidence intervals; this sample sits **below that bar by design** — it
  demonstrates format and method, and is not a powered efficacy estimate.
- **Single model.** Only Claude Opus 4.8 was run. Δ is not established to generalize across models.
- **Domain concentration.** Seven of ten tasks are natural-science. Δ is not established across
  the domain distribution.
- **No score variance to speak of.** All 24 curated runs score exactly 1.000, and only 4 of 24
  unaided runs score strictly between 0 and 1. The scores are near-binary by construction (see
  [Analysis](#analysis)), so this sample cannot support a graded difficulty ranking.
- **Selection.** Tasks were drawn from an existing measured pool rather than sampled at random, and
  every task here has positive Δ. Erza's charter keeps and labels zero- and negative-Δ tasks; none
  are represented in this sample, so it is not evidence about the Δ distribution.
- **Model nondeterminism.** The same model produces different outputs for the same task; the
  unaided arm's differing answers at identical scores are themselves evidence of that.

## License

`cc-by-nc-nd-4.0`. Each bundled `SKILL.md` carries its own header.
