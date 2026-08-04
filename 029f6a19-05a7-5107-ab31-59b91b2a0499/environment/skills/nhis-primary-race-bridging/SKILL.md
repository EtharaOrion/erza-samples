---
name: nhis-primary-race-bridging
description: >-
  Apply the NCHS regression bridging models that convert a multiple-race census
  response into shares of the four 1977-standard single-race categories, using
  the coefficient sets published as Tables 7 and 8 of Vital Health Stat 2(135).
  Use when population counts collected under the 1997 OMB race standard have to
  be made comparable with a data system that still uses the four 1977 categories
  - vital-rate denominators, cause-of-death rates, cancer or natality rates -
  and the inputs give county-level composition, single year of age, sex and
  Hispanic origin. DO NOT USE when the data already carries a bridged single-race
  count, when the multiple-race population is being reported as its own category
  rather than distributed, when the question is about the 1997-standard counts
  themselves, when the year is outside 1997-2010 vintages of the Census Bureau
  Modified Race Data Summary Files, or when whole-person assignment rather than
  fractional assignment is wanted - the whole-assignment methods in the OMB
  provisional guidance are a different procedure and this one does not
  approximate them.
---

# Bridging a multiple-race response to the four 1977 categories

## What this is for

Under the 1997 OMB standard a census respondent may name more than one race, so
a population file has up to 31 race groups. Under the 1977 standard, which many
vital-statistics systems still use, there are four: American Indian or Alaska
Native (AIAN), Asian or Pacific Islander (API), Black or African American
(BLACK) and White (WHITE). Race *bridging* makes the two comparable by
distributing each multiple-race count across the single-race categories it
names, in fractional shares.

The shares are not an arithmetic split. NCHS estimated them by fitting
regressions of *primary race* - which single category a multiple-race respondent
said they would pick - on person-level and county-level covariates, using four
pooled years of the National Health Interview Survey. The fitted coefficients
are published; the survey answers behind them are not. Nothing in a census file
lets you recover them.

## Step 1 - collapse to the four categories, and name the response group

Asian and Native Hawaiian or Other Pacific Islander are a single category, API,
under the 1977 standard. Collapse first, then name the group. Two consequences
that are easy to miss:

- a response of **Asian and Native Hawaiian or Other Pacific Islander is
  single-category API**, not a multiple response, and must not be bridged;
- several of the 31 race groups collapse onto the same bridging group - for
  example White-and-Asian, White-and-NHOPI and White-and-Asian-and-NHOPI all
  become API+WHITE.

After collapsing there are exactly **11 multiple-category response groups**:
AIAN+API, AIAN+BLACK, AIAN+WHITE, API+BLACK, API+WHITE, BLACK+WHITE,
AIAN+API+BLACK, AIAN+API+WHITE, AIAN+BLACK+WHITE, API+BLACK+WHITE and
AIAN+API+BLACK+WHITE.

## Step 2 - choose the model family for the group

This is the first place a run goes wrong. There is no single equation.

| response group | model |
|---|---|
| AIAN+BLACK, AIAN+WHITE, API+BLACK, API+WHITE, BLACK+WHITE | its **own two-category logistic model**, Table 7 |
| AIAN+BLACK+WHITE | its **own three-category multi-logit model**, Table 7, White as the reference outcome |
| AIAN+API, AIAN+API+BLACK, AIAN+API+WHITE, API+BLACK+WHITE, AIAN+API+BLACK+WHITE | the **composite four-outcome multi-logit model**, Table 8 |

The six groups with their own models are the six that had more than 100 survey
respondents choosing a primary race. The other five were too small to fit
separately, so a single composite model was fitted on all multiple-race
respondents and is used for them.

## Step 3 - build the covariate vector

Every model uses the same thirteen covariates plus a constant.

| covariate | how it is coded |
|---|---|
| age per 10 years | single year of age divided by 10. **Ages 70 and over take the value for age 69** - the survey had too few older respondents to support separate estimates, so the age-69 shares were assigned to everyone 70 and over. |
| Hispanic origin | 1 if Hispanic or Latino, else 0 |
| sex | 1 if male, else 0 |
| region | three indicators, Northeast / Midwest / South. **West is the reference** and has no indicator. |
| urbanisation | three indicators, large suburban (large fringe metro) / medium-and-small metropolitan / non-metropolitan. **Large urban (large central metro) is the reference** and has no indicator. |
| percent AIAN in county | the county's percentage of residents reporting AIAN alone |
| percent API in county | the county's percentage reporting API alone |
| percent Black in county | the county's percentage reporting Black alone |
| percent multiple race in county | the county's percentage reporting more than one race |

Percentages are on a **0-100 scale**, not 0-1, and are used exactly as the
Census Bureau Modified Race Data Summary File gives them, **rounded to two
decimal places** before anything else is done to them. Percent single-race White
is deliberately **not** a covariate in any of these models; do not add it.

Two transforms are footnoted on the published tables and are easy to lose:

- the **logarithm** of percent AIAN is used in the AIAN+WHITE model, the
  AIAN+BLACK model and the composite model. The other models use the percentage
  itself.
- the **square** of percent Black is used in the BLACK+WHITE model and the
  AIAN+BLACK model. The other models use the percentage itself.

Where a covariate is marked "not in model" on the published table its
coefficient is zero.

## Step 4a - a two-category group

One linear predictor, one inverse logit. The published column gives the
coefficients for **one** of the two categories; the other is the complement.

```
eta   = constant + sum_k beta_k * x_k
p_modelled = 1 / (1 + exp(-eta))
p_other    = 1 - p_modelled
```

## Step 4b - AIAN+BLACK+WHITE

Two linear predictors, White as the reference outcome:

```
p_AIAN  = exp(eta_AIAN)  / (1 + exp(eta_AIAN) + exp(eta_BLACK))
p_BLACK = exp(eta_BLACK) / (1 + exp(eta_AIAN) + exp(eta_BLACK))
p_WHITE = 1              / (1 + exp(eta_AIAN) + exp(eta_BLACK))
```

## Step 4c - a composite group

The composite model has four outcomes - AIAN, API, BLACK and WHITE - with White
as the reference. It carries three group indicators, `not AIAN`, `not API` and
`not Black`, set to 1 when that category is **not** one of the categories the
response named. **There is no `not White` indicator**, which is why the model
does not distinguish groups that differ only in whether White was named; the
difference between those groups comes from the rescale below, not from the
linear predictors.

When the coefficients for an outcome were estimated, the indicator naming that
same outcome was constrained to zero. That is what the dash means on the
published table - constrained to zero, **not** "omitted from the model". Use
zero for it.

```
eta_AIAN, eta_API, eta_BLACK   from Table 8, including the three indicators
eta_WHITE = 0                  (reference outcome)

p_r = exp(eta_r) / (exp(eta_AIAN) + exp(eta_API) + exp(eta_BLACK) + 1)
```

Then **rescale over the categories the response actually named**, dropping the
others:

```
share_r = p_r / sum over s in the response group of p_s        for r in the group
```

Skipping this rescale is the single most common way to get a composite group
wrong: the raw `p_r` are the shares of *all four* categories, and for a group
that named only two or three of them they do not sum to one.

## Table 7 - the six separate models

Coefficients for the outcome named in each column heading; the remaining
category of the group is the complement. `.` means the variable is not in that
model (coefficient zero).

| covariate | AIAN+BLACK -> BLACK | AIAN+WHITE -> AIAN | API+BLACK -> BLACK | API+WHITE -> API | BLACK+WHITE -> BLACK | AIAN+BLACK+WHITE -> AIAN | AIAN+BLACK+WHITE -> BLACK |
|---|---|---|---|---|---|---|---|
| age per 10 years | -0.05461 | -0.08968 | 0.05669 | 0.09568 | 0.05532 | 0.26212 | 0.36140 |
| Hispanic origin | -1.92602 | 0.88834 | -0.10458 | 0.19303 | -0.52253 | 0.35986 | -0.83526 |
| sex (male) | -0.12359 | 0.00972 | 0.33642 | 0.01393 | 0.11948 | -0.43898 | 0.50777 |
| Northeast | -0.88349 | 0.21233 | -0.45997 | -0.05520 | -0.25363 | -4.53976 | -3.45593 |
| Midwest | -1.70126 | 0.09144 | -3.92403 | -0.06453 | 0.17140 | -3.82328 | -3.79144 |
| South | -0.97935 | -0.28494 | -1.48264 | 0.12694 | -0.64386 | -5.73385 | -2.27313 |
| large suburban | -0.44211 | -0.22069 | 1.46590 | 0.50556 | -0.07649 | 2.78910 | 2.31011 |
| medium/small metropolitan | 0.88281 | -0.44238 | 1.67953 | 0.07443 | 0.28938 | 2.27176 | 0.75477 |
| non-metropolitan | -0.38427 | -0.13978 | 0.13301 | -0.62956 | 0.57636 | 4.17804 | 1.64725 |
| percent AIAN in county | -0.43045 | 0.51235 | . | . | . | 0.54579 | 0.39101 |
| percent API in county | . | . | -0.13245 | 0.00735 | . | . | . |
| percent Black in county | 0.0000258 | . | 0.02078 | . | 0.00079 | 0.11100 | 0.04985 |
| percent multiple race in county | -0.16934 | -0.07906 | 0.31250 | 0.09791 | 0.31679 | -0.23972 | -0.02919 |
| constant | 3.08086 | -0.70527 | 0.45883 | -1.18887 | -0.17533 | -0.64594 | 0.77004 |

Logarithm of percent AIAN in the AIAN+WHITE and AIAN+BLACK columns; square of
percent Black in the BLACK+WHITE and AIAN+BLACK columns.
Source: Ingram DD, Parker JD, Schenker N, Weed JA, Hamilton B, Arias E,
Madans JH. *United States Census 2000 population with bridged race categories.*
National Center for Health Statistics. Vital Health Stat 2(135). 2003, Table 7,
page 19.

## Table 8 - the composite multi-logit model

White is the reference outcome and carries no column. A dash on the published
table means the parameter was **constrained to zero**.

| covariate | AIAN | API | BLACK |
|---|---|---|---|
| not AIAN | 0 (constrained) | 2.78725 | 2.19772 |
| not API | 2.83058 | 0 (constrained) | 3.06153 |
| not Black | 0.97010 | 1.61570 | 0 (constrained) |
| age per 10 years | -0.03967 | 0.01946 | -0.01691 |
| Hispanic origin | 0.84013 | 0.21507 | -0.58721 |
| sex (male) | 0.01914 | 0.01283 | -0.08093 |
| Northeast | 0.59649 | -0.13221 | 0.40115 |
| Midwest | 0.43237 | -0.15172 | 0.20136 |
| South | -0.22255 | -0.24854 | -0.29365 |
| large suburban | 0.15744 | 0.46028 | 0.12070 |
| medium/small metropolitan | -0.17318 | -0.09493 | -0.11129 |
| non-metropolitan | 0.25013 | -0.15342 | -0.12077 |
| percent AIAN in county | 0.56512 | 0.06996 | -0.00347 |
| percent API in county | 0.04203 | 0.03741 | 0.05396 |
| percent Black in county | 0.03921 | 0.03590 | 0.05893 |
| percent multiple race in county | -0.09723 | 0.06402 | -0.03953 |
| constant | -5.29417 | -5.73987 | -5.21431 |

The logarithm of percent AIAN is used in the composite model.
Source: Ingram DD, Parker JD, Schenker N, Weed JA, Hamilton B, Arias E,
Madans JH. *United States Census 2000 population with bridged race categories.*
National Center for Health Statistics. Vital Health Stat 2(135). 2003, Table 8,
page 19.

## Step 5 - sanity checks that can actually disagree

- **The shares of one response group sum to 1** over the categories that group
  named. If they do not, the rescale in Step 4c was skipped or an outcome was
  dropped.
- **Compare against the published distribution.** Table 9 of the same report
  gives the mean, median, interquartile range, minimum and maximum of these
  shares over every county, single year of age, sex and Hispanic origin
  combination in the country. A value outside the published minimum-to-maximum
  range for its own group and category is wrong. The mean is a *national
  average*, not an answer for any particular record: for AIAN+WHITE, for
  example, the AIAN share averages about 0.21 nationally but ranges from about
  0.005 to about 0.91 across counties and ages.
- **Check the direction of the strong effects.** In these fitted equations the
  region and urbanisation terms for AIAN+BLACK+WHITE are very large - several
  units on the linear-predictor scale - so a run that has silently dropped the
  reference-category convention will produce shares near 0 or 1 for that group
  and should notice.

## What this procedure does not give you

It gives **shares**, not counts. Turning shares into a published bridged
population file needs two more steps that are not part of this procedure: the
shares are applied at single year of age, and the resulting fractional counts
are then put through a progressive rounding pass that forces integers while
keeping each county-age-sex-origin total equal to the unbridged total. Applying
these shares to five-year age groups and adding them up will get close to a
published bridged file but will not reproduce it.
