"""Forward implementation of the NCHS regression race-bridging models.

TRANSCRIPTION 1 of 4 (the oracle's). The same coefficient set is transcribed
independently in `tests/independent_bridging.py`, in `tests/checks.py` and in
the author-side rederivation matrix; `tests/sr02_135_table7.csv` and
`tests/sr02_135_table8.csv` are the machine-readable slice cut from the
published PDF, and every transcription is asserted against that slice.

Source: Ingram DD, Parker JD, Schenker N, Weed JA, Hamilton B, Arias E, Madans JH.
United States Census 2000 population with bridged race categories. National Center
for Health Statistics. Vital Health Stat 2(135). 2003.  Table 7 (six separate
logistic regression models) and Table 8 (composite multi-logit model).
"""
from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Table 7 - six separate models.  Column order:
#   0 AIAN/Black          -> Black          (complement: AIAN)
#   1 AIAN/White          -> AIAN           (complement: White)
#   2 API/Black           -> Black          (complement: API)
#   3 API/White           -> API            (complement: White)
#   4 Black/White         -> Black          (complement: White)
#   5 AIAN/Black/White    -> AIAN           (White is the reference outcome)
#   6 AIAN/Black/White    -> Black
# ---------------------------------------------------------------------------
TABLE7 = {
    "age_per_10_years":         (-0.05461, -0.08968,  0.05669,  0.09568,  0.05532,  0.26212,  0.36140),
    "hispanic_origin":          (-1.92602,  0.88834, -0.10458,  0.19303, -0.52253,  0.35986, -0.83526),
    "sex_male":                 (-0.12359,  0.00972,  0.33642,  0.01393,  0.11948, -0.43898,  0.50777),
    "region_northeast":         (-0.88349,  0.21233, -0.45997, -0.05520, -0.25363, -4.53976, -3.45593),
    "region_midwest":           (-1.70126,  0.09144, -3.92403, -0.06453,  0.17140, -3.82328, -3.79144),
    "region_south":             (-0.97935, -0.28494, -1.48264,  0.12694, -0.64386, -5.73385, -2.27313),
    "urban_large_fringe":       (-0.44211, -0.22069,  1.46590,  0.50556, -0.07649,  2.78910,  2.31011),
    "urban_medium_small_metro": ( 0.88281, -0.44238,  1.67953,  0.07443,  0.28938,  2.27176,  0.75477),
    "urban_nonmetro":           (-0.38427, -0.13978,  0.13301, -0.62956,  0.57636,  4.17804,  1.64725),
    "pct_aian_in_area":         (-0.43045,  0.51235,  None,     None,     None,      0.54579,  0.39101),
    "pct_api_in_area":          ( None,     None,    -0.13245,  0.00735,  None,      None,     None),
    "pct_black_in_area":        ( 0.0000258, None,    0.02078,  None,     0.00079,   0.11100,  0.04985),
    "pct_multiple_in_area":     (-0.16934, -0.07906,  0.31250,  0.09791,  0.31679,  -0.23972, -0.02919),
    "constant":                 ( 3.08086, -0.70527,  0.45883, -1.18887, -0.17533,  -0.64594,  0.77004),
}
# Table 7 footnote 4: the LOGARITHM of percent AIAN enters the AIAN/White and
# AIAN/Black models.  Everywhere else the percent enters untransformed.
TABLE7_LOG_AIAN = (True, True, False, False, False, False, False)
# Table 7 footnote 5: the SQUARE of percent Black enters the Black/White and
# AIAN/Black models.
TABLE7_SQ_BLACK = (True, False, False, False, True, False, False)

# ---------------------------------------------------------------------------
# Table 8 - composite multi-logit.  Outcome order: AIAN, API, Black.  White is
# the reference outcome and carries no coefficients.  The indicator whose own
# outcome it names is constrained to zero.
# Table 8 footnote 4: the LOGARITHM of percent AIAN is used in the model.
# ---------------------------------------------------------------------------
TABLE8 = {
    "indicator_not_aian":       ( 0.00000,  2.78725,  2.19772),
    "indicator_not_api":        ( 2.83058,  0.00000,  3.06153),
    "indicator_not_black":      ( 0.97010,  1.61570,  0.00000),
    "age_per_10_years":         (-0.03967,  0.01946, -0.01691),
    "hispanic_origin":          ( 0.84013,  0.21507, -0.58721),
    "sex_male":                 ( 0.01914,  0.01283, -0.08093),
    "region_northeast":         ( 0.59649, -0.13221,  0.40115),
    "region_midwest":           ( 0.43237, -0.15172,  0.20136),
    "region_south":             (-0.22255, -0.24854, -0.29365),
    "urban_large_fringe":       ( 0.15744,  0.46028,  0.12070),
    "urban_medium_small_metro": (-0.17318, -0.09493, -0.11129),
    "urban_nonmetro":           ( 0.25013, -0.15342, -0.12077),
    "pct_aian_in_area":         ( 0.56512,  0.06996, -0.00347),
    "pct_api_in_area":          ( 0.04203,  0.03741,  0.05396),
    "pct_black_in_area":        ( 0.03921,  0.03590,  0.05893),
    "pct_multiple_in_area":     (-0.09723,  0.06402, -0.03953),
    "constant":                 (-5.29417, -5.73987, -5.21431),
}

# group -> (Table 7 column, outcome that column predicts, the other outcome)
SEPARATE_TWO = {
    "AIAN_BLACK":  (0, "BLACK", "AIAN"),
    "AIAN_WHITE":  (1, "AIAN",  "WHITE"),
    "API_BLACK":   (2, "BLACK", "API"),
    "API_WHITE":   (3, "API",   "WHITE"),
    "BLACK_WHITE": (4, "BLACK", "WHITE"),
}
SEPARATE_THREE = "AIAN_BLACK_WHITE"
COMPOSITE = {
    "AIAN_API":             ("AIAN", "API"),
    "AIAN_API_BLACK":       ("AIAN", "API", "BLACK"),
    "AIAN_API_WHITE":       ("AIAN", "API", "WHITE"),
    "API_BLACK_WHITE":      ("API", "BLACK", "WHITE"),
    "AIAN_API_BLACK_WHITE": ("AIAN", "API", "BLACK", "WHITE"),
}
GROUPS = (list(SEPARATE_TWO) + [SEPARATE_THREE] + list(COMPOSITE))
CATEGORIES = ("AIAN", "API", "BLACK", "WHITE")

# The probabilities for persons 69 years of age were assigned to persons 70
# years of age and over (Vital Health Stat 2(135), NHIS Bridging Proportions).
AGE_CAP = 69


def _design(area, age, sex_male, hispanic, log_aian, sq_black):
    """The covariate vector, in the order the coefficient tables use."""
    pct_aian = area["pct_aian_alone"]
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
        "pct_api_in_area": area["pct_api_alone"],
        "pct_black_in_area": (area["pct_black_alone"] ** 2 if sq_black
                              else area["pct_black_alone"]),
        "pct_multiple_in_area": area["pct_multiple_response"],
        "constant": 1.0,
    }


def _linear_predictor(table, column, design, extra=None):
    total = 0.0
    for name, row in table.items():
        beta = row[column]
        if beta is None:
            continue                      # "... Variable not in model."
        if extra is not None and name in extra:
            total += beta * extra[name]
        else:
            total += beta * design[name]
    return total


def proportions(group, area, age, sex_male, hispanic):
    """The assignment shares for one response group in one cell.

    Returns {category: share}, summing to 1 over the categories the group can be
    assigned to.
    """
    if group in SEPARATE_TWO:
        col, modelled, other = SEPARATE_TWO[group]
        design = _design(area, age, sex_male, hispanic,
                         TABLE7_LOG_AIAN[col], TABLE7_SQ_BLACK[col])
        lp = _linear_predictor(TABLE7, col, design)
        p = 1.0 / (1.0 + math.exp(-lp))
        return {modelled: p, other: 1.0 - p}

    if group == SEPARATE_THREE:
        eta = {}
        for col, name in ((5, "AIAN"), (6, "BLACK")):
            design = _design(area, age, sex_male, hispanic,
                             TABLE7_LOG_AIAN[col], TABLE7_SQ_BLACK[col])
            eta[name] = _linear_predictor(TABLE7, col, design)
        e = {k: math.exp(v) for k, v in eta.items()}
        denom = 1.0 + e["AIAN"] + e["BLACK"]
        return {"AIAN": e["AIAN"] / denom, "BLACK": e["BLACK"] / denom,
                "WHITE": 1.0 / denom}

    if group in COMPOSITE:
        applicable = COMPOSITE[group]
        # Table 8 always uses the logarithm of percent AIAN and the untransformed
        # percent Black.
        design = _design(area, age, sex_male, hispanic, True, False)
        indicators = {
            "indicator_not_aian": 0.0 if "AIAN" in applicable else 1.0,
            "indicator_not_api": 0.0 if "API" in applicable else 1.0,
            "indicator_not_black": 0.0 if "BLACK" in applicable else 1.0,
        }
        eta = {}
        for col, name in ((0, "AIAN"), (1, "API"), (2, "BLACK")):
            eta[name] = _linear_predictor(TABLE8, col, design, extra=indicators)
        e = {k: math.exp(v) for k, v in eta.items()}
        denom = 1.0 + sum(e.values())
        full = {k: v / denom for k, v in e.items()}
        full["WHITE"] = 1.0 / denom
        # Rescale over the categories that apply to THIS group, after excluding
        # the inapplicable ones.
        kept = {c: full[c] for c in applicable}
        total = sum(kept.values())
        return {c: v / total for c, v in kept.items()}

    raise KeyError("unknown response group %r" % (group,))
