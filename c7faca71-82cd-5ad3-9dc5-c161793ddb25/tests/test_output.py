"""Outcome verifier for flight-duty-period-legality.

Deterministic. Grades /root/results.json against the frozen reference. The scored
tests are test_graded_case[...]; everything below the divider is a grader
self-check and is excluded from the reward by test.sh, which also GATES on them.

Section 6.1 compliance: this module never imports the oracle's transcription. It
re-derives every graded figure through `reg_reparse`, which is an INDEPENDENT
second formulation - it parses the three limit tables and every non-tabular limit
straight out of the published regulation XML shipped in this directory, selects
the applicable row through a 1440-entry minute index rather than the oracle's
ordered scan, and expresses every duty-time margin as a release deadline in
absolute clock minutes rather than as a maximum minus a duration. A mistyped
cell, a swapped row band or an inverted boundary therefore cannot agree with
itself.

`test_published_tables_are_intact` is a standing tripwire on the parsed artifact
itself, so a mistranscribed source file cannot pass silently either. Neither
check can be skipped: an unreadable or absent XML source is a hard failure and
test.sh scores the run zero.
"""

import copy
import csv
import json
import math
import os
import re
import sys

import pytest

VER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, VER)
import reg_reparse as REG  # noqa: E402

EXP = json.load(open(os.path.join(VER, "expected_values.json")))
ITEMS = EXP["items"]
DATA = os.environ.get("DATA_DIR", "/root/data")
RESULTS_PATH = os.environ.get("RESULTS_PATH", "/root/results.json")
CODES = tuple(EXP["limit_codes"])

# One regulation object for the whole session. Constructing it validates the
# tables, so an unusable source file fails every test rather than one.
REGULATION = REG.Regulation()


def _case_id(item):
    return "%s-%s" % (item["pairing"], item["field"])


def _roster():
    path = os.path.join(DATA, "pairings.csv")
    assert os.path.isfile(path), "%s is missing" % path
    with open(path) as fh:
        return {row["pairing_id"]: row for row in csv.DictReader(fh)}


def _live_reference(roster=None):
    """Every graded figure, re-derived through the second formulation."""
    roster = roster if roster is not None else _roster()
    out = {}
    for pid, row in roster.items():
        code, margin = REGULATION.binding(row)
        out[pid] = {
            "fdp_margin_min": REGULATION.margins(row)["flight_duty_period"],
            "binding_limit": code,
            "binding_margin_min": margin,
        }
    return out


def _load_results():
    assert os.path.isfile(RESULTS_PATH), "%s does not exist" % RESULTS_PATH
    try:
        with open(RESULTS_PATH) as fh:
            data = json.load(fh)
    except Exception as exc:
        pytest.fail("results.json is not valid JSON: %s" % exc)
    assert isinstance(data, dict), "results.json must be a JSON object"
    return data


def _fetch(results, item):
    pid, field = item["pairing"], item["field"]
    assert pid in results, "%s is missing from results.json" % pid
    node = results[pid]
    assert isinstance(node, dict), "%s must map to an object" % pid
    assert field in node, "%s is missing %r" % (pid, field)
    return node[field]


@pytest.mark.parametrize("item", ITEMS, ids=[_case_id(i) for i in ITEMS])
def test_graded_case(item):
    results = _load_results()
    value = _fetch(results, item)
    if item["kind"] == "code":
        assert isinstance(value, str), "%s must be a string" % _case_id(item)
        assert value.strip() == item["ref"], \
            "%s: got %r, expected %r" % (_case_id(item), value, item["ref"])
        return
    assert isinstance(value, (int, float)) and not isinstance(value, bool), \
        "%s must be a number" % _case_id(item)
    got = float(value)
    assert not math.isnan(got) and not math.isinf(got), \
        "%s must be finite" % _case_id(item)
    assert abs(got - item["ref"]) <= item["tolerance"], \
        "%s: got %.3f, expected %.3f (tol %.3f)" % (
            _case_id(item), got, item["ref"], item["tolerance"])


# ---- grader self-checks (NOT scored; test.sh GATES the run on them) ---------

def test_frozen_reference_matches_independent_recompute():
    """The stored goldens reproduce through the second formulation, which shares
    neither its constants nor its arithmetic with the oracle."""
    live = _live_reference()
    for item in ITEMS:
        got = live[item["pairing"]][item["field"]]
        ref = item["ref"]
        if item["kind"] == "code":
            assert got == ref, "freeze drift at %s: %r vs %r" % (
                _case_id(item), got, ref)
        else:
            assert abs(float(got) - float(ref)) <= 1e-09, \
                "freeze drift at %s: %r vs %r" % (_case_id(item), got, ref)


def test_published_tables_are_intact():
    """Standing tripwire on the shipped regulation source itself.

    The three tables must have the published shape, the published clock ranges
    and the published tiling of the day, and the section limits parsed out of the
    prose must equal the values quoted from the published text. A mistranscribed
    cell or a shifted row band cannot pass this quietly.
    """
    path = os.path.join(VER, "part117.xml")
    assert os.path.isfile(path), \
        "the regulation source is missing - the independent route cannot be skipped"
    tables = REG.parse_tables()
    REG.validate_tables(tables)

    assert tuple(label for label, _ in tables["B"]) == REG.EXPECTED_ROWS_B
    assert len(tables["B"]) == 10, "the unaugmented matrix must have ten rows"
    for label, cells in tables["B"]:
        assert len(cells) == REG.EXPECTED_B_COLS == 7, \
            "row %s does not carry seven segment columns" % label
    assert len(tables["A"]) == 3 and len(tables["C"]) == 5
    for label, cells in tables["C"]:
        assert len(cells) == REG.EXPECTED_C_COLS == 6

    limits = REG.parse_section_limits()
    assert limits == REG.PUBLISHED_LIMITS, \
        "a limit read from the section prose does not match the published value"


def test_two_row_bands_are_not_interchangeable():
    """The augmented and unaugmented matrices do not share row boundaries.

    This is the property that makes carrying one index across to the other table
    a silent error, and it is asserted rather than assumed because the whole
    separation argument rests on the two tables being genuinely different objects.
    """
    b_bands = {label for label, _ in REGULATION.tables["B"]}
    c_bands = {label for label, _ in REGULATION.tables["C"]}
    assert b_bands != c_bands
    disagreeing = sum(
        1 for minute in range(1440)
        if REGULATION.table_b_minutes(minute, 3)
        != REGULATION.table_c_minutes(minute, 3, 3))
    assert disagreeing == 1440, \
        "the two matrices agree somewhere; they are meant to be disjoint regimes"


def test_plausibility_envelope():
    """Every golden sits inside the domain-plausible range, and the roster it is
    computed from sits inside its own.

    A duty-period margin cannot be larger in size than the largest published
    ceiling, and the scheduled quantities cannot be outside what a lawful roster
    could ever contain. This is the check that catches a unit slip - minutes
    read as hours, or a day-wrap dropped - which is the most common way a
    reference of this shape goes wrong.
    """
    lo, hi = -12 * 60, 12 * 60
    for item in ITEMS:
        if item["kind"] != "margin":
            continue
        x = item["ref"]
        assert lo <= x <= hi, \
            "%s = %s is outside the plausible envelope %d..%d minutes" % (
                _case_id(item), x, lo, hi)
        assert x != 0, "%s sits exactly on its limit" % _case_id(item)
    for item in ITEMS:
        if item["kind"] == "code":
            assert item["ref"] in CODES, "%s names an unknown limit" % _case_id(item)

    roster = _roster()
    assert len(roster) == EXP["n_pairings"] == 17
    for pid, row in roster.items():
        elapsed = REGULATION.elapsed_minutes(row)
        assert 4 * 60 <= elapsed <= 20 * 60, \
            "%s: %d minutes from report to release is not a pairing" % (pid, elapsed)
        flight = REG.hhmm_to_min(row["scheduled_flight_time"])
        assert 0 < flight < elapsed, "%s: flight time does not sit inside duty" % pid
        assert 8 * 60 <= REG.hhmm_to_min(row["rest_before_duty"]) <= 30 * 60
        assert 1 <= int(row["segments"]) <= 9
        assert int(row["pilots_assigned"]) in (2, 3, 4)


def test_nearest_competitor_reproduces_no_graded_case():
    """The nearest real competing method - a flat fourteen-hour duty day in place
    of the matrix, with every other limit enumerated and applied correctly - must
    reproduce none of the graded figures.

    Recomputed live here rather than read from the ledger, so the separation
    claim is re-measured on every graded run.
    """
    flat = REGULATION.limits["split_combined_max_min"]
    roster = _roster()
    hits = []
    for item in ITEMS:
        row = roster[item["pairing"]]
        m = REGULATION.margins(row)
        m["flight_duty_period"] += flat - REGULATION.max_fdp_minutes(row)
        best = min(CODES, key=lambda c: (m[c], CODES.index(c)))
        got = {"fdp_margin_min": m["flight_duty_period"],
               "binding_limit": best,
               "binding_margin_min": m[best]}[item["field"]]
        if item["kind"] == "code":
            if got == item["ref"]:
                hits.append(_case_id(item))
        elif abs(got - item["ref"]) <= item["tolerance"]:
            hits.append(_case_id(item))
    assert not hits, "the flat-duty-day route reproduces %d graded case(s): %s" % (
        len(hits), ", ".join(hits[:10]))


def test_guess_resistance_and_decoy_freedom():
    """No constant answer, and nothing copied straight out of the input, scores.

    The naive routes checked here are: a fixed margin; the elapsed duty period
    echoed back; and every published cell of the matrix offered as a margin.
    """
    for guess in list(range(-180, 181, 30)) + [600, 840]:
        hits = sum(1 for item in ITEMS if item["kind"] == "margin"
                   and abs(guess - item["ref"]) <= item["tolerance"])
        assert hits == 0, "the constant %d passes %d graded margin(s)" % (guess, hits)

    roster = _roster()
    echoed = 0
    for item in ITEMS:
        if item["kind"] != "margin":
            continue
        row = roster[item["pairing"]]
        for candidate in (REGULATION.elapsed_minutes(row),
                          REG.hhmm_to_min(row["scheduled_flight_time"]),
                          REG.hhmm_to_min(row["rest_before_duty"])):
            if abs(candidate - item["ref"]) <= item["tolerance"]:
                echoed += 1
    assert echoed == 0, "a quantity copied from the roster passes %d case(s)" % echoed

    cells = {c for _, row in REGULATION.tables["B"] for c in row}
    cells |= {c for _, row in REGULATION.tables["C"] for c in row}
    published_hits = sum(1 for item in ITEMS if item["kind"] == "margin"
                         for c in cells
                         if abs(c - item["ref"]) <= item["tolerance"])
    assert published_hits == 0, \
        "a published cell offered as a margin passes %d case(s)" % published_hits

    floors = EXP["constant_answer_floors"]
    best_name = max(floors, key=lambda k: floors[k])
    assert floors[best_name] <= len(ITEMS) // 4, (
        "a constant answer collects %d of %d graded cases, which is above the "
        "quarter-of-the-set ceiling this instance is built to" % (
            floors[best_name], len(ITEMS)))


def test_isomorphic_invariance_under_clock_relabel():
    """V-09: the reference is a property of the roster, not of memorised values.

    Shift a pairing's report and release by the same amount, small enough that
    the report time stays inside its own published clock band on every table it
    touches. Every margin must be exactly preserved, because nothing in the
    derivation depends on the clock except through the band a report time falls
    in. A verifier keyed to remembered surface numbers would not survive this;
    one that re-derives does.

    Pairings carrying a scheduled accommodation rest are excluded on purpose:
    the window that rest must fall inside is an absolute clock window, so the
    identity genuinely does not hold for them and asserting it would be wrong.
    """
    roster = _roster()
    tested = 0
    for pid, row in roster.items():
        if row["rest_opportunity_start"]:
            continue
        report = REG.hhmm_to_min(row["report_local"])
        band = _band_end(REGULATION.tables["A"], report)
        if int(row["pilots_assigned"]) == 2:
            band = min(band, _band_end(REGULATION.tables["B"], report))
        else:
            band = min(band, _band_end(REGULATION.tables["C"], report))
        delta = min(7, band - report)
        if delta <= 0:
            continue
        moved = copy.deepcopy(row)
        moved["report_local"] = "%02d:%02d" % (((report + delta) // 60) % 24,
                                               (report + delta) % 60)
        release = REG.hhmm_to_min(row["release_local"]) + delta
        moved["release_local"] = "%02d:%02d" % ((release // 60) % 24, release % 60)
        before, after = REGULATION.margins(row), REGULATION.margins(moved)
        for code in CODES:
            assert abs(before[code] - after[code]) <= 1e-09, \
                "%s: shifting the clock by %d minutes moved the %s margin" % (
                    pid, delta, code)
        tested += 1
    assert tested >= 10, "the relabel control exercised only %d pairings" % tested


def _band_end(rows, minute):
    for label, _ in rows:
        lo, hi = REG._range_bounds(label)
        if lo <= minute <= hi:
            return hi
    raise AssertionError("no published band covers minute %d" % minute)


def test_tolerances_bind_and_the_ledger_is_arithmetically_sound():
    assert len(ITEMS) == EXP["n_cases"] == 51
    seen = set()
    for item in ITEMS:
        seen.add(_case_id(item))
        if item["kind"] == "margin":
            assert item["tolerance"] > 0, "non-positive tolerance"
            assert math.isfinite(item["ref"])
    assert len(seen) == len(ITEMS), "duplicate case ids"

    band = EXP["published_precision_ambiguity_margin_maxabs"]
    tol = EXP["tolerance_fdp_margin_min_abs"]
    assert band < tol, "a faithful reading of the cited edition would false-fail"
    assert EXP["smallest_wrong_path_gap_multiple"] > 2.0, \
        "a competing method sits inside twice the tolerance"

    ledger = EXP["control_gaps"]
    nearest = [k for k, v in ledger.items() if v.get("nearest_real_competitor")]
    assert nearest, "no nearest real competitor is recorded"
    for name in nearest:
        assert ledger[name]["graded_cases_reproduced"] == 0, \
            "%s is recorded as the nearest competitor and reproduces cases" % name
    for name, entry in ledger.items():
        assert entry.get("note"), "%s has no note naming what it is" % name
        best = max(entry["fdp_margin_gap_over_tol"],
                   entry["binding_margin_gap_over_tol"])
        assert best >= 2.0, \
            "%s separates by only %.2f tolerances at its widest" % (name, best)

    # every pairing is graded on all three figures, and the count is prime
    n = EXP["n_pairings"]
    assert all(n % d for d in range(2, n)), "the pairing count is not prime"
    assert len(ITEMS) == 3 * n
    assert set(EXP["binding_limit_by_pairing"].values()) == set(CODES), \
        "the graded set does not exercise every published limit"


def test_degenerate_submissions_score_zero_without_crashing():
    """Malformed answers must fail as failures, never as verifier errors."""
    for payload in ({}, {"P01": "PASSED"}, {"P01": {"fdp_margin_min": "x"}},
                    {"P01": {"fdp_margin_min": float("nan"),
                             "binding_limit": 1,
                             "binding_margin_min": None}}):
        for item in ITEMS[:3]:
            try:
                value = _fetch(payload, item)
                if item["kind"] == "code":
                    assert isinstance(value, str) and value.strip() == item["ref"]
                else:
                    assert isinstance(value, (int, float)) \
                        and not isinstance(value, bool)
                    assert math.isfinite(float(value))
                    assert abs(float(value) - item["ref"]) <= item["tolerance"]
            except AssertionError:
                continue
            except Exception as exc:  # pragma: no cover - this is the defect
                pytest.fail("degenerate payload raised %s instead of failing: %s"
                            % (type(exc).__name__, exc))
            else:
                pytest.fail("a degenerate payload passed %s" % _case_id(item))


def test_roster_carries_no_compliance_label():
    """The lever survives only while no pairing is labelled.

    A single labelled pairing would pin the cell its report time and segment
    count select from one side, and a handful would bracket the table. The
    roster must therefore carry no verdict, no margin and no ceiling.
    """
    with open(os.path.join(DATA, "pairings.csv")) as fh:
        header = fh.readline().strip().split(",")
    banned = re.compile(r"legal|complian|violat|margin|maximum|max_|limit|exceed",
                        re.I)
    offending = [c for c in header if banned.search(c)]
    assert not offending, "the roster carries labelling column(s): %s" % offending

    with open(os.path.join(DATA, "pairings.csv")) as fh:
        body = fh.read()
    for item in ITEMS:
        if item["kind"] != "margin":
            continue
        for form in ("%.1f" % item["ref"], "%.2f" % item["ref"]):
            assert form not in body, \
                "%s is readable as a literal from the roster" % _case_id(item)
