"""Build the bridged-race-population-estimates instance.

Deterministic. SEED names the selection walk even though no RNG is drawn: the
graded set is chosen by an ordered, reproducible sweep over the published cell
universe, and SEED fixes the rotation offset of that sweep.

What this script does, in order:

1.  Re-reads the coefficient slice cut from the published PDF
    (`source/sr02_135_table7.csv`, `source/sr02_135_table8.csv`) and asserts the
    oracle's own transcription equals it cell by cell.
2.  Selects the graded records from the REAL cell universe of the Census 2000
    Modified Race Data Summary File - only (area, age, sex, Hispanic origin,
    response group) combinations with a non-zero enumerated population are
    eligible, so no graded case is a cell that does not exist.
3.  Applies the DISCRIMINATION ASSERTION to every candidate: the correct share
    must differ by MORE THAN the graded tolerance from all three routes that are
    available without the withheld coefficient set - the equal split, the split
    proportional to the area's single-category counts, and the flat national
    shares shipped in question.json.  A candidate that fails any of the three is
    DROPPED, not recorded as non-discriminating.  This is the rule that
    `.omo/S-LAYER-GATE-2026-07-28.md` sections 14-15 produce: a graded case the
    withheld object does not decide inflates the unaided floor.
4.  Measures every control route in tolerance units and the constant-answer
    floor of the final graded set.
5.  Writes `environment/data/`, `verifier/expected_values.json`,
    `verifier/anchor_table9.csv`, `verifier/cell_universe.npz` and
    `build/build_report.json`.

Run from anywhere:  python3 build/gen.py
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "build", "source")
sys.path.insert(0, os.path.join(ROOT, "solution"))
import bridging_models as bm  # noqa: E402

SEED = 20260731
SEED_BASE = 20260729

N_GRADED = 31                    # prime (PROMPT-AUTHOR-TO-30.md 6.7)
TOLERANCE_ABS = 0.002            # absolute, on a share in [0, 1]
N_AREAS = 17                     # prime; keeps the shipped profile table small
# Every graded case must sit at least this far from EVERY route reachable
# without the withheld coefficient set.  2x the graded tolerance is the floor
# PROMPT-AUTHOR-TO-30.md 6.6 asks for on the nearest real competitor; here it is
# enforced per case and on all three routes, not just on the nearest one.
DISCRIMINATION_FLOOR = 2.0 * TOLERANCE_ABS
# No two graded goldens may sit closer than this, so a single constant answer can
# never clear more than one graded case.
GOLDEN_SEPARATION = 4.0 * TOLERANCE_ABS

APPLICABLE = {
    "AIAN_API": ("AIAN", "API"),
    "AIAN_BLACK": ("AIAN", "BLACK"),
    "AIAN_WHITE": ("AIAN", "WHITE"),
    "API_BLACK": ("API", "BLACK"),
    "API_WHITE": ("API", "WHITE"),
    "BLACK_WHITE": ("BLACK", "WHITE"),
    "AIAN_API_BLACK": ("AIAN", "API", "BLACK"),
    "AIAN_API_WHITE": ("AIAN", "API", "WHITE"),
    "AIAN_BLACK_WHITE": ("AIAN", "BLACK", "WHITE"),
    "API_BLACK_WHITE": ("API", "BLACK", "WHITE"),
    "AIAN_API_BLACK_WHITE": ("AIAN", "API", "BLACK", "WHITE"),
}
GROUP_LABEL = {g: "+".join(g.split("_")) for g in APPLICABLE}
PCT_COL = {"AIAN": "pct_aian_alone", "API": "pct_api_alone",
           "BLACK": "pct_black_alone", "WHITE": "pct_white_alone"}
# mr-co.txt block order: Hispanic male, Hispanic female, non-Hispanic male,
# non-Hispanic female
BLOCKS = ((True, True), (True, False), (False, True), (False, False))
# Census 2000 Modified Race age groups: 1 = under 1, 2 = 1-4, 3 = 5-9 ... 19 = 85+
AGE_BAND = {1: [0], 2: [1, 2, 3, 4], 19: [85]}
for _k in range(3, 19):
    AGE_BAND[_k] = list(range(5 * (_k - 2), 5 * (_k - 2) + 5))


# --------------------------------------------------------------------------- #
# sources
# --------------------------------------------------------------------------- #

def read_table7():
    out = {}
    with open(os.path.join(SOURCE, "sr02_135_table7.csv")) as fh:
        for row in csv.DictReader(fh):
            key = row.pop("covariate")
            out[key] = tuple(None if v == "" else float(v) for v in row.values())
    return out


def read_table8():
    out = {}
    with open(os.path.join(SOURCE, "sr02_135_table8.csv")) as fh:
        for row in csv.DictReader(fh):
            key = row.pop("covariate")
            out[key] = tuple(float(v) for v in row.values())
    return out


def read_areas():
    with open(os.path.join(SOURCE, "nchs_area_covariates_census2000.csv")) as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k in ("pct_aian_alone", "pct_api_alone", "pct_black_alone",
                  "pct_white_alone", "pct_multiple_response"):
            r[k] = float(r[k])
        r["census2000_population"] = int(r["census2000_population"])
    return rows


def read_table9():
    with open(os.path.join(SOURCE, "sr02_135_table9.csv")) as fh:
        return list(csv.DictReader(fh))


def assert_oracle_matches_the_published_slice(t7, t8):
    """The oracle's transcription must equal the slice cut from the PDF."""
    assert set(t7) == set(bm.TABLE7), "Table 7 covariate rows disagree"
    for name, row in t7.items():
        got = bm.TABLE7[name]
        assert len(row) == len(got) == 7, "Table 7 has seven fitted columns"
        for i, (a, b) in enumerate(zip(row, got)):
            assert (a is None) == (b is None), \
                "Table 7 %s column %d: one side says the variable is not in the model" % (name, i)
            if a is not None:
                assert abs(a - b) < 1e-12, \
                    "Table 7 %s column %d: slice %r vs oracle %r" % (name, i, a, b)
    assert set(t8) == set(bm.TABLE8), "Table 8 covariate rows disagree"
    for name, row in t8.items():
        for i, (a, b) in enumerate(zip(row, bm.TABLE8[name])):
            assert abs(a - b) < 1e-12, \
                "Table 8 %s column %d: slice %r vs oracle %r" % (name, i, a, b)


# --------------------------------------------------------------------------- #
# the routes available WITHOUT the withheld coefficient set
# --------------------------------------------------------------------------- #

def route_equal_split(group, area, target):
    return 1.0 / len(APPLICABLE[group])


def route_proportional_to_alone(group, area, target):
    weights = {c: area[PCT_COL[c]] for c in APPLICABLE[group]}
    total = sum(weights.values())
    if total <= 0:
        return 1.0 / len(APPLICABLE[group])
    return weights[target] / total


def flat_shares(table9):
    out = {}
    for row in table9:
        out.setdefault(row["response_group"], {})[row["target_category"]] = \
            float(row["mean"])
    # the published means are rounded to three decimals and need not sum to 1;
    # the orientation block is shipped exactly as published
    return out


# --------------------------------------------------------------------------- #
# candidate sweep
# --------------------------------------------------------------------------- #

def build():
    t7, t8 = read_table7(), read_table8()
    assert_oracle_matches_the_published_slice(t7, t8)
    table9 = read_table9()
    flat = flat_shares(table9)
    FLAT_SHARES.clear()
    FLAT_SHARES.update(flat)

    areas = read_areas()
    by_fips = {a["fips"]: a for a in areas}
    universe = np.load(os.path.join(SOURCE, "census2000_group_cells.npz"))
    cells = universe["cells"]                       # (n_area, 19, 4, 11)
    ufips = [str(f) for f in universe["fips"]]
    ugroups = [str(g) for g in universe["groups"]]

    # An area is eligible only when every model covariate is a genuinely
    # published percentage.  NCHS floors percent AIAN at 0.0001 for areas that
    # enumerated no single-race AIAN residents; those areas are excluded rather
    # than shipped with a convention the prompt would have to state.
    eligible = [i for i, f in enumerate(ufips)
                if by_fips[f]["pct_aian_alone"] > 0.0001
                and by_fips[f]["pct_black_alone"] > 0.0
                and by_fips[f]["pct_api_alone"] > 0.0
                and by_fips[f]["pct_multiple_response"] > 0.0]

    # Spread the shipped areas over region x urbanisation, largest first inside
    # each stratum so the cells are well populated.  Deterministic.
    strata = {}
    for i in eligible:
        a = by_fips[ufips[i]]
        strata.setdefault((a["region"], a["urbanisation"]), []).append(i)
    for key in strata:
        strata[key].sort(key=lambda i: (-by_fips[ufips[i]]["census2000_population"],
                                        ufips[i]))
    ordered_strata = sorted(strata)
    rotate = SEED % len(ordered_strata)
    ordered_strata = ordered_strata[rotate:] + ordered_strata[:rotate]
    chosen, depth = [], 0
    while len(chosen) < N_AREAS:
        progressed = False
        for key in ordered_strata:
            if depth < len(strata[key]) and len(chosen) < N_AREAS:
                chosen.append(strata[key][depth])
                progressed = True
        if not progressed:
            break
        depth += 1
    chosen = chosen[:N_AREAS]
    area_id = {i: "AREA-%02d" % (n + 1) for n, i in enumerate(sorted(chosen))}

    # ---- candidate records -------------------------------------------------
    candidates = []
    for i in sorted(chosen):
        area = by_fips[ufips[i]]
        for gi, group in enumerate(ugroups):
            for band in sorted(AGE_BAND):
                for bi, (hispanic, male) in enumerate(BLOCKS):
                    if cells[i, band - 1, bi, gi] <= 0:
                        continue
                    for age in AGE_BAND[band]:
                        for target in APPLICABLE[group]:
                            candidates.append(
                                dict(area_index=i, group=group, age=age,
                                     male=male, hispanic=hispanic,
                                     target=target,
                                     population=int(cells[i, band - 1, bi, gi])))

    # ---- discrimination assertion, per candidate ---------------------------
    surviving, dropped = [], {"equal_split": 0, "proportional_to_alone": 0,
                              "flat_national_shares": 0, "round_figure": 0}
    for cand in candidates:
        area = by_fips[ufips[cand["area_index"]]]
        shares = bm.proportions(cand["group"], area, cand["age"],
                                cand["male"], cand["hispanic"])
        ref = shares[cand["target"]]
        gaps = {
            "equal_split": abs(ref - route_equal_split(cand["group"], area, cand["target"])),
            "proportional_to_alone": abs(ref - route_proportional_to_alone(
                cand["group"], area, cand["target"])),
            "flat_national_shares": abs(ref - flat[cand["group"]][cand["target"]]),
        }
        failed = [k for k, v in gaps.items() if v <= DISCRIMINATION_FLOOR]
        if failed:
            for k in failed:
                dropped[k] += 1
            continue
        # a golden sitting on a round figure is a free pass for a flat guess
        if min(abs(ref - g) for g in ROUND_FIGURES) <= 2.0 * TOLERANCE_ABS:
            dropped["round_figure"] += 1
            continue
        cand["ref"] = ref
        cand["gaps"] = gaps
        surviving.append(cand)

    graded = select_graded(surviving, ufips, by_fips, area_id)
    return dict(t7=t7, t8=t8, table9=table9, flat=flat, areas=areas,
                by_fips=by_fips, universe=universe, cells=cells, ufips=ufips,
                ugroups=ugroups, chosen=chosen, area_id=area_id,
                candidates=candidates, surviving=surviving, dropped=dropped,
                graded=graded)


ROUND_FIGURES = [0.0, 0.05, 0.1, 0.125, 0.15, 0.2, 0.25, 0.3, 1.0 / 3.0, 0.35,
                 0.4, 0.45, 0.5, 0.55, 0.6, 2.0 / 3.0, 0.65, 0.7, 0.75, 0.8,
                 0.85, 0.9, 0.95, 1.0]


GROUP_ORDER = ["AIAN_API", "AIAN_BLACK", "AIAN_WHITE", "API_BLACK", "API_WHITE",
               "BLACK_WHITE", "AIAN_API_BLACK", "AIAN_API_WHITE",
               "AIAN_BLACK_WHITE", "API_BLACK_WHITE", "AIAN_API_BLACK_WHITE"]
# One graded case per (response group, target category) pair.  There are exactly
# 28 such pairs, and 28 is the number of NHIS bridging proportions the published
# method produces per cell - "a set of 28 probabilities, one for selecting each
# possible primary race in each of the 11 multiple-race groups".  The graded set
# is those 28 plus three EXTRAS that exercise properties no single pair covers.
PAIRS = [(g, t) for g in GROUP_ORDER for t in APPLICABLE[g]]
AGE_TARGETS = [2, 8, 14, 21, 27, 33, 39, 46, 52, 58, 64, 72, 79]
EXTRA_REQUIREMENTS = [
    ("age_cap_applies", lambda c: c["age"] >= 70),
    ("hispanic_origin", lambda c: c["hispanic"]),
    ("composite_rescale_over_four", lambda c: c["group"] == "AIAN_API_BLACK_WHITE"),
]


def select_graded(surviving, ufips, by_fips, area_id):
    """Deterministic, coverage-first selection of the graded set.

    Every one of the 28 (response group, target category) pairs appears exactly
    once, and three extras cover the age cap, Hispanic origin and the four-way
    composite rescale.  Areas rotate across the pairs so no single area carries
    the set, and the age preference walks a fixed ladder so the graded ages span
    the whole published range including the capped tail.
    """
    by_pair = {}
    for cand in surviving:
        by_pair.setdefault((cand["group"], cand["target"]), []).append(cand)
    areas_in_order = sorted({c["area_index"] for c in surviving},
                            key=lambda i: area_id[i])

    chosen, used_triples, refs = [], set(), []

    def far_enough(cand):
        return all(abs(cand["ref"] - r) > GOLDEN_SEPARATION for r in refs)

    for n, pair in enumerate(PAIRS):
        pool = [c for c in by_pair.get(pair, []) if far_enough(c)]
        assert pool, "no separated candidate for pair %s" % (pair,)
        want_area = areas_in_order[(n + SEED) % len(areas_in_order)]
        want_age = AGE_TARGETS[(n + SEED) % len(AGE_TARGETS)]
        want_hisp = ((n + SEED) % 5 == 0)
        best = min(pool, key=lambda c: (
            0 if c["area_index"] == want_area else 1,
            0 if bool(c["hispanic"]) == want_hisp else 1,
            0 if c["population"] >= 10 else 1,
            abs(c["age"] - want_age),
            -c["population"],
            area_id[c["area_index"]], c["age"], c["hispanic"], c["male"]))
        used_triples.add((best["area_index"], best["group"], best["target"]))
        refs.append(best["ref"])
        chosen.append(best)

    for name, predicate in EXTRA_REQUIREMENTS:
        pool = [c for c in surviving
                if predicate(c) and far_enough(c)
                and (c["area_index"], c["group"], c["target"]) not in used_triples]
        assert pool, "no separated candidate satisfies the extra %r" % name
        best = min(pool, key=lambda c: (
            -c["population"], area_id[c["area_index"]], c["group"], c["target"],
            c["age"], c["hispanic"], c["male"]))
        best = dict(best, extra=name)
        used_triples.add((best["area_index"], best["group"], best["target"]))
        refs.append(best["ref"])
        chosen.append(best)

    assert len(chosen) == N_GRADED, \
        "selected %d graded records, need %d" % (len(chosen), N_GRADED)
    out = []
    for n, cand in enumerate(sorted(chosen, key=lambda c: (
            GROUP_ORDER.index(c["group"]),
            APPLICABLE[c["group"]].index(c["target"]),
            area_id[c["area_index"]], c["age"]))):
        cand = dict(cand)
        cand["record_id"] = "R-%02d" % (n + 1)
        out.append(cand)
    return out


# --------------------------------------------------------------------------- #
# control routes - every one is a method a competent practitioner could take
# --------------------------------------------------------------------------- #

def _route_shares(name, group, area, age, male, hispanic):
    """The full share vector this competing route produces for one record."""
    apply_to = APPLICABLE[group]
    if name == "equal_split":
        return {c: 1.0 / len(apply_to) for c in apply_to}
    if name == "proportional_to_area_single_category_counts":
        w = {c: area[PCT_COL[c]] for c in apply_to}
        tot = sum(w.values())
        return {c: (v / tot if tot > 0 else 1.0 / len(apply_to)) for c, v in w.items()}
    if name == "flat_national_shares":
        return dict(FLAT_SHARES[group])
    if name == "composite_model_for_every_group":
        return _composite_only(group, area, age, male, hispanic, rescale=True)
    if name == "composite_shares_not_rescaled":
        if group in COMPOSITE_GROUPS:
            return _composite_only(group, area, age, male, hispanic, rescale=False)
        return bm.proportions(group, area, age, male, hispanic)
    if name == "age_not_capped_at_69":
        return _with_age_override(group, area, age, male, hispanic)
    if name == "log_transform_of_percent_aian_omitted":
        return _with_transform_override(group, area, age, male, hispanic,
                                        log_aian=False, sq_black=None)
    if name == "square_of_percent_black_omitted":
        return _with_transform_override(group, area, age, male, hispanic,
                                        log_aian=None, sq_black=False)
    if name == "area_covariates_omitted":
        flat_area = dict(area, pct_aian_alone=1.0, pct_api_alone=0.0,
                         pct_black_alone=0.0, pct_multiple_response=0.0)
        return bm.proportions(group, flat_area, age, male, hispanic)
    if name == "contextual_covariates_omitted":
        flat_area = dict(area, region="west", urbanisation="large_central",
                         pct_aian_alone=1.0, pct_api_alone=0.0,
                         pct_black_alone=0.0, pct_multiple_response=0.0)
        return bm.proportions(group, flat_area, age, male, hispanic)
    if name == "composite_indicator_variables_omitted":
        if group in COMPOSITE_GROUPS:
            return _composite_only(group, area, age, male, hispanic, rescale=True,
                                   indicators=False)
        return bm.proportions(group, area, age, male, hispanic)
    if name == "hispanic_origin_coded_inverted":
        return bm.proportions(group, area, age, male, not hispanic)
    if name == "sex_coded_inverted":
        return bm.proportions(group, area, age, not male, hispanic)
    raise KeyError(name)


COMPOSITE_GROUPS = set(bm.COMPOSITE)
FLAT_SHARES = {}          # filled by build(); the published country-wide means


def _composite_only(group, area, age, male, hispanic, rescale, indicators=True):
    """Table 8 evaluated for any group, with the rescale and the group indicators
    switchable, so the two composite-model mistakes can be measured separately."""
    apply_to = APPLICABLE[group]
    design = bm._design(area, age, male, hispanic, True, False)
    ind = {"indicator_not_aian": 0.0 if "AIAN" in apply_to else 1.0,
           "indicator_not_api": 0.0 if "API" in apply_to else 1.0,
           "indicator_not_black": 0.0 if "BLACK" in apply_to else 1.0}
    if not indicators:
        ind = {k: 0.0 for k in ind}
    eta = {}
    for col, name in ((0, "AIAN"), (1, "API"), (2, "BLACK")):
        eta[name] = bm._linear_predictor(bm.TABLE8, col, design, extra=ind)
    e = {k: math.exp(v) for k, v in eta.items()}
    den = 1.0 + sum(e.values())
    full = {k: v / den for k, v in e.items()}
    full["WHITE"] = 1.0 / den
    kept = {c: full[c] for c in apply_to}
    if not rescale:
        return kept
    tot = sum(kept.values())
    return {c: v / tot for c, v in kept.items()}


def _with_age_override(group, area, age, male, hispanic):
    saved = bm.AGE_CAP
    try:
        bm.AGE_CAP = 200
        return bm.proportions(group, area, age, male, hispanic)
    finally:
        bm.AGE_CAP = saved


def _with_transform_override(group, area, age, male, hispanic, log_aian, sq_black):
    saved_log, saved_sq = bm.TABLE7_LOG_AIAN, bm.TABLE7_SQ_BLACK
    try:
        if log_aian is not None:
            bm.TABLE7_LOG_AIAN = tuple(log_aian for _ in saved_log)
        if sq_black is not None:
            bm.TABLE7_SQ_BLACK = tuple(sq_black for _ in saved_sq)
        if log_aian is False and group in COMPOSITE_GROUPS:
            return _composite_no_log(group, area, age, male, hispanic)
        return bm.proportions(group, area, age, male, hispanic)
    finally:
        bm.TABLE7_LOG_AIAN, bm.TABLE7_SQ_BLACK = saved_log, saved_sq


def _composite_no_log(group, area, age, male, hispanic):
    apply_to = APPLICABLE[group]
    design = bm._design(area, age, male, hispanic, False, False)
    ind = {"indicator_not_aian": 0.0 if "AIAN" in apply_to else 1.0,
           "indicator_not_api": 0.0 if "API" in apply_to else 1.0,
           "indicator_not_black": 0.0 if "BLACK" in apply_to else 1.0}
    e = {}
    for col, name in ((0, "AIAN"), (1, "API"), (2, "BLACK")):
        e[name] = math.exp(bm._linear_predictor(bm.TABLE8, col, design, extra=ind))
    den = 1.0 + sum(e.values())
    full = {k: v / den for k, v in e.items()}
    full["WHITE"] = 1.0 / den
    kept = {c: full[c] for c in apply_to}
    tot = sum(kept.values())
    return {c: v / tot for c, v in kept.items()}


CONTROL_NOTES = {
    "equal_split": (
        "A real competing method and the first of the two routes the "
        "discrimination assertion is run against: split each response equally "
        "over the categories it names. It is what a run without the withheld "
        "coefficient set can produce from the shipped file alone."),
    "proportional_to_area_single_category_counts": (
        "A real competing method and the second route the discrimination "
        "assertion is run against: allocate in proportion to the area's own "
        "single-category percentages, which the shipped area profile carries. It "
        "is the most defensible thing to do without the models and is the route "
        "an analyst reaches for when the area composition is the only signal "
        "available."),
    "flat_national_shares": (
        "THE NEAREST REAL COMPETITOR, and it is published: the mean assignment "
        "share for each response group over the whole country. question.json "
        "ships it, labelled as orientation only. It gets the response group right "
        "and drops every person-level and area-level covariate, which is exactly "
        "the dimension the withheld models supply."),
    "composite_model_for_every_group": (
        "A real competing method: use the composite model for all eleven response "
        "groups instead of only for the five it was fitted for. It is the "
        "simplification a reader makes on finding one table that covers "
        "everything."),
    "composite_shares_not_rescaled": (
        "A real competing method: for the composite groups, report the modelled "
        "share without rescaling over the categories that actually apply. The "
        "rescale step is a separate sentence in the published method and is easy "
        "to miss; the route is identical to the correct one on the six groups "
        "with their own models, which is why it is recorded rather than dropped."),
    "age_not_capped_at_69": (
        "A real competing method: use the record's own age above 69 rather than "
        "the capped value. It affects only the graded cases at 70 and over and is "
        "recorded with that scope."),
    "log_transform_of_percent_aian_omitted": (
        "A real competing method: read the area percentages straight off the "
        "profile without the logarithm the published footnote specifies for two "
        "of the separate models and for the composite model."),
    "square_of_percent_black_omitted": (
        "A real competing method: omit the square the published footnote "
        "specifies for two of the separate models. It moves only the models that "
        "use it, which is why the recorded gap is scoped to the cases it alters."),
    "area_covariates_omitted": (
        "A real competing method: keep the models but drop the four area "
        "composition covariates, which is what a run does when it cannot decide "
        "how the percentages are scaled."),
    "contextual_covariates_omitted": (
        "A real competing method: keep only the person-level covariates and drop "
        "region, urbanisation and the area composition together. It is the "
        "strongest form of the 'covariates are a detail' error."),
    "composite_indicator_variables_omitted": (
        "A real competing method: evaluate the composite model without the three "
        "group indicators, which is what happens when the constrained-to-zero "
        "convention in the published table is read as 'not in the model'."),
    "hispanic_origin_coded_inverted": (
        "A coding error rather than a method: the Hispanic origin indicator "
        "reversed. Recorded because the shipped file spells origin as a word and "
        "the published model codes it as an indicator."),
    "sex_coded_inverted": (
        "A coding error rather than a method: the sex indicator reversed, which "
        "is the other place a word-to-indicator mapping can flip."),
    "best_case_tuned_single_constant": (
        "Not a competing method - an adversarial lower bound on luck, measured "
        "rather than assumed. The single constant answer that clears the most "
        "graded cases, swept at 5e-06 resolution over [0, 1]. The graded set is "
        "built so that no two goldens sit within twice the tolerance band of each "
        "other, so this is bounded at one case by construction."),
}
DROP_CRITERIA = ("equal_split", "proportional_to_area_single_category_counts",
                 "flat_national_shares")
NEAREST_REAL_COMPETITOR = "flat_national_shares"


# --------------------------------------------------------------------------- #
# outputs
# --------------------------------------------------------------------------- #

DATA = os.path.join(ROOT, "environment", "data")
VERIFIER = os.path.join(ROOT, "tests")
CATEGORY_DESCRIPTION = {
    "AIAN": "American Indian or Alaska Native",
    "API": "Asian or Pacific Islander",
    "BLACK": "Black or African American",
    "WHITE": "White",
}


def case_id(record):
    return "share-%s" % record["record_id"]


def write_agent_data(r):
    os.makedirs(DATA, exist_ok=True)
    rows = []
    for i in sorted(r["chosen"]):
        a = r["by_fips"][r["ufips"][i]]
        rows.append(dict(area_id=r["area_id"][i], region=a["region"],
                         urbanisation=a["urbanisation"],
                         pct_aian_alone=a["pct_aian_alone"],
                         pct_api_alone=a["pct_api_alone"],
                         pct_black_alone=a["pct_black_alone"],
                         pct_white_alone=a["pct_white_alone"],
                         pct_multiple_response=a["pct_multiple_response"]))
    with open(os.path.join(DATA, "area_profile.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    recs = []
    for c in r["graded"]:
        recs.append(dict(record_id=c["record_id"],
                         area_id=r["area_id"][c["area_index"]],
                         age_years=c["age"],
                         sex="male" if c["male"] else "female",
                         hispanic_origin="hispanic" if c["hispanic"] else "not_hispanic",
                         response_group=GROUP_LABEL[c["group"]],
                         target_category=c["target"]))
    with open(os.path.join(DATA, "response_records.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(recs[0]))
        w.writeheader()
        w.writerows(recs)

    orientation = {}
    for group, shares in r["flat"].items():
        orientation[GROUP_LABEL[group]] = dict(shares)
    question = {
        "records_to_report": [c["record_id"] for c in r["graded"]],
        "categories": CATEGORY_DESCRIPTION,
        "output": {
            "path": "/root/results.json",
            "top_level_key": "assignment_share",
            "keyed_by": "record_id",
            "value": "the share of that record's response group assigned to the "
                     "record's target_category, a number between 0 and 1",
            "precision": "report at least six decimal places",
        },
        "orientation_flat_shares": orientation,
        "orientation_note": (
            "The flat shares above are the published country-wide averages for "
            "each response group. They ignore every characteristic of the person "
            "and of the area and are supplied for orientation only; they are NOT "
            "the answer to any record."),
    }
    with open(os.path.join(DATA, "question.json"), "w") as fh:
        json.dump(question, fh, indent=2, sort_keys=True)
        fh.write("\n")


def write_cell_universe(r):
    os.makedirs(VERIFIER, exist_ok=True)
    import shutil
    shutil.copyfile(os.path.join(SOURCE, "sr02_135_table9.csv"),
                    os.path.join(VERIFIER, "anchor_table9.csv"))
    regions = ("northeast", "midwest", "south", "west")
    urbans = ("large_central", "large_fringe", "medium_small_metro", "nonmetro")
    fips = r["ufips"]
    areas = [r["by_fips"][f] for f in fips]
    np.savez_compressed(
        os.path.join(VERIFIER, "cell_universe.npz"),
        groups=np.array(r["ugroups"]),
        region=np.array([regions.index(a["region"]) for a in areas], dtype=np.int8),
        urbanisation=np.array([urbans.index(a["urbanisation"]) for a in areas],
                              dtype=np.int8),
        pct_aian_alone=np.array([a["pct_aian_alone"] for a in areas]),
        pct_api_alone=np.array([a["pct_api_alone"] for a in areas]),
        pct_black_alone=np.array([a["pct_black_alone"] for a in areas]),
        pct_multiple_response=np.array([a["pct_multiple_response"] for a in areas]),
        present=(r["cells"] > 0))


def measure_controls(r):
    """Every control route, in tolerance units, over the graded set."""
    graded = r["graded"]
    ledger = {}
    names = list(CONTROL_NOTES)
    names.remove("best_case_tuned_single_constant")
    for name in names:
        altered, inside, gaps, per_case = [], [], [], {}
        for c in graded:
            area = r["by_fips"][r["ufips"][c["area_index"]]]
            got = _route_shares(name, c["group"], area, c["age"], c["male"],
                                c["hispanic"])[c["target"]]
            multiple = abs(got - c["ref"]) / TOLERANCE_ABS
            per_case[case_id(c)] = round(multiple, 4)
            if multiple > 1e-9:
                altered.append(case_id(c))
                gaps.append(multiple)
            if multiple <= 1.0:
                inside.append(case_id(c))
        entry = {
            "note": CONTROL_NOTES[name],
            "description": CONTROL_NOTES[name].split(":")[0].strip() + ".",
            "n_cases_altered": len(altered),
            "cases_altered": altered,
            "n_cases_inside_tolerance": len(inside),
            "cases_inside_tolerance": inside,
            "min_gap_multiple": round(min(gaps), 4) if gaps else 0.0,
            "max_gap_multiple": round(max(gaps), 4) if gaps else 0.0,
            "min_gap_multiple_scored_over": ("cases this route alters" if altered
                                             else "not applicable - alters nothing"),
            "per_case_gap_multiple": per_case,
        }
        if name in DROP_CRITERIA:
            entry["discrimination_assertion"] = (
                "ENFORCED per graded case at build time: every graded case sits "
                "more than %.1fx the graded tolerance from this route, and any "
                "candidate that did not was DROPPED rather than recorded as "
                "non-discriminating." % (DISCRIMINATION_FLOOR / TOLERANCE_ABS))
        if name == NEAREST_REAL_COMPETITOR:
            entry["nearest_real_competitor"] = True
        if inside:
            entry["non_discriminating_on"] = inside
            entry["non_discriminating_note"] = (
                "MEASURED: this route lands inside tolerance on %d of %d graded "
                "case(s) (%s), of which %d are cases the route actually alters. "
                "Recorded rather than hidden. Every case it clears it clears by "
                "agreeing with the withheld models on that case, so it is not a "
                "route an unaided run can take: it is a mis-step INSIDE the "
                "published method and needs the coefficient set in hand."
                % (len(inside), len(graded), ", ".join(inside),
                   len(set(inside) & set(altered))))
        ledger[name] = entry

    # adversarial floor: the best single constant answer
    refs = np.array([c["ref"] for c in graded])
    grid = np.linspace(0.0, 1.0, 200001)
    hits = np.array([int(np.sum(np.abs(refs - v) <= TOLERANCE_ABS)) for v in grid])
    best = int(hits.max())
    best_at = float(grid[int(hits.argmax())])
    ledger["best_case_tuned_single_constant"] = {
        "note": CONTROL_NOTES["best_case_tuned_single_constant"],
        "description": "one constant answer for every graded record, tuned by "
                       "exhaustive sweep to clear as many graded cases as possible.",
        "n_cases_altered": len(graded),
        "cases_altered": [case_id(c) for c in graded],
        "n_cases_inside_tolerance": best,
        "cases_inside_tolerance": [case_id(c) for c in graded
                                   if abs(c["ref"] - best_at) <= TOLERANCE_ABS],
        "min_gap_multiple": 0.0,
        "max_gap_multiple": 0.0,
        "min_gap_multiple_scored_over": "not applicable - a tuned sweep, not a route",
        "measured": {"best_constant": round(best_at, 6),
                     "cases_cleared": best,
                     "constant_answer_floor": round(best / len(graded), 4)},
        "non_discriminating_note": (
            "See note: bounded at one graded case by construction, because the "
            "graded set is built with a minimum pairwise separation of %.1fx the "
            "tolerance between goldens."
            % (GOLDEN_SEPARATION / TOLERANCE_ABS)),
    }
    return ledger, best / len(graded), best_at


def measure_table9_anchor():
    """Reproduce the publisher's own Table 9 through the SECOND FORMULATION."""
    sys.path.insert(0, VERIFIER)
    import independent_bridging as ind
    stats = ind.table9_statistics()
    published = ind.anchor()
    rows, worst = [], 0.0
    for key, pub in sorted(published.items()):
        got = stats[key]
        for stat in ("mean", "median", "q1", "q3", "min", "max"):
            d = abs(got[stat] - pub[stat])
            worst = max(worst, d)
            rows.append({"response_group": key[0], "target_category": key[1],
                         "statistic": stat, "published": pub[stat],
                         "recomputed": round(got[stat], 4),
                         "absolute_difference": round(d, 4)})
    return stats, rows, worst


def measure_end_to_end_2010(r):
    """Does the published coefficient set reproduce the publisher's OWN 2010
    bridged-race file, county by county?  Measured, not assumed."""
    sys.path.insert(0, VERIFIER)
    import independent_bridging as ind
    z = np.load(os.path.join(SOURCE, "bridged2010_county_check.npz"))
    fips = [str(f) for f in z["fips"]]
    groups = [str(g) for g in z["groups"]]
    cells, alone, bridged = z["cells"], z["alone"], z["bridged"]
    by_fips = r["by_fips"]
    regions = ("northeast", "midwest", "south", "west")
    urbans = ("large_central", "large_fringe", "medium_small_metro", "nonmetro")
    region = np.array([regions.index(by_fips[f]["region"]) for f in fips])
    urban = np.array([urbans.index(by_fips[f]["urbanisation"]) for f in fips])
    pa = np.array([by_fips[f]["pct_aian_alone"] for f in fips])
    pi = np.array([by_fips[f]["pct_api_alone"] for f in fips])
    pb = np.array([by_fips[f]["pct_black_alone"] for f in fips])
    pm = np.array([by_fips[f]["pct_multiple_response"] for f in fips])
    order = ["WHITE", "BLACK", "AIAN", "API"]
    predicted = {c: np.zeros(len(fips)) for c in order}
    # 2010 Modified Race age groups: 1 = 0-4 ... 18 = 85+
    band_years = {k: list(range(5 * k, 5 * k + 5)) for k in range(17)}
    band_years[17] = [85]
    hisp_of_block = (1.0, 1.0, 0.0, 0.0)
    male_of_block = (1.0, 0.0, 1.0, 0.0)
    for gi, group in enumerate(groups):
        for band in range(18):
            for block in range(4):
                pop = cells[:, band, block, gi].astype(float)
                sel = np.nonzero(pop)[0]
                if not len(sel):
                    continue
                cov = (region[sel], urban[sel], pa[sel], pi[sel], pb[sel], pm[sel])
                acc = None
                years = band_years[band]
                for year in years:
                    got = ind.shares_vectorised(
                        group, cov, np.full(len(sel), float(year)),
                        np.full(len(sel), hisp_of_block[block]),
                        np.full(len(sel), male_of_block[block]))
                    acc = got if acc is None else {k: acc[k] + got[k] for k in got}
                for category, value in acc.items():
                    predicted[category][sel] += (value / len(years)) * pop[sel]
    # the publisher's own allocated multiple-response population
    published = {c: (bridged[:, i] - alone[:, i]).astype(float)
                 for i, c in enumerate(order)}
    out = {}
    for c in order:
        pub, pred = published[c].sum(), predicted[c].sum()
        out[c] = {"publisher": int(pub), "predicted": round(float(pred), 1),
                  "relative_difference_pct": round(100.0 * (pred - pub) / pub, 4)}
    # the same comparison for the two routes the discrimination assertion uses
    for route in ("equal_split", "proportional_to_area_single_category_counts"):
        naive = {c: np.zeros(len(fips)) for c in order}
        for gi, group in enumerate(groups):
            apply_to = APPLICABLE[group]
            pop = cells[:, :, :, gi].sum(axis=(1, 2)).astype(float)
            for category in apply_to:
                if route == "equal_split":
                    w = np.full(len(fips), 1.0 / len(apply_to))
                else:
                    cols = {"AIAN": pa, "API": pi, "BLACK": pb,
                            "WHITE": 100.0 - pa - pi - pb - pm}
                    tot = sum(cols[k] for k in apply_to)
                    w = np.where(tot > 0, cols[category] / np.where(tot > 0, tot, 1.0),
                                 1.0 / len(apply_to))
                naive[category] += w * pop
        out[route] = {c: {"predicted": round(float(naive[c].sum()), 1),
                          "relative_difference_pct": round(
                              100.0 * (naive[c].sum() - published[c].sum())
                              / published[c].sum(), 4)} for c in order}
    out["identity"] = {
        "publisher_allocated_total": int(sum(published[c].sum() for c in order)),
        "multiple_response_population_on_the_input_file": int(cells.sum()),
        "exact": int(sum(published[c].sum() for c in order)) == int(cells.sum()),
        "note": "The publisher's own released bridged file minus the publisher's "
                "own single-category counts equals the multiple-response "
                "population on the input file, exactly, over %d counties. That "
                "identity is what makes the 2010 file a check on the method "
                "rather than a restatement of it." % len(fips),
    }
    return out


SOURCES = [
    {"role": "withheld coefficient set (Tables 7 and 8) and the Table 9 anchor",
     "citation": "Ingram DD, Parker JD, Schenker N, Weed JA, Hamilton B, Arias E, "
                 "Madans JH. United States Census 2000 population with bridged "
                 "race categories. National Center for Health Statistics. Vital "
                 "Health Stat 2(135). 2003.",
     "url": "https://web.archive.org/web/20200224153533id_/https://www.cdc.gov/nchs/data/series/sr_02/sr02_135.pdf",
     "http_status": 200, "bytes": 1245730,
     "sha256": "51a4c9f38997fb065561819aa3f68d08ce332fc1c8b0ccbf56dd34bc29037333",
     "note": "The canonical URL https://www.cdc.gov/nchs/data/series/sr_02/sr02_135.pdf "
             "returns HTTP 403 to every automated fetch, so the publisher's own "
             "bytes were taken from a raw web.archive.org capture of that exact "
             "URL. The text layer of that capture is native, not OCR."},
    {"role": "cross-check on the coefficient tables, independent scan",
     "citation": "Same report, ERIC full-text copy ED481807.",
     "url": "https://files.eric.ed.gov/fulltext/ED481807.pdf",
     "http_status": 200, "bytes": 975987,
     "sha256": "d2ec23f7015af367aeaa24f16958571e878476914ef2d58c32b4940acb6c44f7",
     "note": "This copy is an OCR scan and DROPS two Table 7 cells - the "
             "AIAN/Black/White Northeast coefficient and the API/Black Midwest "
             "coefficient come through as bare digit runs with the leading "
             "characters lost. Both are legible in the archived publisher PDF "
             "(-4.53976 and -3.92403). Recorded because a build that had used the "
             "ERIC scan alone would have had to guess two coefficients, which "
             "PROMPT-AUTHOR-TO-30.md S-11 forbids."},
    {"role": "area covariates: the county composition percentages the models use",
     "citation": "U.S. Census Bureau, Census 2000 Modified Race Data Summary "
                 "File, county file mr-co.txt.",
     "url": "https://www2.census.gov/programs-surveys/popest/datasets/2000/modified-race-data-2000/mr-co.txt",
     "http_status": 200, "bytes": 65046291,
     "sha256": "9d77dfc50efba080a03b51880a73b983e8470d1a75ae3ce55c5d6d28cbf48053"},
    {"role": "NCHS's own county urbanisation and region classification",
     "citation": "National Center for Health Statistics, bridged-race county "
                 "probability file cqs_countyprobs.sas7bdat.",
     "url": "https://ftp.cdc.gov/pub/health_statistics/nchs/datasets/nvss/bridgepop/cqs_countyprobs.sas7bdat",
     "http_status": 200, "bytes": 514475008,
     "sha256": "0787181db0f377385b40f415c205fb9dfa2b371975b71920970f165ab1f537a8",
     "note": "Used ONLY for the four-level urbanisation classification and the "
             "region indicators, which are county attributes NCHS released and "
             "which are not derivable from the Census file. See "
             "`cqs_countyprobs_is_not_the_table_7_proportion_set` for what its "
             "probability columns turned out to be."},
    {"role": "publisher's own released output, grader-side measurement only",
     "citation": "National Center for Health Statistics, bridged-race April 1, "
                 "2010 population estimates, census_0401_2010.txt.",
     "url": "https://ftp.cdc.gov/pub/health_statistics/nchs/datasets/nvss/bridgepop/census_0401_2010.txt.zip",
     "http_status": 200, "bytes": 13283930,
     "sha256": "f69a2a18403800fa22b0ec5f5242fedad93fa1520fb1d9ee18f62807da9d4221",
     "note": "4,324,768 records. NEVER shipped agent-side in any form."},
    {"role": "input file the publisher's 2010 output was produced from",
     "citation": "U.S. Census Bureau, Census 2010 Modified Race Data Summary "
                 "File, state-county files.",
     "url": "https://www2.census.gov/programs-surveys/popest/datasets/2010/modified-race-data-2010/stco-mr2010_al_mo.csv"
            " and .../stco-mr2010_mt_wy.csv",
     "http_status": 200, "bytes": 30286031 + 29663828,
     "sha256": "64f01a3ebbf00b439059c26bae0eb3838faf8cd68d99ae7be716066bdb5f7bd8"
               " and 1a2ef8efc9cbdcfdfcee81b93c3b488d9086e3177d081cc292be1ffc91f90230"},
    {"role": "method documentation for the 2010 vintage",
     "citation": "National Center for Health Statistics, Documentation for "
                 "April 1, 2010 Bridged-Race Population Estimates.",
     "url": "https://ftp.cdc.gov/pub/health_statistics/nchs/datasets/nvss/bridgepop/DocumentationBridgedApril1_2010.pdf",
     "http_status": 200, "bytes": 76706,
     "sha256": "5ee0e04f608bb0ede37433ab62674de81c0d986b6de43f7403a357abc0ab12db"},
]


def sha256_of(path):
    import hashlib
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def main():
    r = build()
    graded = r["graded"]
    write_agent_data(r)
    write_cell_universe(r)
    ledger, floor, floor_at = measure_controls(r)
    stats, t9_rows, t9_worst = measure_table9_anchor()
    e2e = measure_end_to_end_2010(r)

    # independent recompute of every golden, through the verifier's second
    # formulation, at build time as well as on every graded run
    sys.path.insert(0, VERIFIER)
    import independent_bridging as ind
    worst_independent = 0.0
    for c in graded:
        area = r["by_fips"][r["ufips"][c["area_index"]]]
        got = ind.shares(c["group"], area, c["age"], c["male"],
                         c["hispanic"])[c["target"]]
        worst_independent = max(worst_independent, abs(got - c["ref"]))

    items, flat_refs = [], {}
    for c in graded:
        cid = case_id(c)
        items.append({"kind": "share", "key": c["record_id"],
                      "ref": c["ref"], "tolerance": TOLERANCE_ABS,
                      "response_group": GROUP_LABEL[c["group"]],
                      "target_category": c["target"],
                      "area_id": r["area_id"][c["area_index"]],
                      "age_years": c["age"],
                      "sex": "male" if c["male"] else "female",
                      "hispanic_origin": "hispanic" if c["hispanic"] else "not_hispanic"})
        flat_refs["ref_%s" % cid.replace("-", "_")] = c["ref"]
        flat_refs["tolerance_%s_abs" % cid.replace("-", "_")] = TOLERANCE_ABS

    round_clearance = min(
        min(abs(c["ref"] - g) for g in ROUND_FIGURES) for c in graded) / TOLERANCE_ABS
    refs = sorted(c["ref"] for c in graded)
    separation = min(b - a for a, b in zip(refs, refs[1:])) / TOLERANCE_ABS
    smallest = min(min(c["gaps"].values()) for c in graded) / TOLERANCE_ABS
    nearest = ledger[NEAREST_REAL_COMPETITOR]["min_gap_multiple"]

    expected = dict(flat_refs)
    expected.update({
        "schema": "flat-ref-plus-items",
        "items": items,
        "control_gaps": ledger,
        "n_cases": len(graded),
        "n_areas": len(r["chosen"]),
        "n_response_groups": len(APPLICABLE),
        "n_group_category_pairs": len(PAIRS),
        "tolerance_abs": TOLERANCE_ABS,
        "tolerance_rel_of_unit_interval": TOLERANCE_ABS,
        "discrimination_floor_multiple": DISCRIMINATION_FLOOR / TOLERANCE_ABS,
        "golden_separation_multiple": round(separation, 4),
        "round_figure_clearance_multiple": round(round_clearance, 4),
        "constant_answer_floor": round(floor, 4),
        "constant_answer_floor_best_constant": round(floor_at, 6),
        "nearest_real_competitor": NEAREST_REAL_COMPETITOR,
        "nearest_real_competitor_gap_multiple": nearest,
        "smallest_wrong_path_gap_multiple": round(smallest, 4),
        "independent_recompute_maxabs": worst_independent,
        # QC V-23 parses published_precision_ambiguity_<output>_maxabs and matches
        # <output> against the graded tolerances. Without the output token it
        # captures "ambiguity", which matches nothing, and the band reads as
        # recorded-but-never-compared. Same value, named so the check can bind.
        "published_precision_ambiguity_share_maxabs": worst_independent,
        "published_precision_ambiguity_method": (
            "MEASURED, not asserted: every graded share re-derived through the "
            "verifier's independent formulation - a second transcription of the "
            "published tables in a different layout, odds accumulated "
            "multiplicatively, the two-category models inverted by bisection on "
            "the logit equation and every multi-category model computed as a "
            "conditional normalisation over the applicable categories - and the "
            "worst absolute disagreement against the frozen golden taken over "
            "all %d graded cases." % len(graded)),
        "table9_anchor_worst_absolute_difference": round(t9_worst, 4),
        "table9_anchor_bound": 0.15,
        "seed": SEED,
        "seed_base": SEED_BASE,
        "candidate_records_swept": len(r["candidates"]),
        "candidate_records_surviving_discrimination": len(r["surviving"]),
        "candidate_records_dropped": r["dropped"],
        "tolerance_rationale": (
            "One absolute band, %.4f on a share that lives in [0, 1], applied to "
            "every graded case. LOWER BOUND (defensible-reading spread): zero. "
            "The published coefficients are exact decimals and every covariate is "
            "shipped in the input, so two faithful readings of the same published "
            "model cannot differ at all; the measured spread of the INDEPENDENT "
            "re-derivation is %.3e, which is %.0f times inside the band. UPPER "
            "BOUND (nearest wrong route): the nearest real competitor, the "
            "published country-wide flat shares that question.json ships as an "
            "orientation block, sits %.2f tolerances away on its closest graded "
            "case, and EVERY graded case clears EVERY route reachable without the "
            "withheld coefficient set by more than %.1f tolerances - that is "
            "enforced per case at build time, not merely measured afterwards. "
            "The band is therefore wide enough that no faithful reading fails and "
            "narrow enough that no competing method passes."
            % (TOLERANCE_ABS, worst_independent,
               TOLERANCE_ABS / max(worst_independent, 1e-18),
               nearest, DISCRIMINATION_FLOOR / TOLERANCE_ABS)),
    })
    with open(os.path.join(VERIFIER, "expected_values.json"), "w") as fh:
        json.dump(expected, fh, indent=2, sort_keys=True)
        fh.write("\n")

    report = build_report(r, ledger, floor, floor_at, stats, t9_rows, t9_worst,
                          e2e, worst_independent, items, separation,
                          round_clearance, smallest, nearest)
    with open(os.path.join(ROOT, "build", "build_report.json"), "w") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print("graded cases        : %d" % len(graded))
    print("constant-answer floor: %.4f (best constant %.6f)" % (floor, floor_at))
    print("smallest wrong-path gap: %.2fx tolerance" % smallest)
    print("independent recompute : %.3e worst absolute" % worst_independent)
    print("Table 9 anchor        : %.4f worst absolute difference" % t9_worst)
    for k in ("WHITE", "BLACK", "AIAN", "API"):
        print("2010 end-to-end %-6s: %+.4f%%" % (k, e2e[k]["relative_difference_pct"]))
    return 0




LICENCE = {
    "gate_a_access": (
        "PASS - every file used is publicly downloadable with no login. Two "
        "access facts are recorded because they are operational, not incidental: "
        "www.cdc.gov returns HTTP 403 to automated fetches, so the publisher's "
        "own report PDF was taken from a raw web.archive.org capture of the "
        "canonical URL, while ftp.cdc.gov serves the whole NCHS bulk tree "
        "without a User-Agent workaround; and stacks.cdc.gov also 403s. "
        "www2.census.gov serves the Modified Race Data Summary Files directly."),
    "gate_b_licence": "PASS with obligations",
    "quotes": [
        "Most of the information on the CDC and ATSDR websites is not subject to "
        "copyright, is in the public domain, and may be freely used or reproduced "
        "without obtaining copyright permission. (CDC, Use of Agency Materials, "
        "https://www.cdc.gov/other/agencymaterials.html)",
        "The following requirements must be followed to utilize CDC's public "
        "domain content: 1) Attribution to the agency that developed the material "
        "must be provided in your use of the materials. (CDC, Use of Agency "
        "Materials)",
        "These confidentiality laws state the data collected by NCHS may be used "
        "only for statistical reporting and analysis. Any effort to determine the "
        "identity of individuals and establishments violates the assurances of "
        "confidentiality provided by federal law. (NCHS Data User Agreement, "
        "https://www.cdc.gov/nchs/data_access/restrictions.htm)",
        "Therefore, users will: Use the data in this dataset for statistical "
        "reporting and analysis only. Make no attempt to learn the identity of "
        "any person or establishment included in these data. Not link this "
        "dataset with individually identifiable data from other NCHS or non-NCHS "
        "datasets. Not engage in any efforts to assess disclosure methodologies "
        "applied to protect individuals and establishments or any research on "
        "methods of re-identification of individuals and establishments. (NCHS "
        "Data User Agreement)",
        "Proper citation ensures that Census Bureau statistical products and "
        "research can be discovered, reused, replicated for verification, and "
        "credited for recognition to measure usage and impact. (U.S. Census "
        "Bureau, Citing our Data, Tools, Technical Documents and Research, "
        "https://www.census.gov/about/policies/citation.html)",
        "Data users who create their own estimates using data from disseminated "
        "tables and other data should cite the Census Bureau as the source of the "
        "original data only. Conclusions drawn from any analysis of these data "
        "are the sole responsibility of the performing party. (U.S. Census "
        "Bureau, Citing our Data, Tools, Technical Documents and Research)",
    ],
    "obligations_met": [
        "attribution carried in this report, in verifier/truth.md, in "
        "verifier/process/TRUTH.md, in the skill's source line and in every "
        "module that carries a transcribed coefficient",
        "the Census Bureau is cited as the source of the original data, and the "
        "derived area percentages are labelled as derived rather than presented "
        "as Census Bureau estimates",
        "no CDC, HHS or Census Bureau logo, emblem or endorsement is used",
        "NCHS Data User Agreement respected in full: every figure in this bundle "
        "is a county-level statistical aggregate or a model-implied share, no "
        "record-level microdata is used, no re-identification is attempted, "
        "nothing is linked to any identifiable record, and no disclosure "
        "methodology is assessed",
        "the county identifiers are replaced by opaque labels in everything the "
        "agent can see, which is stricter than the agreement requires",
    ],
    "honest_caveat": (
        "The CDC public-domain statement is site-wide, not file-level: there is "
        "no LICENSE file, SPDX tag or CC0 dedication anywhere in the NCHS "
        "bridged-race FTP tree, and CDC's own page carves out contractor-developed "
        "and third-party-licensed material. A contractor-attribution grep over the "
        "NCHS bridged-race tree returned zero hits, and the report itself is "
        "authored by named NCHS staff, so the carve-out does not appear to bite - "
        "but the verdict rests on the general statements quoted above plus the "
        "absence of any redistribution restriction, NOT on a 'US federal therefore "
        "public domain' inference, which is unsound. On the Census side, "
        "https://www.census.gov/about/policies/open-government/data-policy.html is "
        "a 404 (HTTP 404, 26,711-byte 'Page not found' body) and is deliberately "
        "NOT cited here; the live citation policy page is."),
}


def build_report(r, ledger, floor, floor_at, stats, t9_rows, t9_worst, e2e,
                 worst_independent, items, separation, round_clearance,
                 smallest, nearest):
    graded = r["graded"]
    sources = [dict(s) for s in SOURCES]
    slices = {}
    for name in sorted(os.listdir(SOURCE)):
        p = os.path.join(SOURCE, name)
        slices[name] = {"bytes": os.path.getsize(p), "sha256": sha256_of(p)}
    return {
        "task": "bridged-race-population-estimates",
        "built_by": "build/gen.py",
        "seed": SEED,
        "seed_base": SEED_BASE,
        "delta_lever": (
            "A census response naming more than one race is assigned to one of "
            "the four 1977-standard categories with the logistic-regression "
            "coefficient set NCHS estimated from National Health Interview Survey "
            "primary-race answers - Table 7's six separate models and Table 8's "
            "composite multi-logit, evaluated on that person's own age, sex, "
            "Hispanic origin and county composition - not by splitting the "
            "response equally over the categories it names and not in proportion "
            "to the area's single-category counts."),
        "gap_type": "(b) a published, measured coefficient set the default route "
                    "replaces with an arithmetic split",
        "failure_family": "F2 (a real published statistical model the default "
                          "route substitutes with a plausible arithmetic rule)",
        "template": "A - a real, published, citable, non-recallable coefficient "
                    "set carried in the skill, a neutral in-input distractor the "
                    "default grabs (question.json's orientation block of published "
                    "country-wide flat shares), and genuine multi-stage "
                    "computation: model selection, two footnoted covariate "
                    "transforms, reference categories, an age cap, and a "
                    "conditional rescale over the categories that apply.",
        "phase_1_scope_exception": (
            "PROMPT-AUTHOR-TO-30.md section 3.2 / ERZA-OTS.md section 4 scope "
            "Phase 1 to Natural Science. This task is DEMOGRAPHIC / official "
            "statistics and is therefore filed as category `finance-economics` "
            "with `secondary_category: office-white-collar`, both of which are "
            "outside Phase 1. FLAGGED FOR A HUMAN to accept or defer, not "
            "resolved unilaterally. The diversity argument for accepting it is "
            "that Phase-1-only cannot meet the Tier-1 target of two domains per "
            "family, and the licence-clear sources for a genuine published "
            "coefficient set of this kind live in official statistics."),
        "graded_set": {
            "n_cases": len(graded),
            "n_cases_is_prime": True,
            "composition": (
                "One graded case for each of the 28 (response group, target "
                "category) pairs the published method produces - the report's own "
                "'set of 28 probabilities, one for selecting each possible primary "
                "race in each of the 11 multiple-race groups' - plus three extras "
                "that exercise the age cap at 70 and over, Hispanic origin, and "
                "the four-way conditional rescale."),
            "extras": [c["record_id"] + ": " + c["extra"]
                       for c in graded if c.get("extra")],
            "tolerance": "%.4f absolute on a share in [0, 1], per case" % TOLERANCE_ABS,
            "goldens": {case_id(c): round(c["ref"], 9) for c in graded},
            "records": {case_id(c): {
                "area_id": r["area_id"][c["area_index"]],
                "response_group": GROUP_LABEL[c["group"]],
                "target_category": c["target"], "age_years": c["age"],
                "sex": "male" if c["male"] else "female",
                "hispanic_origin": "hispanic" if c["hispanic"] else "not_hispanic",
                "enumerated_population_of_the_cell": c["population"]}
                for c in graded},
            "measured_separation_min_multiple": {
                k: v["min_gap_multiple"] for k, v in sorted(ledger.items())},
        },
        "discrimination_assertion": {
            "rule": (
                "S-LAYER-GATE-2026-07-28.md sections 14-15: every graded case must "
                "be one the withheld object actually decides. Enforced per "
                "candidate at build time against ALL THREE routes reachable "
                "without the coefficient set - the equal split, the split "
                "proportional to the area's own single-category percentages, and "
                "the published country-wide flat shares that question.json ships "
                "- at a floor of %.1fx the graded tolerance. A candidate failing "
                "any one of them is DROPPED, never recorded as non-discriminating."
                % (DISCRIMINATION_FLOOR / TOLERANCE_ABS)),
            "candidate_records_swept": len(r["candidates"]),
            "candidate_records_surviving": len(r["surviving"]),
            "candidate_records_dropped_by_reason": r["dropped"],
            "carried_into_the_verifier_as_a_standing_self_check":
                "test_every_graded_case_is_decided_by_the_withheld_models",
            "smallest_surviving_gap_multiple": round(smallest, 4),
        },
        "constant_answer_floor": {
            "value": round(floor, 4),
            "cases_cleared": int(round(floor * len(graded))),
            "best_constant": round(floor_at, 6),
            "method": "exhaustive sweep of a single constant answer over [0, 1] "
                      "at 5e-06 resolution, scored against the graded tolerance",
            "why_it_is_at_the_floor": (
                "The graded set is built with a minimum pairwise separation of "
                "%.2f tolerances between goldens (measured: %.2f), so no constant "
                "can clear two cases. 1/%d is the arithmetic minimum for a set of "
                "this size." % (GOLDEN_SEPARATION / TOLERANCE_ABS, separation,
                                len(graded))),
        },
        "independent_verification": {
            "method": (
                "INDEPENDENT SECOND FORMULATION, in the verifier and run on every "
                "graded run: verifier/independent_bridging.py. It is not the "
                "oracle's code - the published tables are transcribed a second "
                "time in a model-major layout rather than the oracle's "
                "covariate-major one, the odds are accumulated as a product of "
                "per-covariate factors rather than as one exponential of a summed "
                "linear predictor, the two-category models are inverted by "
                "bisection on the logit equation rather than by evaluating the "
                "logistic function, and every multi-category model is computed as "
                "a conditional normalisation over the applicable categories "
                "instead of forming the four-category vector and rescaling it."),
            "worst_disagreement_abs": worst_independent,
            "worst_disagreement_note": "%.3e against a %.4f graded tolerance"
                                       % (worst_independent, TOLERANCE_ABS),
            "publisher_anchor": {
                "what": (
                    "NCHS Table 9 of the same report publishes the mean, median, "
                    "interquartile bounds, minimum and maximum of the bridging "
                    "proportions for all 28 (group, category) series - 168 "
                    "published numbers describing exactly the quantity this task "
                    "grades. verifier/anchor_table9.csv carries them and "
                    "test_published_table9_distribution_is_reproduced recomputes "
                    "them over the published cell universe on every graded run."),
                "worst_absolute_difference": round(t9_worst, 4),
                "rows": t9_rows,
                "known_one_sided_bias": (
                    "Table 9's cell universe is every county, SINGLE YEAR of age, "
                    "sex and Hispanic origin combination with a non-zero "
                    "population for the group. The public Modified Race Data "
                    "Summary File releases the population by five-year age group, "
                    "so the recompute decides membership at the band the file "
                    "publishes. That is a strict SUPERSET of the publisher's cell "
                    "set, which is why the recomputed minima run at or below the "
                    "published minima and the recomputed maxima at or above them "
                    "on most series. The bound is set at 0.15 absolute to "
                    "accommodate it; the median absolute difference is far "
                    "smaller and is in `rows`."),
            },
        },
        "plausibility_envelope": {
            "share": "every graded value is a share and must satisfy "
                     "0 < share < 1; the goldens run from %.4f to %.4f"
                     % (min(c["ref"] for c in graded), max(c["ref"] for c in graded)),
            "sum_over_a_group": "the shares of one response group must sum to 1 "
                                "over the categories that group can be assigned "
                                "to; asserted on every graded run",
            "against_the_publisher": "every graded value must sit inside the "
                                     "published minimum-to-maximum range Table 9 "
                                     "gives for its own (group, category) series",
        },
        "end_to_end_against_the_publishers_own_2010_output": e2e,
        "end_to_end_verdict": (
            "DOES NOT REPRODUCE, and the task is scoped accordingly. Applying the "
            "published coefficient set to the Census 2010 Modified Race Data "
            "Summary File and comparing against the publisher's own released "
            "bridged file gives national agreement of %+.3f%% (White), %+.3f%% "
            "(API), %+.3f%% (Black) and %+.3f%% (AIAN) on the allocated "
            "multiple-response population. That is far better than either naive "
            "route - the equal split misses AIAN by %+.3f%% and the "
            "proportional-to-single-category split by %+.3f%% - but it is not "
            "golden precision, and two irreducible reasons are known: the public "
            "input file releases population by five-year age group while the "
            "publisher applied the proportions at single years of age, and the "
            "publisher then ran a progressive rounding step that forces integer "
            "counts and preserves cell totals. The graded quantity is therefore "
            "the assignment SHARE, which is what the report itself publishes "
            "distributional characteristics for, and the 2010 comparison is "
            "reported here as a measurement rather than used as a golden."
            % (e2e["WHITE"]["relative_difference_pct"],
               e2e["API"]["relative_difference_pct"],
               e2e["BLACK"]["relative_difference_pct"],
               e2e["AIAN"]["relative_difference_pct"],
               e2e["equal_split"]["AIAN"]["relative_difference_pct"],
               e2e["proportional_to_area_single_category_counts"]["AIAN"]
                  ["relative_difference_pct"])),
        "cqs_countyprobs_is_not_the_table_7_proportion_set": (
            "A scouting note said the publisher's own intermediate "
            "cqs_countyprobs.sas7bdat would give a record-by-record anchor for the "
            "bridging proportions. It does not, and this was MEASURED rather than "
            "assumed. The file carries 879,200 rows (3,140 counties x 70 single "
            "years of age x 2 sexes x 2 origins) and 28 probability columns, which "
            "is the right shape - but regressing the logit of each column on the "
            "Table 7 covariate set gives R-squared between 0.48 and 0.99, while "
            "regressing it on the file's OWN 40 covariates - which include "
            "dissimilarity, interaction and isolation indices, poverty, crowding, "
            "single-parent share, high-school education, foreign-born share and "
            "public-assistance share, none of which appear in Table 7 or Table 8 - "
            "gives R-squared 1.0000000000 with a maximum residual of 7.6e-06. The "
            "file is an EXPANDED, later model, not the published one, and two of "
            "its 28 columns are national constants rather than functions of the "
            "covariates at all. Grading Table 7 output against it would have been "
            "grading against the wrong model. What the file IS used for here is "
            "its county attributes: the four-level urbanisation classification and "
            "the region indicators, which are NCHS's own and are not derivable "
            "from the Census file."),
        "area_covariates_are_the_publishers_own": (
            "The four area percentages the models use were reconstructed from the "
            "public Census 2000 Modified Race Data Summary File and checked "
            "against the values NCHS itself carries: percent single-category AIAN, "
            "percent API, percent Black and percent multiple-response agree "
            "EXACTLY, to the last stored digit, on 3,139 of the 3,140 counties. "
            "The single exception is 51005 (Alleghany County, Virginia), where an "
            "independent-city merge moved population between two FIPS codes. Three "
            "conventions were recovered rather than guessed and are now stated in "
            "the skill: the percentages are rounded to two decimal places before "
            "the transforms are applied; the Asian-and-Pacific-Islander percentage "
            "counts the Asian-and-Native-Hawaiian response as single-category API, "
            "not as a multiple response; and the logarithm of an area's AIAN "
            "percentage is taken after that rounding. Areas whose rounded AIAN "
            "percentage is zero - where NCHS floors the value - are EXCLUDED from "
            "the shipped set, so no graded case depends on a floor the prompt "
            "would have to state."),
        "anonymisation": {
            "method": "Counties are replaced by opaque labels AREA-01 to AREA-%02d "
                      "and no name, FIPS code, state or population appears in "
                      "anything the agent can see. The shipped area profile "
                      "carries only the model covariates plus percent "
                      "single-category White, which the published models "
                      "deliberately exclude." % N_AREAS,
            "why": "PROMPT-AUTHOR-TO-30.md 6.8: network_mode no-network is "
                   "declared but is NOT enforced for LLM arms, so validity must "
                   "not rest on it. With the areas delabelled, the withheld "
                   "coefficient set is the only route to the answer even with "
                   "full internet: the published tables are covariate-indexed, so "
                   "an agent that fetched the report would still have to hold the "
                   "coefficients, and there is no published table of shares keyed "
                   "by anything the agent can see.",
            "residual_risk": "An agent with network access could retrieve the "
                             "report itself and the coefficient tables in it. "
                             "That is the withheld object, so a successful fetch "
                             "is a leak; it is a hygiene signal about the run, "
                             "detected by the process guardrail "
                             "d_g_network_egress, and the reason the pilot must "
                             "run with the egress firewall enabled.",
        },
        "s01_recall_probe": {
            "route_a_recall": (
                "NO, on analysis; the empirical probe is the caller's kill gate "
                "and is recorded OPEN. The withheld object is a 7-column by "
                "14-row table of five-decimal regression coefficients plus a "
                "3-column by 17-row one, from a 2003 NCHS methodology report. "
                "There is no named formula and no round number in it."),
            "route_b_reconstruction": (
                "NO, on analysis, and this is the decisive route. The task grades "
                "the model OUTPUT, so a reconstruction would have to reproduce 31 "
                "shares to 0.002 absolute from remembered five-decimal "
                "coefficients across three different model families. Every route "
                "that does not hold the coefficients is measured to miss every "
                "graded case by more than %.1f tolerances, per case, by "
                "construction. OPEN: not probed empirically here, because this "
                "bundle is handed over before any agent run."
                % (DISCRIMINATION_FLOOR / TOLERANCE_ABS)),
            "route_c_library": (
                "NO. No package implements the NCHS bridging models. The image "
                "carries python:3.11-slim plus numpy and pytest only; statsmodels "
                "and scikit-learn are not installed, and neither would help - "
                "they fit models, they do not carry NCHS's fitted coefficients."),
            "route_d_script": (
                "NO. instruction.md states the goal - report the assignment share for "
                "each listed record - and never states the model, the coefficient "
                "set, the model-selection rule, the covariate transforms or the "
                "rescale. A run can script the arithmetic only once it holds the "
                "table."),
            "verdict": "NOT-RECALLABLE on analysis. The empirical n=1 no-skill "
                       "probe is the caller's kill gate and is deliberately not "
                       "run here.",
        },
        "s05_kill_list": (
            "Cleared. Not a famous formula (the models are named in one 2003 "
            "methodology report), not a named method with a standard "
            "implementation, not a global-standard table, not library-packaged, "
            "not a fully-stated clean cascade (the prompt states no rule), not a "
            "guessable statutory rule, not a single recallable convention, and "
            "NOT an invented house method - every constant in this bundle is a "
            "published, citable coefficient with a page reference."),
        "licence": LICENCE,
        "sources": sources,
        "bundled_source_slices": slices,
        "open_fields": [
            "S-01 route (b) has NOT been probed empirically. The caller runs the "
            "n=1 no-skill kill gate; this bundle is handed over unfrozen and "
            "unpiloted.",
            "PROPERTY 3 IS ACHIEVED IN AGGREGATE, NOT RECORD BY RECORD. The "
            "goldens are computed by the oracle from the published coefficient "
            "set. They are anchored against the publisher in two independent "
            "ways - Table 9's 168 published distributional numbers, reproduced to "
            "%.3f absolute worst case, and the publisher's own 2010 bridged file, "
            "reproduced to %+.3f%% to %+.3f%% by category - but no single graded "
            "share is a number NCHS itself printed. The scouting note that "
            "cqs_countyprobs would supply record-level shares was tested and is "
            "wrong; see cqs_countyprobs_is_not_the_table_7_proportion_set."
            % (t9_worst, min(e2e[c]["relative_difference_pct"] for c in
                             ("WHITE", "BLACK", "AIAN", "API")),
               max(e2e[c]["relative_difference_pct"] for c in
                   ("WHITE", "BLACK", "AIAN", "API"))),
            "The 2010 end-to-end comparison excludes 6 of 3,143 counties whose "
            "boundaries changed between the two censuses (five Alaska boroughs "
            "and Broomfield, Colorado) and one county, 51005, whose Census 2000 "
            "percentages differ from NCHS's stored values because of a Virginia "
            "independent-city merge.",
            "Category and subcategory are recorded as `category_confidence: "
            "medium`: official demographic statistics sit between "
            "finance-economics and office-white-collar in the committed taxonomy, "
            "and neither is a clean fit.",
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
