"""Outcome verifier for bridged-race-population-estimates.

Deterministic. Grades /root/results.json against the frozen reference. The scored
tests are test_graded_case[...]; everything below the divider is a grader
self-check and is excluded from the reward by test.sh, which also GATES on them.

PROMPT-AUTHOR-TO-30.md 6.1 compliance: this module never imports the oracle's
model code. It re-derives every graded share through `independent_bridging`,
which transcribes the published tables a second time in a different layout,
accumulates the odds multiplicatively, inverts the two-category models by
bisection on the logit equation and computes every multi-category model as a
conditional normalisation over the applicable categories. It additionally
anchors those shares against `anchor_table9.csv` - the distributional
characteristics NCHS itself published for exactly this quantity - recomputed over
the published cell universe in `cell_universe.npz`. A mistyped coefficient
therefore cannot agree with itself.

The anchor cannot be skipped: `independent_bridging.anchor()` and
`.cell_universe()` raise rather than returning empty when their file is absent or
short, and test.sh scores a run 0 when any self-check fails OR is skipped.

S-LAYER-GATE-2026-07-28.md sections 14-15 compliance: the build DROPS any
candidate record whose correct share sits within twice the graded tolerance of a
route reachable without the withheld coefficient set, and
`test_every_graded_case_is_decided_by_the_withheld_models` re-measures that
property on every graded run so it cannot rot.
"""

import csv
import json
import math
import os
import sys

import pytest

VER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, VER)
import independent_bridging as ind  # noqa: E402

EXP = json.load(open(os.path.join(VER, "expected_values.json")))
ITEMS = EXP["items"]
DATA = os.environ.get("DATA_DIR", "/root/data")
RESULTS_PATH = os.environ.get("RESULTS_PATH", "/root/results.json")

TOP_KEY = "assignment_share"


def _case_id(item):
    return "%s-%s" % (item["kind"], item["key"])


def _load_results():
    assert os.path.exists(RESULTS_PATH), "%s does not exist" % RESULTS_PATH
    try:
        with open(RESULTS_PATH) as fh:
            data = json.load(fh)
    except Exception as exc:
        pytest.fail("results.json is not valid JSON: %s" % exc)
    assert isinstance(data, dict), "results.json must be a JSON object"
    return data


def _fetch(results, item):
    assert TOP_KEY in results, "results.json must have an %r object" % TOP_KEY
    payload = results[TOP_KEY]
    assert isinstance(payload, dict), "%r must be an object" % TOP_KEY
    for spelling in (item["key"], item["key"].replace("-", "_"),
                     item["key"].replace("-", "")):
        if spelling in payload:
            return payload[spelling]
    pytest.fail("record %r missing from %s" % (item["key"], TOP_KEY))


@pytest.mark.parametrize("item", ITEMS, ids=[_case_id(i) for i in ITEMS])
def test_graded_case(item):
    results = _load_results()
    value = _fetch(results, item)
    assert isinstance(value, (int, float)) and not isinstance(value, bool), \
        "%s must be a number" % _case_id(item)
    got = float(value)
    assert not math.isnan(got) and not math.isinf(got), \
        "%s must be finite" % _case_id(item)
    ref, tol = item["ref"], item["tolerance"]
    assert abs(got - ref) <= tol, \
        "%s: got %.9f, expected %.9f (tol %.6f)" % (
            _case_id(item), got, ref, tol)


# ---- grader self-checks (NOT scored; test.sh GATES the run on them) ---------

def _areas(data_dir=None):
    out = {}
    with open(os.path.join(data_dir or DATA, "area_profile.csv")) as fh:
        for row in csv.DictReader(fh):
            for key in ("pct_aian_alone", "pct_api_alone", "pct_black_alone",
                        "pct_white_alone", "pct_multiple_response"):
                row[key] = float(row[key])
            out[row["area_id"]] = row
    return out


def _records(data_dir=None):
    with open(os.path.join(data_dir or DATA, "response_records.csv")) as fh:
        return list(csv.DictReader(fh))


def _question(data_dir=None):
    with open(os.path.join(data_dir or DATA, "question.json")) as fh:
        return json.load(fh)


def _group_key(label):
    return "_".join(p.strip().upper() for p in label.split("+"))


def _item_shares(item, areas=None, area_id=None):
    """Every share of this item's response group, through the SECOND
    FORMULATION."""
    areas = areas if areas is not None else _areas()
    return ind.shares(_group_key(item["response_group"]),
                      areas[area_id or item["area_id"]],
                      int(item["age_years"]),
                      item["sex"] == "male",
                      item["hispanic_origin"] == "hispanic")


PCT_COL = {"AIAN": "pct_aian_alone", "API": "pct_api_alone",
           "BLACK": "pct_black_alone", "WHITE": "pct_white_alone"}


def _equal_split(item):
    return 1.0 / len(item["response_group"].split("+"))


def _proportional_to_alone(item, areas):
    area = areas[item["area_id"]]
    parts = [p.strip().upper() for p in item["response_group"].split("+")]
    weights = {c: area[PCT_COL[c]] for c in parts}
    total = sum(weights.values())
    if total <= 0:
        return 1.0 / len(parts)
    return weights[item["target_category"]] / total


def test_frozen_reference_matches_independent_recompute():
    """Every stored golden reproduces through the SECOND FORMULATION, which never
    imports the oracle's model module."""
    areas = _areas()
    bound = max(EXP["independent_recompute_maxabs"] * 10.0, 1e-12)
    assert bound < EXP["tolerance_abs"], \
        "the independent recompute's own spread is not inside the graded band"
    worst = 0.0
    for item in ITEMS:
        got = _item_shares(item, areas)[item["target_category"]]
        gap = abs(got - item["ref"])
        worst = max(worst, gap)
        assert gap <= bound, (
            "freeze drift at %s: independent %.12f vs frozen %.12f (bound %.3e)"
            % (_case_id(item), got, item["ref"], bound))
    assert worst <= bound, \
        "independent agreement %.3e is worse than the declared bound" % worst


def test_published_table9_distribution_is_reproduced():
    """THE PUBLISHER'S OWN ANCHOR, on every graded run.

    NCHS Table 9 publishes the mean, median, interquartile bounds, minimum and
    maximum of these shares for all 28 (response group, category) series, over
    every county, single year of age, sex and Hispanic origin combination in the
    country. This recomputes all 168 numbers from the published cell universe and
    compares them with what NCHS printed. A coefficient that is wrong in both the
    oracle and this module still cannot agree with the publisher's own summary.

    It cannot be skipped: a missing anchor or a missing cell universe raises.
    """
    published = ind.anchor()
    recomputed = ind.table9_statistics()
    assert len(published) == 28, "the published anchor is not the full 28 series"
    bound = EXP["table9_anchor_bound"]
    worst, worst_at = 0.0, None
    for key, pub in published.items():
        assert key in recomputed, "no recomputed series for %s" % (key,)
        got = recomputed[key]
        assert got["n_cells"] > 1000, \
            "%s was recomputed over only %d cells" % (key, got["n_cells"])
        for stat in ("mean", "median", "q1", "q3", "min", "max"):
            d = abs(got[stat] - pub[stat])
            if d > worst:
                worst, worst_at = d, (key, stat)
            assert d <= bound, (
                "%s %s: NCHS published %.3f, the models reproduce %.4f "
                "(difference %.4f, bound %.4f)"
                % (key, stat, pub[stat], got[stat], d, bound))
    assert abs(worst - EXP["table9_anchor_worst_absolute_difference"]) < 5e-4, (
        "the recorded worst Table 9 difference %.4f does not match the measured "
        "%.4f at %s" % (EXP["table9_anchor_worst_absolute_difference"], worst,
                        worst_at))


def test_every_graded_case_is_decided_by_the_withheld_models():
    """THE STANDING DISCRIMINATION SELF-CHECK.

    S-LAYER-GATE-2026-07-28.md sections 14-15: two rigorous bundles were
    discarded because the withheld object decided only a minority of their graded
    cases. Here every graded case must differ, by more than twice the graded
    tolerance, from EVERY route reachable without the withheld coefficient set:
    the equal split, the split proportional to the area's own single-category
    percentages, and the published country-wide flat shares question.json ships.
    """
    areas = _areas()
    flat = _question()["orientation_flat_shares"]
    floor = EXP["discrimination_floor_multiple"] * EXP["tolerance_abs"]
    worst, worst_at = None, None
    for item in ITEMS:
        routes = {
            "equal_split": _equal_split(item),
            "proportional_to_area_single_category_counts":
                _proportional_to_alone(item, areas),
            "flat_national_shares":
                flat[item["response_group"]][item["target_category"]],
        }
        for name, value in routes.items():
            gap = abs(item["ref"] - value)
            if worst is None or gap < worst:
                worst, worst_at = gap, (_case_id(item), name)
            assert gap > floor, (
                "%s is NOT decided by the withheld models: the %s route lands "
                "%.6f from the reference %.6f, inside the %.6f floor"
                % (_case_id(item), name, value, item["ref"], floor))
    assert abs(worst / EXP["tolerance_abs"]
               - EXP["smallest_wrong_path_gap_multiple"]) < 0.01, (
        "the recorded smallest wrong-path gap %.4f does not match the measured "
        "%.4f at %s" % (EXP["smallest_wrong_path_gap_multiple"],
                        worst / EXP["tolerance_abs"], worst_at))


def test_shares_of_a_response_group_sum_to_one():
    """Structural: the shares of one response group must exhaust that group."""
    areas = _areas()
    for item in ITEMS:
        shares = _item_shares(item, areas)
        parts = {p.strip().upper() for p in item["response_group"].split("+")}
        assert set(shares) == parts, (
            "%s: the model produced shares for %s, the response group is %s"
            % (_case_id(item), sorted(shares), sorted(parts)))
        total = sum(shares.values())
        assert abs(total - 1.0) < 1e-12, \
            "%s: the shares sum to %.15f" % (_case_id(item), total)
        assert item["target_category"] in shares, \
            "%s asks for a category its response group does not name" % _case_id(item)


def test_every_model_family_and_every_pair_is_exercised():
    """The graded set must cover all three model families and all 28 (response
    group, category) pairs the published method produces - otherwise a run could
    fail one family and still score well."""
    pairs = {(i["response_group"], i["target_category"]) for i in ITEMS}
    assert len(pairs) == EXP["n_group_category_pairs"] == 28, \
        "the graded set covers %d of the 28 published pairs" % len(pairs)
    groups = {_group_key(i["response_group"]) for i in ITEMS}
    assert groups == set(ind.GROUPS), (
        "graded groups and modelled groups disagree: only-in-graded=%s "
        "only-in-models=%s" % (sorted(groups - set(ind.GROUPS)),
                               sorted(set(ind.GROUPS) - groups)))
    assert any(int(i["age_years"]) >= 70 for i in ITEMS), \
        "no graded case exercises the age cap at 70 and over"
    assert any(i["hispanic_origin"] == "hispanic" for i in ITEMS), \
        "no graded case exercises Hispanic origin"
    assert len({i["area_id"] for i in ITEMS}) >= 10, \
        "the graded set is concentrated in too few areas"


def test_plausibility_envelope_and_guess_resistance():
    """Declared plausibility bound on every golden, plus: no round number, no
    task.md placeholder and no single constant clears more than one case."""
    lo, hi = ind.ENVELOPE
    for item in ITEMS:
        assert lo < item["ref"] < hi, (
            "%s golden %.6f is outside the declared plausible range (%.1f, %.1f) "
            "for a share" % (_case_id(item), item["ref"], lo, hi))

    # the task.md placeholder must fail every graded case (6.7)
    for item in ITEMS:
        assert abs(42.7 - item["ref"]) > item["tolerance"], \
            "the task.md placeholder 42.7 passes %s" % _case_id(item)

    round_figures = [0.0, 0.05, 0.1, 0.125, 0.15, 0.2, 0.25, 0.3, 1.0 / 3.0,
                     0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 2.0 / 3.0, 0.65, 0.7,
                     0.75, 0.8, 0.85, 0.9, 0.95, 1.0]
    clearance = min(abs(i["ref"] - g) / i["tolerance"]
                    for i in ITEMS for g in round_figures)
    assert clearance > 2.0, (
        "a golden sits only %.2f tolerances from a round figure; a flat guess "
        "would score a graded case for free" % clearance)
    assert abs(clearance - EXP["round_figure_clearance_multiple"]) < 0.01, \
        "the recorded round-figure clearance does not match the frozen goldens"

    refs = sorted(i["ref"] for i in ITEMS)
    separation = min(b - a for a, b in zip(refs, refs[1:])) / EXP["tolerance_abs"]
    assert separation > 2.0, (
        "two goldens sit %.2f tolerances apart, so one constant answer would "
        "clear both" % separation)
    assert abs(separation - EXP["golden_separation_multiple"]) < 0.01, \
        "the recorded golden separation does not match the frozen goldens"
    assert abs(EXP["constant_answer_floor"] - 1.0 / len(ITEMS)) < 1e-3, (
        "the recorded constant-answer floor %.4f is not the arithmetic minimum "
        "1/%d = %.4f" % (EXP["constant_answer_floor"], len(ITEMS),
                         1.0 / len(ITEMS)))


def test_orientation_block_fails_every_graded_case():
    """question.json's orientation block is the nearest real competitor. It is
    shipped, so it must not pass anything."""
    question = _question()
    flat = question["orientation_flat_shares"]
    assert flat, "question.json no longer carries the orientation block"
    for item in ITEMS:
        group = item["response_group"]
        assert group in flat, "the orientation block no longer covers %s" % group
        assert item["target_category"] in flat[group], \
            "the orientation block no longer covers %s" % _case_id(item)
        assert abs(flat[group][item["target_category"]] - item["ref"]) \
            > item["tolerance"], \
            "the shipped orientation figure passes graded case %s" % _case_id(item)
    assert "not the answer" in question["orientation_note"].lower(), \
        "the orientation block is no longer labelled as not the answer"


def test_isomorphic_invariance_under_relabelling_and_reordering():
    """V-09: the reference is a property of the record, not of memorised values.

    Two structure-preserving transformations, both applied to the INDEPENDENT
    formulation rather than to the frozen numbers:

      * relabel every area. The models read an area's composition, its region and
        its urbanisation and never its label, so no graded share may move at all.
      * reverse the record order. The shares are per record, so order cannot
        matter; a verifier keyed to position rather than to content would not
        survive this.

    Both relations hold only for a formulation that actually evaluates the
    published equations, so they bind the method as well as the arithmetic.
    """
    areas = _areas()
    relabelled = {"Z-%04d" % (i * 7919 % 10000): dict(a, area_id="Z-%04d" % (i * 7919 % 10000))
                  for i, a in enumerate(areas.values())}
    mapping = {old: new for old, new in
               zip(areas, sorted(relabelled, key=lambda k: list(relabelled).index(k)))}
    for item in ITEMS:
        base = _item_shares(item, areas)[item["target_category"]]
        moved = _item_shares(item, relabelled,
                             area_id=mapping[item["area_id"]])[item["target_category"]]
        assert abs(moved - base) <= 1e-15, (
            "relabel invariance broken at %s: %.15f vs %.15f"
            % (_case_id(item), moved, base))

    forward = [_item_shares(i, areas)[i["target_category"]] for i in ITEMS]
    backward = [_item_shares(i, areas)[i["target_category"]]
                for i in reversed(ITEMS)]
    assert forward == list(reversed(backward)), \
        "the shares depend on the order the records are evaluated in"


def test_tolerances_are_positive_and_bind():
    assert len(ITEMS) == EXP["n_cases"] == 31, "item set malformed"
    seen = set()
    for item in ITEMS:
        assert item["tolerance"] > 0, "non-positive tolerance"
        assert math.isfinite(item["ref"])
        assert abs(item["tolerance"] - EXP["tolerance_abs"]) < 1e-15
        seen.add(_case_id(item))
    assert len(seen) == len(ITEMS), "duplicate case ids"
    assert EXP["published_precision_ambiguity_share_maxabs"] < EXP["tolerance_abs"], \
        "a faithful reading would false-fail"
    assert EXP["nearest_real_competitor_gap_multiple"] > 2.0, \
        "nearest competing method is inside 2x tolerance"
    gaps = EXP["control_gaps"]
    assert gaps[EXP["nearest_real_competitor"]].get("nearest_real_competitor"), \
        "the nearest real competitor is not flagged in the control ledger"
    for name, entry in gaps.items():
        assert entry.get("note"), "control %s carries no note" % name


def test_input_data_is_intact():
    """The graded shares are properties of THESE records; an edited input must not
    be graded against the frozen golden."""
    records = _records()
    assert len(records) == EXP["n_cases"], (
        "response_records.csv has %d rows, expected %d"
        % (len(records), EXP["n_cases"]))
    areas = _areas()
    assert len(areas) == EXP["n_areas"], (
        "area_profile.csv has %d areas, expected %d" % (len(areas), EXP["n_areas"]))
    by_id = {r["record_id"]: r for r in records}
    for item in ITEMS:
        row = by_id.get(item["key"])
        assert row is not None, "record %s is missing from the input" % item["key"]
        for field in ("area_id", "response_group", "target_category"):
            assert row[field] == item[field], (
                "record %s field %s changed: input %r, frozen %r"
                % (item["key"], field, row[field], item[field]))
        assert int(row["age_years"]) == item["age_years"]
        assert row["sex"] == item["sex"]
        assert row["hispanic_origin"] == item["hispanic_origin"]
    with open(os.path.join(DATA, "response_records.csv")) as fh:
        header = next(csv.reader(fh))
    assert header == ["record_id", "area_id", "age_years", "sex",
                      "hispanic_origin", "response_group", "target_category"], \
        "record schema changed"
    with open(os.path.join(DATA, "area_profile.csv")) as fh:
        header = next(csv.reader(fh))
    assert header == ["area_id", "region", "urbanisation", "pct_aian_alone",
                      "pct_api_alone", "pct_black_alone", "pct_white_alone",
                      "pct_multiple_response"], "area schema changed"
    assert set(_question()["records_to_report"]) == set(by_id), \
        "question.json and response_records.csv disagree about the record set"
