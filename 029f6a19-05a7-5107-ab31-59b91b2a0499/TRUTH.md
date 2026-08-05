# TRUTH.md — bridged-race-population-estimates (golden trajectory)

The ordered moves a competent run makes, from opening the task to writing the
answer. Each step says **what to do and why**; **no step states what it evaluates
to**. Derived from `oracle/solve.sh` with every produced value stripped out: no
graded share, no fitted constant, no tolerance and no golden appears anywhere in
this file.

**Method is kept; step answers are stripped.** The relations below are complete —
which family of equations governs which response group, how the covariate vector
is coded, which two covariates are transformed, which categories are reference
categories, where the age variable is capped, how a multi-outcome model is
normalised, and where the conditional rescale goes. What is deliberately **not**
printed here is the fitted constant set. Those constants are the withheld object
the task exists to measure, and this file is handed to an LLM judge; printing
them would make it a second answer key, which `PROMPT-AUTHOR-TO-30.md` §6.11
forbids.

---

## What is being asked

One row per record. Each record names an area, a single year of age, a sex, a
Hispanic-origin status, a **response group** — the set of legacy categories the
census response named, joined by `+` — and a **target category**, one member of
that group. For each record: the share of that response group assigned to that
target category. Thirty-one graded figures, one output object, one file.

The records, the area profiles and the output contract come from `/root/data`.
All of them are supplied.

## Delta-lever

A census response naming more than one category is split across those categories
with a **fitted equation set the national statistics agency estimated from a
household survey**, evaluated on the person's own age, sex and origin and on the
composition of the area they live in — not by splitting the response evenly and
not in proportion to the area's own single-category counts.

Everything else in this task — reading two CSVs, joining them on the area label,
writing a JSON object — is work a competent run does correctly without help. The
lever is entirely in *which equation family governs this response group*, *how
the covariate vector is coded*, and *how the equation's output is normalised over
the categories the response actually named*.

## The crux

**The crux is Step 3: every record is priced with the fitted equation the
publisher estimated for that record's own response group, evaluated on that
record's own covariates.**

It has four failure surfaces. The first three are separately fatal; the fourth is
fatal only for the five response groups it applies to, and is recorded with that
scope rather than asserted to be fatal everywhere:

1. **An arithmetic split.** Splitting the response evenly over the categories it
   names, or in proportion to the area's own single-category percentages. These
   are the two routes available to a run that does not hold the equations, and
   the graded set is built so that **both miss every graded record by more than
   twice the tolerance** — that property is asserted per record at build time and
   re-measured on every graded run.
2. **The published country-wide averages substituted for the record's own
   value.** The input carries them, plainly labelled as orientation only. They
   get the response group right and drop every covariate, which is exactly the
   dimension the equations supply. This is the nearest real competitor.
3. **One equation family for all eleven response groups.** Six groups have their
   own fitted equations and five share a composite one; a run that finds one
   table and applies it everywhere has collapsed the model-selection step.
4. **The composite output not rescaled.** The composite equation produces a share
   for each of the four legacy categories. A response group that named only two
   or three of them needs those shares renormalised over the ones it named. A run
   that reports the raw share has reported the share of a different quantity.

The gap between the correct value and each of these is measured, per route, in
`../expected_values.json` under `control_gaps`.

## Step 0 — Read the input

Open `/root/data/response_records.csv`, `/root/data/area_profile.csv` and
`/root/data/question.json`. The records carry the person-level fields and the
response group; the area profile carries each area's composition, its census
region and how urban it is; the JSON carries the record list, what each category
code means, the output contract and the orientation block.

`area_id` is an opaque label and carries no information beyond the row it points
at. Thirty-one records over eleven response groups and four target categories is
more than can be done reliably by hand, so a solver is written and run.

## Step 1 — Establish that the split is not arithmetic

A response naming two categories is not half and half, and it is not in the ratio
of the area's own single-category counts. The publisher estimated the split from
a household survey that asked people who named several categories which single
one they would have chosen, and fitted equations relating that answer to the
person's characteristics and to the area's composition. The survey answers were
never released; only the fitted constants were.

Two consequences a run should draw before computing anything: the split depends
on covariates, so two records in the same response group with different ages or
different areas have different answers; and no quantity in the input stands in a
fixed ratio to any graded figure, so the constants cannot be recovered from the
data supplied.

## Step 2 — Choose the equation family for the response group

The response group is the join key, and there is no single equation.

- Five two-category groups and one three-category group have **their own fitted
  equations**, because the survey had enough respondents in each to fit
  separately.
- The remaining five groups share a **single composite equation set** fitted on
  all multiple-category respondents together, because each was too small on its
  own.

Deciding this before Step 3 is what separates a run that has read the method from
one that has found a table. Note also that the composite set carries indicators
for which categories the response did *not* name, and that there is no indicator
for one of the four categories — so the composite equations alone do not
distinguish every group, and the distinction is completed by the rescale at
Step 4.

## Step 3 — Build the covariate vector  *(crux)*

Every equation reads the same covariates:

- age in single years, entered **per ten years**, and **capped**: the survey
  could not support separate estimates at the oldest ages, so every record at 70
  and over takes the value the equations give at 69;
- Hispanic origin and sex, each as a 0/1 indicator;
- census region as three indicators, with **one region as the reference** and no
  indicator of its own;
- urbanisation as three indicators, with **the most urban level as the
  reference** and no indicator of its own;
- the area's percentage of residents reporting each of three single categories,
  and the percentage reporting more than one. These are on a 0-100 scale.

Two of the area percentages are **transformed** before they enter, and which
transform applies depends on which equation is being evaluated — one enters as a
logarithm in some equations and untransformed in others, and another enters as a
square in some and untransformed in others. The published table footnotes name
the equations each transform belongs to; applying a transform everywhere, or
nowhere, is a distinct error from omitting the covariate.

The percentage of residents reporting the fourth single category is supplied in
the input and is **not** a covariate of any of these equations. It is there
because it is part of an area's composition, not because the equations use it.

A cell of the published table marked "not in model" is a zero coefficient, and a
cell marked with a dash in the composite table means the parameter was
*constrained to zero* — which is also a zero, but for a different reason, and a
run that reads it as "omit this term" has changed the model.

## Step 4 — Normalise, then rescale

- **A two-category group** has one linear predictor and one inverse logit; the
  other category is the complement.
- **The three-category group with its own equations** has two linear predictors
  and one reference outcome carrying no equation; the three shares are the
  exponentials of the predictors and one, all over their sum.
- **A composite group** has three linear predictors and one reference outcome
  carrying no equation, giving a share for each of the four legacy categories.
  Those four do not answer the question. **Rescale them over the categories the
  response group actually named**, dropping the rest, so the reported shares of
  one response group sum to one over that group.

## Step 5 — Sanity-check against something that can disagree

A sound run checks before writing. Three checks that can actually fail:

- **The group closes.** Compute every share of a record's response group, not
  only the one asked for, and confirm they sum to one over the categories that
  group named. A missed rescale fails here immediately.
- **The published distribution.** The same report that carries the equations also
  publishes the mean, median, interquartile range, minimum and maximum of these
  shares across the whole country, for each response group and category. A value
  outside the published minimum-to-maximum range for its own series is wrong.
  This is the check `../independent_bridging.py:table9_statistics` performs on
  the whole country at once.
- **The direction of the strong terms.** Some of the fitted region and
  urbanisation terms are large on the linear-predictor scale. A run that has
  silently dropped the reference-category convention — by giving every level an
  indicator, or by giving the reference one — will produce shares pinned near 0
  or 1 for the affected group, which is visible without knowing the answer.

## Step 6 — Emit the contract

Write `/root/results.json` with exactly one top-level object,
`assignment_share`, keyed by `record_id`, with one numeric, finite value per
record in `question.json`'s `records_to_report`, at six or more decimal places.
The key and the number shown in the prompt are a shape illustration: the record
id in it is not in the input and the number is far outside the range a share can
take, so copying either through is not an answer.

## Where runs break

Each route below is recomputed at build time and recorded in
`../expected_values.json:control_gaps` with its distance from the reference in
tolerance units.

- **The even split** — the response divided equally over the categories it names.
  Available without the equations, and asserted per record to miss.
- **The composition split** — the response divided in proportion to the area's own
  single-category percentages. Also available without the equations, and also
  asserted per record to miss.
- **The orientation block echoed** — the published country-wide averages the input
  supplies, copied into the answer. The nearest real competitor, and the input
  labels it honestly.
- **One equation family for every group** — the composite set applied to all
  eleven groups, or a two-category equation stretched over a group it was not
  fitted for.
- **The composite output not rescaled** — the four-category share reported as
  though it were the group's share.
- **A transform applied in the wrong equations** — the logarithm or the square
  taken everywhere, or nowhere, instead of in the equations the footnotes name.
- **The reference category given an indicator** — every region or every
  urbanisation level entered, which double-counts the reference.
- **The age cap ignored** — the record's own age used above the capped value.
- **The origin or sex indicator inverted** — the input spells these as words and
  the equations code them as 0/1.

## What cannot be done

The fitted constants are not recoverable from the supplied input. There is no
share anywhere in `/root/data` — the records carry only covariates and the
orientation block is a national average that is deliberately not any record's
answer — so no quantity in the input stands in a fixed ratio to a graded figure
and nothing can be back-solved by division. A run that claims to have derived the
constants from the data has not; judge such a claim on the arithmetic it shows,
not on its confidence.

Equally, the graded figures are not published anywhere as a table. The areas are
opaque labels, so a figure a model regenerates from its own weights — a national
average, a headline statistic — is not an answer to this task even when it lands
nearby.

## Sources

- **The fitted equations, and the published distribution quoted at Step 5** —
  Ingram DD, Parker JD, Schenker N, Weed JA, Hamilton B, Arias E, Madans JH.
  *United States Census 2000 population with bridged race categories.* National
  Center for Health Statistics. Vital Health Stat 2(135). 2003, Tables 7, 8
  and 9. Retrieved from a raw web.archive.org capture of
  `https://www.cdc.gov/nchs/data/series/sr_02/sr02_135.pdf`, which returns HTTP
  403 to automated fetches; sha256 recorded in
  `../../build/build_report.json:sources`.
- **The area composition percentages** — U.S. Census Bureau, Census 2000 Modified
  Race Data Summary File, county file `mr-co.txt`, reconstructed and checked
  against the values the agency itself carries; see
  `../../build/build_report.json:area_covariates_are_the_publishers_own`.
- **The records, the area labels and the output contract** —
  `../../environment/data/`, mirrored in `../expected_values.json`.
- **The per-route separations quoted under "Where runs break"** —
  `../expected_values.json:control_gaps`, each recomputed at build time.
