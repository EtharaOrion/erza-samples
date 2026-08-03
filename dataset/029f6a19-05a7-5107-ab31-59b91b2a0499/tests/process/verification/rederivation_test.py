"""Rederivation: the method TRUTH.md describes reproduces every frozen golden.

The published coefficients are transcribed HERE for a THIRD time - as a flat list
of (covariate, column, value) triples, independently of `oracle/bridging_models.py`
(covariate-major), of `verifier/independent_bridging.py` (model-major) and of
`verifier/process/tests/checks.py` (column-major lists). Four transcriptions
that agree cannot all be the same typo, and this module asserts all four agree
with the machine-readable slice cut from the published PDF as well as reproducing
`verifier/expected_values.json` from the shipped input.

It also carries the answer-free audit of TRUTH.md, the placeholder audit of
task.md, the skill audit, and a re-run of the DISCRIMINATION ASSERTION that
selected the graded set - the rule S-LAYER-GATE-2026-07-28.md sections 14-15
produce.

Paths come from `ERZA_BUNDLE_DIR` (default: the bundle this file lives in). NO
`sys.argv`: under pytest argv holds pytest's own flags, and a module named
`*_test.py` that reads them errors at COLLECTION and takes the rest of the
directory with it.

    python3 -m pytest verification/rederivation_test.py -q
"""
import csv
import json
import math
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PROC = os.path.normpath(os.path.join(HERE, ".."))
BUNDLE = os.environ.get(
    "ERZA_BUNDLE_DIR", os.path.normpath(os.path.join(HERE, "..", "..", "..")))

sys.path.insert(0, os.path.join(BUNDLE, "verifier"))
sys.path.insert(0, os.path.join(BUNDLE, "oracle"))
sys.path.insert(0, os.path.join(PROC, "verifier"))
import independent_bridging as ind  # noqa: E402
import bridging_models as oracle  # noqa: E402
import checks  # noqa: E402

SKILL = os.path.join(BUNDLE, "environment", "skills",
                     "nhis-primary-race-bridging", "SKILL.md")

# --- third, independent transcription ---------------------------------------
# Ingram DD, Parker JD, Schenker N, Weed JA, Hamilton B, Arias E, Madans JH.
# United States Census 2000 population with bridged race categories. National
# Center for Health Statistics. Vital Health Stat 2(135). 2003, Tables 7 and 8.
# Flat triples: (covariate, column heading, coefficient).
THIRD_TABLE7 = [
    ("age_per_10_years", "aian_black:BLACK", -0.05461),
    ("age_per_10_years", "aian_white:AIAN", -0.08968),
    ("age_per_10_years", "api_black:BLACK", 0.05669),
    ("age_per_10_years", "api_white:API", 0.09568),
    ("age_per_10_years", "black_white:BLACK", 0.05532),
    ("age_per_10_years", "aian_black_white:AIAN", 0.26212),
    ("age_per_10_years", "aian_black_white:BLACK", 0.36140),
    ("hispanic_origin", "aian_black:BLACK", -1.92602),
    ("hispanic_origin", "aian_white:AIAN", 0.88834),
    ("hispanic_origin", "api_black:BLACK", -0.10458),
    ("hispanic_origin", "api_white:API", 0.19303),
    ("hispanic_origin", "black_white:BLACK", -0.52253),
    ("hispanic_origin", "aian_black_white:AIAN", 0.35986),
    ("hispanic_origin", "aian_black_white:BLACK", -0.83526),
    ("sex_male", "aian_black:BLACK", -0.12359),
    ("sex_male", "aian_white:AIAN", 0.00972),
    ("sex_male", "api_black:BLACK", 0.33642),
    ("sex_male", "api_white:API", 0.01393),
    ("sex_male", "black_white:BLACK", 0.11948),
    ("sex_male", "aian_black_white:AIAN", -0.43898),
    ("sex_male", "aian_black_white:BLACK", 0.50777),
    ("region_northeast", "aian_black:BLACK", -0.88349),
    ("region_northeast", "aian_white:AIAN", 0.21233),
    ("region_northeast", "api_black:BLACK", -0.45997),
    ("region_northeast", "api_white:API", -0.05520),
    ("region_northeast", "black_white:BLACK", -0.25363),
    ("region_northeast", "aian_black_white:AIAN", -4.53976),
    ("region_northeast", "aian_black_white:BLACK", -3.45593),
    ("region_midwest", "aian_black:BLACK", -1.70126),
    ("region_midwest", "aian_white:AIAN", 0.09144),
    ("region_midwest", "api_black:BLACK", -3.92403),
    ("region_midwest", "api_white:API", -0.06453),
    ("region_midwest", "black_white:BLACK", 0.17140),
    ("region_midwest", "aian_black_white:AIAN", -3.82328),
    ("region_midwest", "aian_black_white:BLACK", -3.79144),
    ("region_south", "aian_black:BLACK", -0.97935),
    ("region_south", "aian_white:AIAN", -0.28494),
    ("region_south", "api_black:BLACK", -1.48264),
    ("region_south", "api_white:API", 0.12694),
    ("region_south", "black_white:BLACK", -0.64386),
    ("region_south", "aian_black_white:AIAN", -5.73385),
    ("region_south", "aian_black_white:BLACK", -2.27313),
    ("urban_large_fringe", "aian_black:BLACK", -0.44211),
    ("urban_large_fringe", "aian_white:AIAN", -0.22069),
    ("urban_large_fringe", "api_black:BLACK", 1.46590),
    ("urban_large_fringe", "api_white:API", 0.50556),
    ("urban_large_fringe", "black_white:BLACK", -0.07649),
    ("urban_large_fringe", "aian_black_white:AIAN", 2.78910),
    ("urban_large_fringe", "aian_black_white:BLACK", 2.31011),
    ("urban_medium_small_metro", "aian_black:BLACK", 0.88281),
    ("urban_medium_small_metro", "aian_white:AIAN", -0.44238),
    ("urban_medium_small_metro", "api_black:BLACK", 1.67953),
    ("urban_medium_small_metro", "api_white:API", 0.07443),
    ("urban_medium_small_metro", "black_white:BLACK", 0.28938),
    ("urban_medium_small_metro", "aian_black_white:AIAN", 2.27176),
    ("urban_medium_small_metro", "aian_black_white:BLACK", 0.75477),
    ("urban_nonmetro", "aian_black:BLACK", -0.38427),
    ("urban_nonmetro", "aian_white:AIAN", -0.13978),
    ("urban_nonmetro", "api_black:BLACK", 0.13301),
    ("urban_nonmetro", "api_white:API", -0.62956),
    ("urban_nonmetro", "black_white:BLACK", 0.57636),
    ("urban_nonmetro", "aian_black_white:AIAN", 4.17804),
    ("urban_nonmetro", "aian_black_white:BLACK", 1.64725),
    ("pct_aian_in_area", "aian_black:BLACK", -0.43045),
    ("pct_aian_in_area", "aian_white:AIAN", 0.51235),
    ("pct_aian_in_area", "aian_black_white:AIAN", 0.54579),
    ("pct_aian_in_area", "aian_black_white:BLACK", 0.39101),
    ("pct_api_in_area", "api_black:BLACK", -0.13245),
    ("pct_api_in_area", "api_white:API", 0.00735),
    ("pct_black_in_area", "aian_black:BLACK", 0.0000258),
    ("pct_black_in_area", "api_black:BLACK", 0.02078),
    ("pct_black_in_area", "black_white:BLACK", 0.00079),
    ("pct_black_in_area", "aian_black_white:AIAN", 0.11100),
    ("pct_black_in_area", "aian_black_white:BLACK", 0.04985),
    ("pct_multiple_in_area", "aian_black:BLACK", -0.16934),
    ("pct_multiple_in_area", "aian_white:AIAN", -0.07906),
    ("pct_multiple_in_area", "api_black:BLACK", 0.31250),
    ("pct_multiple_in_area", "api_white:API", 0.09791),
    ("pct_multiple_in_area", "black_white:BLACK", 0.31679),
    ("pct_multiple_in_area", "aian_black_white:AIAN", -0.23972),
    ("pct_multiple_in_area", "aian_black_white:BLACK", -0.02919),
    ("constant", "aian_black:BLACK", 3.08086),
    ("constant", "aian_white:AIAN", -0.70527),
    ("constant", "api_black:BLACK", 0.45883),
    ("constant", "api_white:API", -1.18887),
    ("constant", "black_white:BLACK", -0.17533),
    ("constant", "aian_black_white:AIAN", -0.64594),
    ("constant", "aian_black_white:BLACK", 0.77004),
]
THIRD_TABLE8 = [
    ("indicator_not_aian", "API", 2.78725), ("indicator_not_aian", "BLACK", 2.19772),
    ("indicator_not_api", "AIAN", 2.83058), ("indicator_not_api", "BLACK", 3.06153),
    ("indicator_not_black", "AIAN", 0.97010), ("indicator_not_black", "API", 1.61570),
    ("age_per_10_years", "AIAN", -0.03967), ("age_per_10_years", "API", 0.01946),
    ("age_per_10_years", "BLACK", -0.01691),
    ("hispanic_origin", "AIAN", 0.84013), ("hispanic_origin", "API", 0.21507),
    ("hispanic_origin", "BLACK", -0.58721),
    ("sex_male", "AIAN", 0.01914), ("sex_male", "API", 0.01283),
    ("sex_male", "BLACK", -0.08093),
    ("region_northeast", "AIAN", 0.59649), ("region_northeast", "API", -0.13221),
    ("region_northeast", "BLACK", 0.40115),
    ("region_midwest", "AIAN", 0.43237), ("region_midwest", "API", -0.15172),
    ("region_midwest", "BLACK", 0.20136),
    ("region_south", "AIAN", -0.22255), ("region_south", "API", -0.24854),
    ("region_south", "BLACK", -0.29365),
    ("urban_large_fringe", "AIAN", 0.15744), ("urban_large_fringe", "API", 0.46028),
    ("urban_large_fringe", "BLACK", 0.12070),
    ("urban_medium_small_metro", "AIAN", -0.17318),
    ("urban_medium_small_metro", "API", -0.09493),
    ("urban_medium_small_metro", "BLACK", -0.11129),
    ("urban_nonmetro", "AIAN", 0.25013), ("urban_nonmetro", "API", -0.15342),
    ("urban_nonmetro", "BLACK", -0.12077),
    ("pct_aian_in_area", "AIAN", 0.56512), ("pct_aian_in_area", "API", 0.06996),
    ("pct_aian_in_area", "BLACK", -0.00347),
    ("pct_api_in_area", "AIAN", 0.04203), ("pct_api_in_area", "API", 0.03741),
    ("pct_api_in_area", "BLACK", 0.05396),
    ("pct_black_in_area", "AIAN", 0.03921), ("pct_black_in_area", "API", 0.03590),
    ("pct_black_in_area", "BLACK", 0.05893),
    ("pct_multiple_in_area", "AIAN", -0.09723),
    ("pct_multiple_in_area", "API", 0.06402),
    ("pct_multiple_in_area", "BLACK", -0.03953),
    ("constant", "AIAN", -5.29417), ("constant", "API", -5.73987),
    ("constant", "BLACK", -5.21431),
]
T7_COLUMNS = ["aian_black:BLACK", "aian_white:AIAN", "api_black:BLACK",
              "api_white:API", "black_white:BLACK", "aian_black_white:AIAN",
              "aian_black_white:BLACK"]
T8_COLUMNS = ["AIAN", "API", "BLACK"]
# which Table 7 column takes which footnoted transform
T7_LOG_AIAN = {"aian_black:BLACK", "aian_white:AIAN"}
T7_SQ_BLACK = {"aian_black:BLACK", "black_white:BLACK"}


def _expected():
    with open(os.path.join(BUNDLE, "verifier", "expected_values.json")) as fh:
        return json.load(fh)


def _areas():
    out = {}
    with open(os.path.join(BUNDLE, "environment", "data",
                           "area_profile.csv")) as fh:
        for row in csv.DictReader(fh):
            for key in ("pct_aian_alone", "pct_api_alone", "pct_black_alone",
                        "pct_white_alone", "pct_multiple_response"):
                row[key] = float(row[key])
            out[row["area_id"]] = row
    return out


def _question():
    with open(os.path.join(BUNDLE, "environment", "data", "question.json")) as fh:
        return json.load(fh)


def _slice7():
    out = {}
    with open(os.path.join(BUNDLE, "build", "source",
                           "sr02_135_table7.csv")) as fh:
        for row in csv.DictReader(fh):
            name = row.pop("covariate")
            for column, value in row.items():
                if value != "":
                    out[(name, column)] = float(value)
    return out


def _slice8():
    out = {}
    with open(os.path.join(BUNDLE, "build", "source",
                           "sr02_135_table8.csv")) as fh:
        for row in csv.DictReader(fh):
            name = row.pop("covariate")
            for column, value in row.items():
                out[(name, column)] = float(value)
    return out


def _case_id(item):
    return "%s-%s" % (item["kind"], item["key"])


EXP = _expected()
ITEMS = EXP["items"]


# --------------------------- the rederivation --------------------------- #

def _third_shares(group, area, age, male, hispanic):
    """A THIRD evaluation path, built from the flat triples above."""
    t7 = {}
    for name, column, value in THIRD_TABLE7:
        t7.setdefault(column, {})[name] = value
    t8 = {}
    for name, column, value in THIRD_TABLE8:
        t8.setdefault(column, {})[name] = value

    def design(log_aian, sq_black):
        pa, pb = area["pct_aian_alone"], area["pct_black_alone"]
        return {
            "age_per_10_years": min(int(age), 69) / 10.0,
            "hispanic_origin": 1.0 if hispanic else 0.0,
            "sex_male": 1.0 if male else 0.0,
            "region_northeast": 1.0 if area["region"] == "northeast" else 0.0,
            "region_midwest": 1.0 if area["region"] == "midwest" else 0.0,
            "region_south": 1.0 if area["region"] == "south" else 0.0,
            "urban_large_fringe": 1.0 if area["urbanisation"] == "large_fringe" else 0.0,
            "urban_medium_small_metro":
                1.0 if area["urbanisation"] == "medium_small_metro" else 0.0,
            "urban_nonmetro": 1.0 if area["urbanisation"] == "nonmetro" else 0.0,
            "pct_aian_in_area": math.log(pa) if log_aian else pa,
            "pct_api_in_area": area["pct_api_alone"],
            "pct_black_in_area": pb ** 2 if sq_black else pb,
            "pct_multiple_in_area": area["pct_multiple_response"],
            "constant": 1.0,
        }

    def eta7(column):
        x = design(column in T7_LOG_AIAN, column in T7_SQ_BLACK)
        return sum(b * x[name] for name, b in t7[column].items())

    two = {"AIAN_BLACK": ("aian_black:BLACK", "BLACK", "AIAN"),
           "AIAN_WHITE": ("aian_white:AIAN", "AIAN", "WHITE"),
           "API_BLACK": ("api_black:BLACK", "BLACK", "API"),
           "API_WHITE": ("api_white:API", "API", "WHITE"),
           "BLACK_WHITE": ("black_white:BLACK", "BLACK", "WHITE")}
    if group in two:
        column, modelled, other = two[group]
        p = 1.0 / (1.0 + math.exp(-eta7(column)))
        return {modelled: p, other: 1.0 - p}
    if group == "AIAN_BLACK_WHITE":
        a = math.exp(eta7("aian_black_white:AIAN"))
        b = math.exp(eta7("aian_black_white:BLACK"))
        return {"AIAN": a / (1.0 + a + b), "BLACK": b / (1.0 + a + b),
                "WHITE": 1.0 / (1.0 + a + b)}
    applicable = tuple(ind.COMPOSITE_APPLICABLE[group])
    x = design(True, False)
    ind_values = {"indicator_not_aian": 0.0 if "AIAN" in applicable else 1.0,
                  "indicator_not_api": 0.0 if "API" in applicable else 1.0,
                  "indicator_not_black": 0.0 if "BLACK" in applicable else 1.0}
    e = {}
    for column in T8_COLUMNS:
        total = 0.0
        for name, b in t8[column].items():
            total += b * (ind_values[name] if name in ind_values else x[name])
        e[column] = math.exp(total)
    e["WHITE"] = 1.0
    kept = {c: e[c] for c in applicable}
    denom = sum(kept.values())
    return {c: v / denom for c, v in kept.items()}


@pytest.mark.parametrize("item", ITEMS, ids=[_case_id(i) for i in ITEMS])
def test_frozen_golden_is_reproduced(item):
    """Every stored reference reproduces from the shipped input, exactly."""
    areas = _areas()
    group = "_".join(p.strip().upper()
                     for p in item["response_group"].split("+"))
    got = _third_shares(group, areas[item["area_id"]], item["age_years"],
                        item["sex"] == "male",
                        item["hispanic_origin"] == "hispanic")[item["target_category"]]
    assert abs(got - item["ref"]) <= 1e-12, (
        "%s: rederived %.15f, frozen %.15f - the golden and the bundle have "
        "drifted apart" % (_case_id(item), got, item["ref"]))


def test_all_four_transcriptions_agree_with_the_bundled_source():
    """The oracle's tables, the verifier's, the process checks' and this one must
    all equal the slice cut from the published PDF. Four that agree cannot be the
    same typo."""
    slice7, slice8 = _slice7(), _slice8()
    third7 = {(n, c): v for n, c, v in THIRD_TABLE7}
    assert set(third7) == set(slice7), (
        "Table 7 cells disagree with the slice: only-in-rederivation=%s "
        "only-in-slice=%s" % (sorted(set(third7) - set(slice7)),
                              sorted(set(slice7) - set(third7))))
    for key, value in slice7.items():
        assert abs(third7[key] - value) < 1e-12, \
            "rederivation Table 7 %s is %r, the slice says %r" % (key, third7[key], value)
        name, column = key
        i = T7_COLUMNS.index(column)
        assert abs(oracle.TABLE7[name][i] - value) < 1e-12, \
            "oracle Table 7 %s is %r, the slice says %r" % (key, oracle.TABLE7[name][i], value)

    third8 = {(n, c): v for n, c, v in THIRD_TABLE8}
    for key, value in slice8.items():
        name, column = key
        i = T8_COLUMNS.index(column)
        assert abs(oracle.TABLE8[name][i] - value) < 1e-12, \
            "oracle Table 8 %s is %r, the slice says %r" % (key, oracle.TABLE8[name][i], value)
        if value != 0.0:
            assert abs(third8[key] - value) < 1e-12, \
                "rederivation Table 8 %s is %r, the slice says %r" % (key, third8[key], value)

    # the verifier's model-major transcription
    column_of = {"aian_black:BLACK": ("AIAN_BLACK", "BLACK"),
                 "aian_white:AIAN": ("AIAN_WHITE", "AIAN"),
                 "api_black:BLACK": ("API_BLACK", "BLACK"),
                 "api_white:API": ("API_WHITE", "API"),
                 "black_white:BLACK": ("BLACK_WHITE", "BLACK"),
                 "aian_black_white:AIAN": ("AIAN_BLACK_WHITE", "AIAN"),
                 "aian_black_white:BLACK": ("AIAN_BLACK_WHITE", "BLACK")}
    for (name, column), value in slice7.items():
        spec = ind.SEPARATE_MODELS[column_of[column]]
        assert abs(spec["beta"].get(name, 0.0) - value) < 1e-12, \
            "verifier Table 7 %s/%s disagrees with the slice" % (name, column)
    for (name, column), value in slice8.items():
        assert abs(ind.COMPOSITE_MODELS[column].get(name, 0.0) - value) < 1e-12, \
            "verifier Table 8 %s/%s disagrees with the slice" % (name, column)

    # the process channel's column-major transcription
    for key, values in checks.TABLE7.items():
        column = {"AIAN_BLACK": "aian_black:BLACK", "AIAN_WHITE": "aian_white:AIAN",
                  "API_BLACK": "api_black:BLACK", "API_WHITE": "api_white:API",
                  "BLACK_WHITE": "black_white:BLACK"}.get(
            key[0], "aian_black_white:%s" % key[1])
        published = sorted(
            ((name, v) for (name, c), v in slice7.items() if c == column),
            key=lambda t: _T7_ROW_ORDER.index(t[0]))
        assert [round(v, 10) for _n, v in published] == [round(v, 10) for v in values], \
            "process-channel Table 7 column %s disagrees with the slice" % column
    for column, values in checks.TABLE8.items():
        published = [v for (name, c), v in slice8.items()
                     if c == column and v != 0.0]
        assert sorted(round(v, 10) for v in published) == \
            sorted(round(v, 10) for v in values), \
            "process-channel Table 8 column %s disagrees with the slice" % column


_T7_ROW_ORDER = ["age_per_10_years", "hispanic_origin", "sex_male",
                 "region_northeast", "region_midwest", "region_south",
                 "urban_large_fringe", "urban_medium_small_metro",
                 "urban_nonmetro", "pct_aian_in_area", "pct_api_in_area",
                 "pct_black_in_area", "pct_multiple_in_area", "constant"]


def test_skill_tables_match_the_bundled_source_cell_by_cell():
    """Every coefficient in the skill's two tables is the publisher's.

    This exists because the skill is the withheld object: a constant that is not
    the publisher's would make the with-skill arm wrong in a way nothing else in
    the bundle would catch, since the skill is not read by the oracle or the
    verifier.
    """
    with open(SKILL) as fh:
        text = fh.read()
    def renderings(value):
        out = {("%%.%df" % dp) % value for dp in (5, 6, 7)}
        out.add(repr(value))
        out.add("%g" % value)
        return {r for r in out if float(r) == value}

    checked = 0
    for table, name_of in ((_slice7(), "Table 7"), (_slice8(), "Table 8")):
        for (name, column), value in sorted(table.items()):
            if value == 0.0:
                continue
            forms = renderings(value)
            assert any(form in text for form in forms), (
                "the skill does not carry the published %s value %r for %s/%s "
                "in any of the forms %s"
                % (name_of, value, name, column, sorted(forms)))
            checked += 1
    # 89 non-empty Table 7 cells + 47 non-zero Table 8 cells
    assert checked == 136, "the skill audit covered %d cells" % checked


def test_control_ledger_reproduces_from_the_shipped_bundle():
    """The three routes the discrimination assertion is run against re-measure to
    what the ledger stores."""
    areas = _areas()
    flat = _question()["orientation_flat_shares"]
    tol = EXP["tolerance_abs"]
    pct = {"AIAN": "pct_aian_alone", "API": "pct_api_alone",
           "BLACK": "pct_black_alone", "WHITE": "pct_white_alone"}
    for name in ("equal_split", "proportional_to_area_single_category_counts",
                 "flat_national_shares"):
        multiples = []
        for item in ITEMS:
            parts = [p.strip().upper() for p in item["response_group"].split("+")]
            area = areas[item["area_id"]]
            if name == "equal_split":
                got = 1.0 / len(parts)
            elif name == "flat_national_shares":
                got = flat[item["response_group"]][item["target_category"]]
            else:
                weights = {c: area[pct[c]] for c in parts}
                got = weights[item["target_category"]] / sum(weights.values())
            multiples.append(abs(got - item["ref"]) / tol)
        stored = EXP["control_gaps"][name]["min_gap_multiple"]
        assert abs(min(multiples) - stored) < 0.01, (
            "control %s: measured %.4fx, stored %.4fx"
            % (name, min(multiples), stored))
        assert min(multiples) > EXP["discrimination_floor_multiple"], (
            "control %s sits %.2fx from the reference, inside the %.1fx "
            "discrimination floor"
            % (name, min(multiples), EXP["discrimination_floor_multiple"]))
        assert EXP["control_gaps"][name]["n_cases_inside_tolerance"] == 0, \
            "control %s lands inside tolerance on a graded case" % name


def test_every_control_route_carries_a_note_and_a_measurement():
    """6.6: the QC pass greps `note`, not `description`, and a route with no
    measurement is an assertion rather than a ledger entry."""
    for name, entry in EXP["control_gaps"].items():
        assert entry.get("note"), "control %s carries no note" % name
        assert "per_case_gap_multiple" in entry or "measured" in entry, \
            "control %s carries no per-case measurement" % name
        if entry.get("n_cases_inside_tolerance"):
            assert entry.get("non_discriminating_note"), \
                "control %s clears cases but records no non-discriminating note" % name


# --------------------------- TRUTH.md audit --------------------------- #

def _truth():
    with open(os.path.join(PROC, "TRUTH.md")) as fh:
        return fh.read()


def _renderings(value):
    """Every plausible printed form of a graded value, 2 to 6 decimal places."""
    return {("%%.%df" % dp) % value for dp in (2, 3, 4, 5, 6)} | {repr(value)}


@pytest.mark.parametrize("item", ITEMS, ids=[_case_id(i) for i in ITEMS])
def test_truth_md_states_no_graded_value(item):
    """TRUTH.md is answer-free by construction: it is handed to the LLM judge, so
    a graded figure printed in it would be a second answer key."""
    truth = _truth()
    for text in _renderings(item["ref"]):
        pattern = r"(?<![\d.])%s(?!\d)" % re.escape(text)
        assert not re.search(pattern, truth), (
            "TRUTH.md prints %r, which is the graded value for %s"
            % (text, _case_id(item)))


def test_truth_md_carries_the_delta_lever_heading():
    """The heading must be the literal ASCII string, not only the Greek letter."""
    assert re.search(r"^#+\s*Delta-lever\s*$", _truth(), re.M), \
        "TRUTH.md has no literal `Delta-lever` heading"


def test_truth_md_avoids_the_forbidden_provenance_phrases():
    """A QC pass fires on these strings regardless of context, including when
    they describe the unaided agent's behaviour."""
    truth = _truth().lower()
    banned = ["from memory", "recalled", "reconstructed from memory",
              "approximated from", "approximate from"]
    hits = [phrase for phrase in banned if phrase in truth]
    assert not hits, "TRUTH.md contains forbidden phrase(s): %s" % ", ".join(hits)


def test_truth_md_withholds_the_coefficient_set():
    """The decisive test of 6.11: prompt + TRUTH.md, without the skill, must not
    be enough to score 1. The fitted constants are the whole lever, so not one of
    them may be printed - the model selection, the covariate coding, the
    transforms, the reference categories and the rescale are, which is what keeps
    the file method rather than an answer key."""
    truth = _truth()
    leaked = []
    for (name, column), value in list(_slice7().items()) + list(_slice8().items()):
        if value == 0.0:
            continue
        for dp in (3, 4, 5):
            text = ("%%.%df" % dp) % value
            if re.search(r"(?<![\d.])%s(?!\d)" % re.escape(text), truth):
                leaked.append("%s/%s = %s" % (name, column, text))
    assert not leaked, (
        "TRUTH.md prints published coefficient(s) %s - with those it becomes a "
        "second answer key" % ", ".join(sorted(set(leaked))))


# --------------------------- task.md audit --------------------------- #

def _task_md():
    with open(os.path.join(BUNDLE, "task.md")) as fh:
        return fh.read()


def test_task_md_placeholders_fail_every_graded_case():
    """6.7: every placeholder number in the prompt must be obviously fake."""
    body = _task_md().split("Output:")[-1]
    numbers = {float(m) for m in re.findall(r"(?<![\w.])\d+\.\d+(?![\w.])", body)}
    assert numbers, "no placeholder number found in the prompt's output block"
    for value in numbers:
        for item in ITEMS:
            assert abs(value - item["ref"]) > item["tolerance"], (
                "the prompt placeholder %r is inside tolerance of %s"
                % (value, _case_id(item)))


def test_task_md_placeholder_key_is_not_a_real_record():
    """The placeholder key must name a record the input does not have."""
    body = _task_md()
    real = {item["key"] for item in ITEMS}
    for key in re.findall(r'"(R-\d+)"', body):
        assert key not in real, \
            "the prompt placeholder key %r names a real record" % key


def test_task_md_does_not_name_the_skill_or_its_significant_words():
    """6.12: the prompt must never name the Skill or its significant words."""
    body = _task_md().lower()
    banned = ["nhis", "primary race", "bridging", "bridged", "bridge",
              "logistic", "regression", "coefficient", "multi-logit", "logit",
              "national health interview", "vital health stat", "ingram",
              "odds ratio"]
    hits = [w for w in banned if w in body]
    assert not hits, "task.md leaks skill vocabulary: %s" % ", ".join(hits)


def test_skill_states_when_not_to_use_it():
    """6.12: the frontmatter description must say when NOT to use the skill."""
    with open(SKILL) as fh:
        text = fh.read()
    front = text.split("---")[1]
    assert re.search(r"do not use|don't use|not appropriate", front, re.I), \
        "the skill's frontmatter description does not say when NOT to use it"


def test_skill_names_no_verifier_internal():
    """6.12: the Skill must never name a tolerance, test name, seed or instance id."""
    with open(SKILL) as fh:
        text = fh.read().lower()
    banned = ["expected_values", "test_graded_case", "tolerance_", "seed",
              "anchor_table9", "cell_universe", "results.json",
              "independent_bridging", "control_gaps", "area-01", "r-01"]
    hits = [w for w in banned if w in text]
    assert not hits, "the skill names verifier internals: %s" % ", ".join(hits)
