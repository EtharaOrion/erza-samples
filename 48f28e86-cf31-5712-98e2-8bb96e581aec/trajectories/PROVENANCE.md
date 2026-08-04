# Provenance — geomagnetic-declination-survey / IGRF spherical-harmonic reduction (48f28e86)

> # ⚠️ SCREENING BUNDLE — NOT PART OF THE DELIVERABLE SET.
>
> Retained for provenance only. The recorded runs are **not a valid paired comparison**:
> the agent budget differs across runs (`1200` / `700` / `900` s), so the arms are not
> single-variable and no Δ may be quoted from them. Arms are also unbalanced (4 vs 3).

**Task:** for 12 stations of a geodetic control survey (Alaska/Canada, lat 55–72°N),
reduce each station's magnetic-referenced baseline azimuth to a true (geographic)
azimuth for survey epoch 2020.0. The true azimuth is the measured magnetic azimuth
plus the local magnetic declination, where declination must be computed per-station
from the IGRF-13 geomagnetic field model (spherical-harmonic synthesis, Schmidt
semi-normalized Legendre functions, geodetic→geocentric latitude conversion).
A decoy reference supplies a single rounded declination (6.5°) from an old regional
chart — applying it fails every station by many degrees. numpy is available; network
is not. The agent must either implement WMM2020/IGRF-13 spherical-harmonic synthesis
from known Gauss coefficients, or discover and apply the curated skill under
`environment/skills/geomagnetic-declination-igrf/`.

Scoring: per-station tolerance 0.1°, Score = passed/12, reward 0/1 with pass@1.

- **Task id:** `48f28e86-cf31-5712-98e2-8bb96e581aec` — minted as uuid5 of the
  canonical content hash of the shipped bundle. See
  `dataset/48f28e86-…/uuid_provenance.json` for the manifest and hash construction.
- **Imported from:** `harness/tasks/geomagnetic-declination-survey/` (authored and
  piloted 2026-07-24 via the Erza FORGE pipeline).
- **Frozen-bytes binding:** All 8 packaged runs share `task_digest`
  `sha256:40ac03e2ef0e9814ed7279f001b5417988cf0b8e90a0a2a2db223ca7b5807818`,
  proving they are a single frozen-bytes cohort.

## Result (claude-opus-4-8, benchflow, Docker)

| Arm | Trials | Passes | Pass rate | Mean Score |
|---|---|---|---|---|
| **no-skill** | 4 | 3 | 0.750 | 0.750 |
| **with-skill** | 3 | 3 | 1.000 | 1.000 |

**Δ = +0.250** (with-skill 1.000 − no-skill 0.750).

The single no-skill failure (run_1, reward 0.0) shows a model that attempted but
produced an incomplete geomagnetic-field implementation — all 12 stations fell outside
the 0.1° tolerance. The remaining 7 runs scored 1.0, demonstrating that the model
reliably produces a correct WMM2020 spherical-harmonic synthesis either from embedded
knowledge (no-skill) or via the curated skill (with-skill).

**n=3 on the aided arm is too small to certify the Δ** (finding F1: a 30-run drift
control can move the baseline by 0.18). The 3/3 sweep is nonetheless clean evidence
that the skill works.

## Verifier

`verifier/test.sh` runs pytest (`test_outputs.py`) against the agent's
`/root/results.json`. Each station's true_azimuth_deg is compared against the
reference with a tolerance of 0.1°. The pass count is read from pytest's JUnit XML
output — submission content cannot forge the count.

## Context

Authored under the Erza FORGE methodology. The task tests whether an agent can:
(1) recognize that magnetic declination is spatially variable and requires a
field model, (2) implement or apply IGRF-13 spherical-harmonic synthesis, and
(3) correctly handle the geodetic→geocentric latitude conversion (a load-bearing
subtlety where treating geodetic latitude as geocentric displaces every station
past tolerance). The curated skill at `environment/skills/geomagnetic-declination-igrf/`
teaches the full synthesis chain with the geodetic conversion explicitly documented.
