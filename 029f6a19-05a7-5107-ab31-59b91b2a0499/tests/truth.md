# truth.md — bridged-race-population-estimates (grader-side)

Grader-side dossier. Goldens are permitted in this file. It is never mounted into
the agent's container: `environment/Dockerfile` copies `data/` and nothing else,
and `/verifier` is in the recorded `sandbox_locked_paths`.

## Delta-lever

A census response naming more than one race is assigned to the four 1977-standard
categories with the **logistic-regression coefficient set NCHS estimated from
National Health Interview Survey primary-race answers** — Table 7's six separate
models and Table 8's composite multi-logit, evaluated on that person's own age,
sex, Hispanic origin and county composition — not by splitting the response
equally over the categories it names and not in proportion to the area's
single-category counts. Both arithmetic routes miss **every** graded case by more
than twice the tolerance, and that property is asserted per case at build time
and re-measured on every graded run.

Gap type **(b)**, a published measured coefficient set the default route replaces
with a plausible arithmetic rule. Failure family **F2**. This is a
**non-natural-science** task and is flagged as a Phase-1 scope exception for a
human in `build/build_report.json:phase_1_scope_exception`.

## What the agent is given, and what it is not

Given: 31 records, each naming an opaque area label, a single year of age, a sex,
a Hispanic-origin status, a response group and one target category; a profile per
area carrying its census region, its urbanisation level and the percentage of its
residents in each single category and in more than one; and a plainly labelled
orientation block of published country-wide flat shares.

Not given: the coefficient set. It is not recoverable from the input either.
**There is no share anywhere in `/root/data`** — the records carry covariates
only, and the orientation block is a national average that is deliberately not
any record's answer — so no quantity in the input stands in a fixed ratio to a
graded figure and nothing can be back-solved by division. That is the specific
failure that killed the EPA derived-5-cycle candidate and it is closed here by
construction, not by assertion.

The counties are **delabelled**: no name, no FIPS code, no state, no population.
Per `PROMPT-AUTHOR-TO-30.md` §6.8 this is what makes the lever un-fetchable even
with full internet, because there is no published table of shares keyed by
anything the agent can see.

## Derivation

Each record is priced with the equation family the publisher fitted for its own
response group, evaluated on its own covariates:

```
  five two-category groups          Table 7, one column each, inverse logit
    AIAN+BLACK -> BLACK column        (AIAN is the complement)
    AIAN+WHITE -> AIAN column         (WHITE is the complement)
    API+BLACK  -> BLACK column        (API is the complement)
    API+WHITE  -> API column          (WHITE is the complement)
    BLACK+WHITE-> BLACK column        (WHITE is the complement)

  one three-category group          Table 7, two columns, WHITE the reference
    AIAN+BLACK+WHITE                  softmax over (eta_AIAN, eta_BLACK, 0)

  five composite groups             Table 8, three columns, WHITE the reference
    AIAN+API, AIAN+API+BLACK, AIAN+API+WHITE, API+BLACK+WHITE,
    AIAN+API+BLACK+WHITE              softmax over the four, then RESCALED over
                                      the categories the group actually names
```

Covariate coding, in the order the published tables use: age in single years
divided by 10 and **capped at 69**; Hispanic origin and male as 0/1; three region
indicators with **West as the reference**; three urbanisation indicators with
**large central metro as the reference**; the area's percent AIAN alone, percent
API alone, percent Black alone and percent multiple-response, all on a 0-100
scale; constant. Footnote 4: the **logarithm** of percent AIAN in the AIAN/White
and AIAN/Black columns and in the composite model. Footnote 5: the **square** of
percent Black in the Black/White and AIAN/Black columns. Table 8's three group
indicators are set from which categories the response group does *not* name, and
the indicator naming an outcome is constrained to zero for that outcome.

The 17 shipped areas are real US counties, delabelled, chosen by a deterministic
sweep over region x urbanisation strata with the rotation offset fixed by
SEED 20260731 (`SEED_BASE + 2`). Their composition percentages are the ones NCHS
itself used, reconstructed from the public Census 2000 Modified Race Data Summary
File and verified to agree exactly on 3,139 of 3,140 counties
(`build/build_report.json:area_covariates_are_the_publishers_own`). The 31 graded
records are real cells: only (area, age group, sex, origin, response group)
combinations with a non-zero enumerated population were eligible.

## Golden

Frozen in `expected_values.json`, which is authoritative wherever it and this
document disagree. Tolerance **0.002 absolute** on a share in [0, 1], the same
band for every case.

| case | record | response group | target | reference |
|---|---|---|---|---|
| `share-R-01` | AREA-13, age 59, F, non-Hispanic | AIAN+API | AIAN | 0.342134 |
| `share-R-02` | AREA-14, age 54, F, non-Hispanic | AIAN+API | API | 0.611434 |
| `share-R-03` | AREA-15, age 14, M, non-Hispanic | AIAN+BLACK | AIAN | 0.065097 |
| `share-R-04` | AREA-16, age 2, M, non-Hispanic | AIAN+BLACK | BLACK | 0.887948 |
| `share-R-05` | AREA-17, age 8, F, Hispanic | AIAN+WHITE | AIAN | 0.387857 |
| `share-R-06` | AREA-01, age 14, F, non-Hispanic | AIAN+WHITE | WHITE | 0.644999 |
| `share-R-07` | AREA-02, age 21, F, non-Hispanic | API+BLACK | API | 0.594901 |
| `share-R-08` | AREA-03, age 27, M, non-Hispanic | API+BLACK | BLACK | 0.928597 |
| `share-R-09` | AREA-02, age 70, F, non-Hispanic | API+WHITE | API | 0.432105 |
| `share-R-10` | AREA-04, age 32, F, non-Hispanic | API+WHITE | API | 0.322367 |
| `share-R-11` | AREA-02, age 6, M, Hispanic | API+WHITE | WHITE | 0.661300 |
| `share-R-12` | AREA-05, age 39, F, Hispanic | API+WHITE | WHITE | 0.772250 |
| `share-R-13` | AREA-06, age 23, F, non-Hispanic | BLACK+WHITE | BLACK | 0.585750 |
| `share-R-14` | AREA-07, age 52, F, non-Hispanic | BLACK+WHITE | WHITE | 0.472826 |
| `share-R-15` | AREA-08, age 14, M, non-Hispanic | AIAN+API+BLACK | AIAN | 0.228139 |
| `share-R-16` | AREA-09, age 59, M, non-Hispanic | AIAN+API+BLACK | API | 0.285469 |
| `share-R-17` | AREA-10, age 44, F, non-Hispanic | AIAN+API+BLACK | BLACK | 0.509460 |
| `share-R-18` | AREA-11, age 80, M, non-Hispanic | AIAN+API+WHITE | AIAN | 0.013811 |
| `share-R-19` | AREA-12, age 19, M, non-Hispanic | AIAN+API+WHITE | API | 0.073164 |
| `share-R-20` | AREA-13, age 15, F, non-Hispanic | AIAN+API+WHITE | WHITE | 0.974421 |
| `share-R-21` | AREA-14, age 13, F, non-Hispanic | AIAN+BLACK+WHITE | AIAN | 0.462470 |
| `share-R-22` | AREA-15, age 21, F, Hispanic | AIAN+BLACK+WHITE | BLACK | 0.406510 |
| `share-R-23` | AREA-16, age 26, F, non-Hispanic | AIAN+BLACK+WHITE | WHITE | 0.357912 |
| `share-R-24` | AREA-17, age 11, F, non-Hispanic | API+BLACK+WHITE | API | 0.057035 |
| `share-R-25` | AREA-01, age 14, F, non-Hispanic | API+BLACK+WHITE | BLACK | 0.039828 |
| `share-R-26` | AREA-02, age 39, M, Hispanic | API+BLACK+WHITE | WHITE | 0.790859 |
| `share-R-27` | AREA-03, age 25, M, Hispanic | AIAN+API+BLACK+WHITE | AIAN | 0.021864 |
| `share-R-28` | AREA-04, age 58, M, non-Hispanic | AIAN+API+BLACK+WHITE | API | 0.004582 |
| `share-R-29` | AREA-12, age 54, M, non-Hispanic | AIAN+API+BLACK+WHITE | BLACK | 0.088996 |
| `share-R-30` | AREA-02, age 30, M, non-Hispanic | AIAN+API+BLACK+WHITE | WHITE | 0.965695 |
| `share-R-31` | AREA-06, age 72, M, non-Hispanic | AIAN+API+BLACK+WHITE | WHITE | 0.982957 |

The 28 (response group, target category) pairs are exactly the 28 assignment
probabilities the published method produces per cell; the graded set is those 28
plus three extras — `share-R-09` (age cap), `share-R-11` (Hispanic origin) and
`share-R-30` (four-way rescale). **31 is prime.**

### Why the golden is trustworthy

Not by assertion, and not by asking the oracle's own code whether it agrees with
itself. There are four separate anchors, three of which run on every graded run:

- **A second formulation inside the verifier.** `verifier/independent_bridging.py`
  transcribes the published tables a second time in a **model-major** layout
  rather than the oracle's covariate-major one, accumulates the odds as a
  **product of per-covariate factors** rather than one exponential of a summed
  linear predictor, inverts the two-category models by **bisection on the logit
  equation** rather than by evaluating the logistic function, and computes every
  multi-category model as a **conditional normalisation over the applicable
  categories** instead of forming the four-category vector and rescaling it.
  Worst disagreement against the frozen goldens: **2.2e-16**, i.e. machine
  precision, against a 0.002 tolerance. Asserted on every run by
  `test_frozen_reference_matches_independent_recompute`.
- **The publisher's own anchor.** NCHS Table 9 of the same report publishes the
  mean, median, interquartile bounds, minimum and maximum of these shares for all
  28 series — **168 published numbers describing exactly the quantity this task
  grades**. `verifier/anchor_table9.csv` carries them and
  `test_published_table9_distribution_is_reproduced` recomputes all 168 over the
  published cell universe on every graded run. Worst absolute difference
  **0.1140**, against a declared bound of 0.15; the residual is one-sided and
  explained (see Plausibility envelope). A mistyped coefficient cannot agree with
  itself here: it would have to be wrong in the oracle, wrong in the second
  transcription, and wrong in NCHS's own released summary in the same way.
- **The publisher's own released output.** Applying the same coefficient set to
  the Census 2010 Modified Race Data Summary File and comparing against the
  bridged file NCHS released reproduces the allocated multiple-response
  population to **+0.032% (White), +0.597% (API), −2.052% (Black), +5.781%
  (AIAN)** nationally, against **+14.2% (AIAN)** for the equal split and
  **−10.6% (AIAN)** for the proportional split. Measured at build time and
  recorded in `build/build_report.json:end_to_end_against_the_publishers_own_2010_output`.
  It is an anchor, not a golden — see the honest caveat below.
- **Four transcriptions.** The oracle, the verifier, the process channel and
  `verifier/process/verification/rederivation_test.py` each carry the tables in a
  different layout, and all four are asserted cell by cell against
  `build/source/sr02_135_table7.csv` and `sr02_135_table8.csv`, the slice cut
  from the publisher's PDF.

**Honest caveat, recorded rather than buried.** No single graded share is a number
NCHS itself printed. Property 3 — a golden verified record by record against the
publisher — is achieved here in aggregate (168 published statistics, plus the
2010 file at county level) but **not** at the record level. The scouting note that
`cqs_countyprobs.sas7bdat` would supply record-level shares was tested and is
wrong: regressing the logit of its probability columns on the Table 7 covariate
set gives R² 0.48–0.99, while regressing on its own 40 covariates — which include
dissimilarity, isolation and interaction indices, poverty, crowding and
single-parent share, none of which appear in Table 7 or Table 8 — gives R²
1.0000000000 with a maximum residual of 7.6e-06. It is an expanded, later model.
The full measurement is in
`build/build_report.json:cqs_countyprobs_is_not_the_table_7_proportion_set`.

The anchors cannot silently skip: `independent_bridging.anchor()` and
`.cell_universe()` raise `MissingAnchor` when their file is absent or short, and
`test.sh` scores the run 0 if any self-check fails **or is skipped**.

## Plausibility envelope

Every graded value must sit inside these bounds, and the oracle's values do.
Asserted in `test_plausibility_envelope_and_guess_resistance`,
`test_shares_of_a_response_group_sum_to_one` and
`test_published_table9_distribution_is_reproduced`.

| quantity | envelope | why |
|---|---|---|
| a graded share | strictly inside (0, 1) | it is a share; outside is an arithmetic or normalisation error |
| the shares of one response group | sum to 1 over the categories that group names, to 1e-12 | a missed composite rescale fails here immediately |
| every graded share | inside the published minimum-to-maximum range Table 9 gives for its own series | the publisher's own bound on the same quantity |
| distance from a round figure | > 2 tolerances (measured: 2.29) | a flat guess must not score a case for free |
| distance between two goldens | > 2 tolerances (measured: 4.03) | one constant answer can then never clear two cases |

The 31 goldens run from 0.004582 to 0.982957, spread over eleven response groups
and four target categories, and each sits inside the published range for its own
series — which is the external sanity anchor.

**The one-sided Table 9 residual, explained.** Table 9's cell universe is every
county, *single year* of age, sex and Hispanic origin combination with a non-zero
population for the group. The public Modified Race Data Summary File releases the
population by five-year age group, so the recompute decides membership at the
band the file publishes. That is a strict **superset** of the publisher's cell
set, which is why the recomputed minima sit at or below the published minima and
the recomputed maxima at or above them on most series. The worst single
difference, 0.1140, is on the AIAN+API+BLACK / API maximum, a series with 22,715
cells whose published maximum is attained in a county the superset filter cannot
isolate. Recorded in
`build/build_report.json:independent_verification.publisher_anchor.known_one_sided_bias`.

## Wrong paths

Measured from the shipped input, in tolerance units. Keys match
`expected_values.json#control_gaps` exactly.

| key | route | separation |
|---|---|---|
| `equal_split` | the response split equally over the categories it names — **a drop criterion** | 12.29x min, 366.48x worst, **0 of 31 inside** |
| `proportional_to_area_single_category_counts` | split in proportion to the area's own single-category percentages — **a drop criterion** | 3.62x min, 230.28x worst, **0 of 31 inside** |
| `flat_national_shares` | the published country-wide averages `question.json` ships as an orientation block — **the nearest real competitor, and a drop criterion** | 2.21x min, 149.30x worst, **0 of 31 inside** |
| `composite_model_for_every_group` | the composite table applied to all eleven response groups | 3.33x over the 15 cases it alters |
| `composite_indicator_variables_omitted` | the composite model without its three group indicators | 4.18x over the 8 cases it alters |
| `composite_shares_not_rescaled` | the four-category share reported without the rescale | 0.09x min, 299.17x worst, over the 11 cases it alters |
| `log_transform_of_percent_aian_omitted` | the AIAN percentage entered untransformed where the footnote calls for its logarithm | 0.20x min, 112.59x worst, over the 20 cases it alters |
| `square_of_percent_black_omitted` | the Black percentage entered untransformed where the footnote calls for its square | 0.01x min, 44.89x worst, over the 4 cases it alters |
| `area_covariates_omitted` | the models kept, the four area percentages dropped | 0.44x min, 117.74x worst |
| `contextual_covariates_omitted` | region, urbanisation and area composition all dropped | 0.44x min, 145.06x worst |
| `age_not_capped_at_69` | the record's own age used above the cap | 0.04x min, 1.17x worst, over the 3 cases it alters |
| `hispanic_origin_coded_inverted` | the origin indicator reversed | 0.55x min, 176.01x worst |
| `sex_coded_inverted` | the sex indicator reversed | 0.03x min, 74.42x worst |
| `best_case_tuned_single_constant` | one constant answer, tuned by sweep | **1 case of 31, by construction** |

**Every route reachable without the withheld coefficient set misses all 31
cases**, and that is enforced per case at build time rather than measured
afterwards: a candidate record whose correct share sat within twice the tolerance
of the equal split, the proportional split or the shipped orientation block was
**dropped**, not recorded as non-discriminating. 92,706 candidate records were
swept, 775 were dropped on the equal split, 3,301 on the proportional split,
6,428 on the flat national shares and 14,100 for sitting on a round figure, and
the graded 31 were selected from the 68,685 survivors.
`test_every_graded_case_is_decided_by_the_withheld_models` re-measures the
property on every graded run so it cannot rot. This is the rule
`.omo/S-LAYER-GATE-2026-07-28.md` §§14-15 produce, applied per case.

The routes with cases inside tolerance — `composite_shares_not_rescaled`,
`log_transform_of_percent_aian_omitted`, `square_of_percent_black_omitted`,
`age_not_capped_at_69`, `hispanic_origin_coded_inverted`, `sex_coded_inverted`,
`area_covariates_omitted`, `contextual_covariates_omitted`,
`composite_indicator_variables_omitted` and `composite_model_for_every_group` —
are mis-steps **inside** the published method and are reachable only with the
coefficient set already in hand; each is recorded with its
`non_discriminating_note` and its per-case measurement rather than hidden. The
count of cases "inside tolerance" for a scoped route includes the cases it does
not alter at all, which is why the per-case ledger is stored alongside.

**Constant-answer floor: 0.0323 (1 case of 31)**, measured by an exhaustive sweep
of a single constant answer over [0, 1] at 5e-06 resolution. That is the
arithmetic minimum for a 31-case set and it is reached by construction: no two
goldens sit within 4 tolerances of each other.

## Tolerance rationale

0.002 absolute on a share in [0, 1], the same band for every case.

**Lower bound: zero.** The published coefficients are exact decimals and every
covariate is shipped in the input, so two faithful readings of the same published
model cannot differ at all. The measured spread of the **independent**
re-derivation — a second transcription in a different layout, odds accumulated
multiplicatively, the two-category models inverted by bisection — is **2.2e-16**,
which is 9e12 times inside the band.

**Upper bound: 2.21 tolerances.** The nearest real competitor, the published
country-wide flat shares the input ships as an orientation block, sits that far
away on its closest graded case. Every route reachable without the coefficient
set clears the 2x floor on **every** case, by construction. The margin is
thinnest on `share-R-10` (AREA-04, API+WHITE, API), whose area composition
happens to put the model close to the national average; that is recorded as an
open field in `build/build_report.json`.

The band is therefore wide enough that no faithful reading fails and narrow
enough that no competing method passes. It is also wide enough to absorb a
reasonable implementation choice a with-skill run might make — evaluating the
logistic function directly rather than by a root-find, or accumulating the linear
predictor in a different order — since both agree to machine precision.

## Citations

- Ingram DD, Parker JD, Schenker N, Weed JA, Hamilton B, Arias E, Madans JH.
  *United States Census 2000 population with bridged race categories.* National
  Center for Health Statistics. **Vital Health Stat 2(135). 2003.** Tables 7
  (page 19), 8 (page 19) and 9 (page 20). Source of every coefficient and of the
  Table 9 anchor. Retrieved 2026-07-29 from a raw web.archive.org capture of
  `https://www.cdc.gov/nchs/data/series/sr_02/sr02_135.pdf`, which returns HTTP
  403 to automated fetches; capture URL, HTTP status, byte count and sha256
  `51a4c9f3…29037333` recorded in `build/build_report.json:sources`. The ERIC
  full-text copy `ED481807.pdf` was fetched as a cross-check and is an OCR scan
  that **drops two Table 7 cells**; both are legible in the archived publisher
  PDF and neither was guessed.
- U.S. Census Bureau, **Census 2000 Modified Race Data Summary File**, county
  file `mr-co.txt`, sha256 `9d77dfc5…cbf48053`. Source of the area composition
  percentages.
- U.S. Census Bureau, **Census 2010 Modified Race Data Summary File**, and
  National Center for Health Statistics, **bridged-race April 1, 2010 population
  estimates** `census_0401_2010.txt`, sha256 `f69a2a18…da9d4221`, 4,324,768
  records. Grader-side measurement only; never shipped agent-side.
- National Center for Health Statistics, **bridged-race county probability file**
  `cqs_countyprobs.sas7bdat`, sha256 `0787181d…ab1f537a8`. Source of the
  four-level urbanisation classification only; its probability columns were
  measured and shown to come from a different, expanded model.
- Licence position, the verbatim NCHS Data User Agreement and CDC Use of Agency
  Materials quotes, and the verbatim Census Bureau citation-policy quotes:
  `build/build_report.json#licence`. Note that
  `census.gov/about/policies/open-government/data-policy.html` is a **404** and
  is deliberately not cited.

## Scoring

One case per record, 31 total, read from the JUnit XML and filtered to the
`test_graded_case` prefix. `test.sh` **gates**: if any grader self-check fails or
is skipped, the run scores 0 rather than being graded by a verifier that has
failed its own audit.
