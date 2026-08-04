"""Verifier-side SECOND FORMULATION. Deliberately not the oracle's code.

PROMPT-AUTHOR-TO-30.md 6.1 requires the golden to be confirmed by an independent
recompute that lives IN THE VERIFIER, runs on every graded run, and cannot skip.
Three things make this module independent of `oracle/bridging_models.py` rather
than a copy of it:

1.  A DIFFERENT DATA LAYOUT AND A DIFFERENT TRANSCRIPTION. The oracle stores the
    published tables covariate-major (one row per covariate, seven or three
    columns). This module stores them model-major: one dict per fitted model,
    written out from the published page a second time. A transposition error in
    either transcription shows up as a disagreement rather than cancelling.

2.  A DIFFERENT ALGEBRA. The oracle builds an additive linear predictor and then
    exponentiates. This module accumulates the ODDS as a product of per-covariate
    factors, inverts the two-category models by BISECTION on the logit equation
    rather than by evaluating the logistic function, and computes every
    multi-category model as a CONDITIONAL normalisation over the categories that
    apply - it never forms the four-category vector and then rescales it, which
    is the step the oracle takes. The two routes agree only if both the
    coefficients and the model structure are right.

3.  AN EXTERNAL ANCHOR THAT IS THE PUBLISHER'S, NOT OURS. `anchor_table9.csv`
    carries the distributional characteristics of the bridging proportions that
    NCHS published in Table 9 of the same report - mean, median, interquartile
    bounds, minimum and maximum for all 28 (response group, category) series.
    `table9_statistics()` recomputes those statistics over the published cell
    universe carried in `cell_universe.npz` and the verifier asserts agreement
    with the publisher's own numbers. A mistyped coefficient cannot agree with
    itself here: it would have to be wrong in the oracle, wrong in this
    transcription, and wrong in the publisher's released summary in the same way.

The anchor cannot silently skip: `anchor()` raises `MissingAnchor` when
`anchor_table9.csv` is absent or short, and `test.sh` scores a run 0 when any
grader self-check fails OR is skipped.

Source: Ingram DD, Parker JD, Schenker N, Weed JA, Hamilton B, Arias E,
Madans JH. United States Census 2000 population with bridged race categories.
National Center for Health Statistics. Vital Health Stat 2(135). 2003.
Tables 7, 8 and 9.
"""
from __future__ import annotations

import csv
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ANCHOR_PATH = os.path.join(HERE, "anchor_table9.csv")
UNIVERSE_PATH = os.path.join(HERE, "cell_universe.npz")

CATEGORIES = ("AIAN", "API", "BLACK", "WHITE")

# --------------------------------------------------------------------------- #
# Transcription 2: MODEL-MAJOR. One entry per fitted model equation.
# `outcome` is the category the equation predicts; the reference outcome carries
# no equation. `log_aian` and `sq_black` record the two footnoted transforms.
# --------------------------------------------------------------------------- #
SEPARATE_MODELS = {
    ("AIAN_BLACK", "BLACK"): dict(
        log_aian=True, sq_black=True, beta={
            "age_per_10_years": -0.05461, "hispanic_origin": -1.92602,
            "sex_male": -0.12359, "region_northeast": -0.88349,
            "region_midwest": -1.70126, "region_south": -0.97935,
            "urban_large_fringe": -0.44211, "urban_medium_small_metro": 0.88281,
            "urban_nonmetro": -0.38427, "pct_aian_in_area": -0.43045,
            "pct_black_in_area": 0.0000258, "pct_multiple_in_area": -0.16934,
            "constant": 3.08086}),
    ("AIAN_WHITE", "AIAN"): dict(
        log_aian=True, sq_black=False, beta={
            "age_per_10_years": -0.08968, "hispanic_origin": 0.88834,
            "sex_male": 0.00972, "region_northeast": 0.21233,
            "region_midwest": 0.09144, "region_south": -0.28494,
            "urban_large_fringe": -0.22069, "urban_medium_small_metro": -0.44238,
            "urban_nonmetro": -0.13978, "pct_aian_in_area": 0.51235,
            "pct_multiple_in_area": -0.07906, "constant": -0.70527}),
    ("API_BLACK", "BLACK"): dict(
        log_aian=False, sq_black=False, beta={
            "age_per_10_years": 0.05669, "hispanic_origin": -0.10458,
            "sex_male": 0.33642, "region_northeast": -0.45997,
            "region_midwest": -3.92403, "region_south": -1.48264,
            "urban_large_fringe": 1.46590, "urban_medium_small_metro": 1.67953,
            "urban_nonmetro": 0.13301, "pct_api_in_area": -0.13245,
            "pct_black_in_area": 0.02078, "pct_multiple_in_area": 0.31250,
            "constant": 0.45883}),
    ("API_WHITE", "API"): dict(
        log_aian=False, sq_black=False, beta={
            "age_per_10_years": 0.09568, "hispanic_origin": 0.19303,
            "sex_male": 0.01393, "region_northeast": -0.05520,
            "region_midwest": -0.06453, "region_south": 0.12694,
            "urban_large_fringe": 0.50556, "urban_medium_small_metro": 0.07443,
            "urban_nonmetro": -0.62956, "pct_api_in_area": 0.00735,
            "pct_multiple_in_area": 0.09791, "constant": -1.18887}),
    ("BLACK_WHITE", "BLACK"): dict(
        log_aian=False, sq_black=True, beta={
            "age_per_10_years": 0.05532, "hispanic_origin": -0.52253,
            "sex_male": 0.11948, "region_northeast": -0.25363,
            "region_midwest": 0.17140, "region_south": -0.64386,
            "urban_large_fringe": -0.07649, "urban_medium_small_metro": 0.28938,
            "urban_nonmetro": 0.57636, "pct_black_in_area": 0.00079,
            "pct_multiple_in_area": 0.31679, "constant": -0.17533}),
    ("AIAN_BLACK_WHITE", "AIAN"): dict(
        log_aian=False, sq_black=False, beta={
            "age_per_10_years": 0.26212, "hispanic_origin": 0.35986,
            "sex_male": -0.43898, "region_northeast": -4.53976,
            "region_midwest": -3.82328, "region_south": -5.73385,
            "urban_large_fringe": 2.78910, "urban_medium_small_metro": 2.27176,
            "urban_nonmetro": 4.17804, "pct_aian_in_area": 0.54579,
            "pct_black_in_area": 0.11100, "pct_multiple_in_area": -0.23972,
            "constant": -0.64594}),
    ("AIAN_BLACK_WHITE", "BLACK"): dict(
        log_aian=False, sq_black=False, beta={
            "age_per_10_years": 0.36140, "hispanic_origin": -0.83526,
            "sex_male": 0.50777, "region_northeast": -3.45593,
            "region_midwest": -3.79144, "region_south": -2.27313,
            "urban_large_fringe": 2.31011, "urban_medium_small_metro": 0.75477,
            "urban_nonmetro": 1.64725, "pct_aian_in_area": 0.39101,
            "pct_black_in_area": 0.04985, "pct_multiple_in_area": -0.02919,
            "constant": 0.77004}),
}
TWO_CATEGORY = {
    "AIAN_BLACK": ("BLACK", "AIAN"),
    "AIAN_WHITE": ("AIAN", "WHITE"),
    "API_BLACK": ("BLACK", "API"),
    "API_WHITE": ("API", "WHITE"),
    "BLACK_WHITE": ("BLACK", "WHITE"),
}
THREE_CATEGORY = {"AIAN_BLACK_WHITE": ("AIAN", "BLACK", "WHITE")}

# Composite multi-logit, model-major. White is the reference outcome.
COMPOSITE_MODELS = {
    "AIAN": {"indicator_not_aian": 0.00000, "indicator_not_api": 2.83058,
             "indicator_not_black": 0.97010, "age_per_10_years": -0.03967,
             "hispanic_origin": 0.84013, "sex_male": 0.01914,
             "region_northeast": 0.59649, "region_midwest": 0.43237,
             "region_south": -0.22255, "urban_large_fringe": 0.15744,
             "urban_medium_small_metro": -0.17318, "urban_nonmetro": 0.25013,
             "pct_aian_in_area": 0.56512, "pct_api_in_area": 0.04203,
             "pct_black_in_area": 0.03921, "pct_multiple_in_area": -0.09723,
             "constant": -5.29417},
    "API": {"indicator_not_aian": 2.78725, "indicator_not_api": 0.00000,
            "indicator_not_black": 1.61570, "age_per_10_years": 0.01946,
            "hispanic_origin": 0.21507, "sex_male": 0.01283,
            "region_northeast": -0.13221, "region_midwest": -0.15172,
            "region_south": -0.24854, "urban_large_fringe": 0.46028,
            "urban_medium_small_metro": -0.09493, "urban_nonmetro": -0.15342,
            "pct_aian_in_area": 0.06996, "pct_api_in_area": 0.03741,
            "pct_black_in_area": 0.03590, "pct_multiple_in_area": 0.06402,
            "constant": -5.73987},
    "BLACK": {"indicator_not_aian": 2.19772, "indicator_not_api": 3.06153,
              "indicator_not_black": 0.00000, "age_per_10_years": -0.01691,
              "hispanic_origin": -0.58721, "sex_male": -0.08093,
              "region_northeast": 0.40115, "region_midwest": 0.20136,
              "region_south": -0.29365, "urban_large_fringe": 0.12070,
              "urban_medium_small_metro": -0.11129, "urban_nonmetro": -0.12077,
              "pct_aian_in_area": -0.00347, "pct_api_in_area": 0.05396,
              "pct_black_in_area": 0.05893, "pct_multiple_in_area": -0.03953,
              "constant": -5.21431},
}
COMPOSITE_APPLICABLE = {
    "AIAN_API": ("AIAN", "API"),
    "AIAN_API_BLACK": ("AIAN", "API", "BLACK"),
    "AIAN_API_WHITE": ("AIAN", "API", "WHITE"),
    "API_BLACK_WHITE": ("API", "BLACK", "WHITE"),
    "AIAN_API_BLACK_WHITE": ("AIAN", "API", "BLACK", "WHITE"),
}
APPLICABLE = dict(TWO_CATEGORY)
APPLICABLE.update({"AIAN_BLACK": ("AIAN", "BLACK"), "AIAN_WHITE": ("AIAN", "WHITE"),
                   "API_BLACK": ("API", "BLACK"), "API_WHITE": ("API", "WHITE"),
                   "BLACK_WHITE": ("BLACK", "WHITE")})
APPLICABLE.update(THREE_CATEGORY)
APPLICABLE.update(COMPOSITE_APPLICABLE)
GROUPS = tuple(APPLICABLE)

AGE_CAP = 69
REGIONS = ("northeast", "midwest", "south", "west")
URBANISATIONS = ("large_central", "large_fringe", "medium_small_metro", "nonmetro")

# Domain-plausible envelope for an assignment share. Anything outside is an
# arithmetic or unit error rather than a hard case.
ENVELOPE = (0.0, 1.0)


class MissingAnchor(Exception):
    """The publisher's anchor is absent. Never a skip - always a hard failure."""


# --------------------------------------------------------------------------- #
# covariate vector
# --------------------------------------------------------------------------- #

def covariates(area, age, sex_male, hispanic, log_aian, sq_black):
    pct_aian = float(area["pct_aian_alone"])
    pct_black = float(area["pct_black_alone"])
    return {
        "age_per_10_years": min(int(age), AGE_CAP) / 10.0,
        "hispanic_origin": 1.0 if hispanic else 0.0,
        "sex_male": 1.0 if sex_male else 0.0,
        "region_northeast": 1.0 if area["region"] == "northeast" else 0.0,
        "region_midwest": 1.0 if area["region"] == "midwest" else 0.0,
        "region_south": 1.0 if area["region"] == "south" else 0.0,
        "urban_large_fringe": 1.0 if area["urbanisation"] == "large_fringe" else 0.0,
        "urban_medium_small_metro":
            1.0 if area["urbanisation"] == "medium_small_metro" else 0.0,
        "urban_nonmetro": 1.0 if area["urbanisation"] == "nonmetro" else 0.0,
        "pct_aian_in_area": math.log(pct_aian) if log_aian else pct_aian,
        "pct_api_in_area": float(area["pct_api_alone"]),
        "pct_black_in_area": pct_black ** 2 if sq_black else pct_black,
        "pct_multiple_in_area": float(area["pct_multiple_response"]),
        "constant": 1.0,
    }


def _odds(beta, x, indicators=None):
    """The odds against the reference outcome, accumulated MULTIPLICATIVELY.

    exp(sum(b*x)) computed as prod(exp(b*x)) - a different arithmetic path from
    the oracle's single exponential of a summed linear predictor.
    """
    product = 1.0
    for name, b in beta.items():
        if indicators is not None and name in indicators:
            value = indicators[name]
        else:
            value = x[name]
        if b == 0.0 or value == 0.0:
            continue
        product *= math.exp(b * value)
    return product


def _probability_from_odds_by_bisection(odds):
    """Solve logit(p) = ln(odds) for p by bisection.

    Deliberately NOT p = odds / (1 + odds): a root-find on the defining equation
    is a numerically independent inversion, so a mis-stated logistic function in
    either module shows up as a disagreement.
    """
    target = math.log(odds)
    lo, hi = 1e-15, 1.0 - 1e-15
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if math.log(mid / (1.0 - mid)) < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def shares(group, area, age, sex_male, hispanic):
    """The assignment shares for one response group in one cell."""
    if group in TWO_CATEGORY:
        modelled, other = TWO_CATEGORY[group]
        spec = SEPARATE_MODELS[(group, modelled)]
        x = covariates(area, age, sex_male, hispanic,
                       spec["log_aian"], spec["sq_black"])
        p = _probability_from_odds_by_bisection(_odds(spec["beta"], x))
        return {modelled: p, other: 1.0 - p}

    if group in THREE_CATEGORY:
        # Conditional normalisation over the three outcomes, with the reference
        # outcome carrying odds 1. No four-category vector is ever formed.
        odds = {"WHITE": 1.0}
        for outcome in ("AIAN", "BLACK"):
            spec = SEPARATE_MODELS[(group, outcome)]
            x = covariates(area, age, sex_male, hispanic,
                           spec["log_aian"], spec["sq_black"])
            odds[outcome] = _odds(spec["beta"], x)
        total = sum(odds.values())
        return {k: v / total for k, v in odds.items()}

    if group in COMPOSITE_APPLICABLE:
        applicable = COMPOSITE_APPLICABLE[group]
        x = covariates(area, age, sex_male, hispanic, True, False)
        indicators = {
            "indicator_not_aian": 0.0 if "AIAN" in applicable else 1.0,
            "indicator_not_api": 0.0 if "API" in applicable else 1.0,
            "indicator_not_black": 0.0 if "BLACK" in applicable else 1.0,
        }
        odds = {}
        for category in applicable:
            if category == "WHITE":
                odds["WHITE"] = 1.0
            else:
                odds[category] = _odds(COMPOSITE_MODELS[category], x, indicators)
        total = sum(odds.values())
        return {k: v / total for k, v in odds.items()}

    raise KeyError("unknown response group %r" % (group,))


# --------------------------------------------------------------------------- #
# vectorised path, used only for the publisher anchor
# --------------------------------------------------------------------------- #

_ORDER = ("age_per_10_years", "hispanic_origin", "sex_male", "region_northeast",
          "region_midwest", "region_south", "urban_large_fringe",
          "urban_medium_small_metro", "urban_nonmetro", "pct_aian_in_area",
          "pct_api_in_area", "pct_black_in_area", "pct_multiple_in_area",
          "constant")


def _design_matrix(cov, age, hispanic, male, log_aian, sq_black):
    """cov: (n, 4) region index, urban index, and the four percentages come from
    the arrays passed in. Returns the (n, 14) design matrix in _ORDER."""
    region, urban, pa, pi, pb, pm = cov
    n = len(age)
    out = np.empty((n, len(_ORDER)))
    out[:, 0] = np.minimum(age, AGE_CAP) / 10.0
    out[:, 1] = hispanic
    out[:, 2] = male
    out[:, 3] = (region == REGIONS.index("northeast"))
    out[:, 4] = (region == REGIONS.index("midwest"))
    out[:, 5] = (region == REGIONS.index("south"))
    out[:, 6] = (urban == URBANISATIONS.index("large_fringe"))
    out[:, 7] = (urban == URBANISATIONS.index("medium_small_metro"))
    out[:, 8] = (urban == URBANISATIONS.index("nonmetro"))
    out[:, 9] = np.log(pa) if log_aian else pa
    out[:, 10] = pi
    out[:, 11] = pb ** 2 if sq_black else pb
    out[:, 12] = pm
    out[:, 13] = 1.0
    return out


def _beta_vector(beta):
    return np.array([beta.get(name, 0.0) for name in _ORDER])


def shares_vectorised(group, cov, age, hispanic, male):
    """{category: array} for one response group over many cells."""
    if group in TWO_CATEGORY:
        modelled, other = TWO_CATEGORY[group]
        spec = SEPARATE_MODELS[(group, modelled)]
        X = _design_matrix(cov, age, hispanic, male,
                           spec["log_aian"], spec["sq_black"])
        eta = X @ _beta_vector(spec["beta"])
        p = 1.0 / (1.0 + np.exp(-eta))
        return {modelled: p, other: 1.0 - p}

    if group in THREE_CATEGORY:
        eta = {"WHITE": np.zeros(len(age))}
        for outcome in ("AIAN", "BLACK"):
            spec = SEPARATE_MODELS[(group, outcome)]
            X = _design_matrix(cov, age, hispanic, male,
                               spec["log_aian"], spec["sq_black"])
            eta[outcome] = X @ _beta_vector(spec["beta"])
        return _softmax(eta)

    applicable = COMPOSITE_APPLICABLE[group]
    X = _design_matrix(cov, age, hispanic, male, True, False)
    eta = {}
    for category in applicable:
        if category == "WHITE":
            eta["WHITE"] = np.zeros(len(age))
            continue
        beta = dict(COMPOSITE_MODELS[category])
        shift = 0.0
        for key, present in (("indicator_not_aian", "AIAN" in applicable),
                             ("indicator_not_api", "API" in applicable),
                             ("indicator_not_black", "BLACK" in applicable)):
            if not present:
                shift += beta[key]
            beta.pop(key)
        eta[category] = X @ _beta_vector(beta) + shift
    return _softmax(eta)


def _softmax(eta):
    """Normalise over the categories present, subtracting the row maximum first.

    The shift-invariant form is a third structural difference from the oracle,
    which divides by an explicitly formed denominator of raw exponentials.
    """
    keys = list(eta)
    stack = np.vstack([eta[k] for k in keys])
    stack = stack - stack.max(axis=0, keepdims=True)
    e = np.exp(stack)
    e = e / e.sum(axis=0, keepdims=True)
    return {k: e[i] for i, k in enumerate(keys)}


# --------------------------------------------------------------------------- #
# the publisher's anchor
# --------------------------------------------------------------------------- #

_CACHE = {}


def anchor(path: str = ANCHOR_PATH) -> dict:
    """{(group, category): {stat: published value}} from NCHS Table 9."""
    if path in _CACHE:
        return _CACHE[path]
    if not os.path.exists(path):
        raise MissingAnchor(
            "anchor_table9.csv is missing from %s - the independent formulation "
            "has no published series to check itself against and MUST fail "
            "rather than skip" % path)
    out = {}
    with open(path) as fh:
        for row in csv.DictReader(fh):
            out[(row["response_group"], row["target_category"])] = {
                k: float(row[k]) for k in ("mean", "median", "q1", "q3", "min", "max")}
    if len(out) < 28:
        raise MissingAnchor(
            "anchor_table9.csv carries only %d published series; the report "
            "publishes 28" % len(out))
    _CACHE[path] = out
    return out


def cell_universe(path: str = UNIVERSE_PATH):
    if path in _CACHE:
        return _CACHE[path]
    if not os.path.exists(path):
        raise MissingAnchor(
            "cell_universe.npz is missing from %s - the publisher anchor cannot "
            "be recomputed and MUST fail rather than skip" % path)
    data = np.load(path)
    if data["present"].shape[0] < 3000:
        raise MissingAnchor("cell_universe.npz carries only %d areas; the "
                            "published file covers every US county"
                            % data["present"].shape[0])
    _CACHE[path] = data
    return data


# Census 2000 Modified Race age groups: 1 = under 1, 2 = 1-4, 3 = 5-9 ... 19 = 85+
AGE_BAND = {0: [0], 1: [1, 2, 3, 4], 18: [85]}
for _k in range(2, 18):
    AGE_BAND[_k] = list(range(5 * (_k - 1), 5 * (_k - 1) + 5))
# mr-co.txt block order: Hispanic male, Hispanic female, non-Hispanic male,
# non-Hispanic female
BLOCK_HISPANIC = (1.0, 1.0, 0.0, 0.0)
BLOCK_MALE = (1.0, 0.0, 1.0, 0.0)


def table9_statistics():
    """Recompute NCHS Table 9 over the published cell universe.

    The universe is every (county, single year of age, sex, Hispanic origin)
    combination with a non-zero enumerated population for the response group, as
    Table 9 states. The public Modified Race Data Summary File releases the
    population by five-year age group rather than by single year, so membership
    is decided at the band the file publishes; that is a documented SUPERSET of
    the publisher's own cell set, and `build/build_report.json` records the
    resulting one-sided bias in the tails.
    """
    data = cell_universe()
    region = data["region"]
    urban = data["urbanisation"]
    pa, pi, pb, pm = (data["pct_aian_alone"], data["pct_api_alone"],
                      data["pct_black_alone"], data["pct_multiple_response"])
    present = data["present"]                     # (n_area, 19, 4, 11) bool
    groups = [str(g) for g in data["groups"]]
    out = {}
    for gi, group in enumerate(groups):
        area_idx, ages, hisp, male = [], [], [], []
        for band in range(19):
            for block in range(4):
                sel = np.nonzero(present[:, band, block, gi])[0]
                if not len(sel):
                    continue
                for single_year in AGE_BAND[band]:
                    area_idx.append(sel)
                    ages.append(np.full(len(sel), single_year, dtype=float))
                    hisp.append(np.full(len(sel), BLOCK_HISPANIC[block]))
                    male.append(np.full(len(sel), BLOCK_MALE[block]))
        idx = np.concatenate(area_idx)
        cov = (region[idx], urban[idx], pa[idx], pi[idx], pb[idx], pm[idx])
        result = shares_vectorised(group, cov, np.concatenate(ages),
                                   np.concatenate(hisp), np.concatenate(male))
        for category, values in result.items():
            out[(group, category)] = {
                "mean": float(values.mean()),
                "median": float(np.median(values)),
                "q1": float(np.percentile(values, 25)),
                "q3": float(np.percentile(values, 75)),
                "min": float(values.min()),
                "max": float(values.max()),
                "n_cells": int(values.size),
            }
    return out
