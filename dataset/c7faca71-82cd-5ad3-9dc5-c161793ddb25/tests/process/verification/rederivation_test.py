"""Stage-7 re-derivation: the frozen goldens reproduce from the shipped bundle.

Runs from the bundle, wherever the bundle sits: every path is resolved relative
to this file, nothing is read from outside the bundle, and no argument is taken.
A module under this directory that read `sys.argv` would error at COLLECTION
under pytest and take the fixture matrix down with it.

Independence, stated plainly: this module re-derives through
`verifier/reg_reparse.py`, which parses the published regulation XML shipped at
`verifier/part117.xml` and answers every query by a different mechanism from the
oracle's hand transcription. It also re-reads the oracle's transcription and
asserts the two agree cell by cell, which is the check that a mistyped table
cannot survive. It never imports `oracle/solve.py`.

    python3 -m pytest verification/rederivation_test.py -q
"""
import csv
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(BUNDLE, "tests"))
sys.path.insert(0, os.path.join(BUNDLE, "solution"))

import reg_reparse as REG        # noqa: E402  the independent route
import part117_tables as ORACLE  # noqa: E402  the transcription under test

EXPECTED = json.load(open(os.path.join(BUNDLE, "tests", "expected_values.json")))
ITEMS = EXPECTED["items"]
REGULATION = REG.Regulation()


def _roster():
    path = os.path.join(BUNDLE, "environment", "data", "pairings.csv")
    with open(path) as fh:
        return {row["pairing_id"]: row for row in csv.DictReader(fh)}


ROSTER = _roster()


def _case_id(item):
    return "%s-%s" % (item["pairing"], item["field"])


@pytest.mark.parametrize("item", ITEMS, ids=[_case_id(i) for i in ITEMS])
def test_golden_reproduces_through_the_independent_route(item):
    row = ROSTER[item["pairing"]]
    code, margin = REGULATION.binding(row)
    got = {"fdp_margin_min": REGULATION.margins(row)["flight_duty_period"],
           "binding_limit": code,
           "binding_margin_min": margin}[item["field"]]
    if item["kind"] == "code":
        assert got == item["ref"]
    else:
        assert got == item["ref"], "%s: %r vs frozen %r" % (
            _case_id(item), got, item["ref"])


@pytest.mark.parametrize("table", ["A", "B", "C"])
def test_transcription_matches_the_published_bytes(table):
    """The oracle's hand transcription and the XML parse agree on every cell."""
    query = {"A": lambda m: (ORACLE.table_a(m), REGULATION.table_a_minutes(m)),
             "B": lambda m: (tuple(ORACLE.table_b(m, s) for s in range(1, 10)),
                             tuple(REGULATION.table_b_minutes(m, s)
                                   for s in range(1, 10))),
             "C": lambda m: (tuple(ORACLE.table_c(m, c, p)
                                   for c in (1, 2, 3) for p in (3, 4)),
                             tuple(REGULATION.table_c_minutes(m, c, p)
                                   for c in (1, 2, 3) for p in (3, 4)))}[table]
    for minute in range(1440):
        oracle_value, parsed_value = query(minute)
        assert oracle_value == parsed_value, \
            "table %s disagrees at minute %d: transcription %r, published %r" % (
                table, minute, oracle_value, parsed_value)


def test_section_limits_match_the_published_bytes():
    assert ORACLE.LIMITS == REGULATION.limits
    assert REGULATION.limits == REG.PUBLISHED_LIMITS


def test_no_pairing_ties_and_no_margin_is_zero():
    """The governing limit is well defined without invoking the tie-break rule,
    and no pairing sits exactly on a limit."""
    for pid, row in ROSTER.items():
        margins = sorted(REGULATION.margins(row).values())
        assert margins[0] != margins[1], "%s: two limits tie at %d" % (pid, margins[0])
        assert all(m != 0 for m in margins), "%s: a margin is exactly zero" % pid


def test_every_published_limit_governs_somewhere():
    governing = {REGULATION.binding(row)[0] for row in ROSTER.values()}
    assert governing == set(REG.LIMIT_CODES), \
        "limits that never govern: %s" % sorted(set(REG.LIMIT_CODES) - governing)


def test_ledger_separation_recomputes():
    """The recorded control-gap multiples are re-measured, not trusted.

    Only the two paths whose claim the separation argument rests on are
    recomputed here: the nearest real competitor must reproduce nothing, and the
    smallest recorded non-zero gap must be the smallest one actually observed.
    """
    flat = REGULATION.limits["split_combined_max_min"]
    reproduced = 0
    for item in ITEMS:
        row = ROSTER[item["pairing"]]
        m = REGULATION.margins(row)
        m["flight_duty_period"] += flat - REGULATION.max_fdp_minutes(row)
        best = min(REG.LIMIT_CODES,
                   key=lambda c: (m[c], REG.LIMIT_CODES.index(c)))
        got = {"fdp_margin_min": m["flight_duty_period"],
               "binding_limit": best,
               "binding_margin_min": m[best]}[item["field"]]
        if item["kind"] == "code":
            reproduced += got == item["ref"]
        else:
            reproduced += abs(got - item["ref"]) <= item["tolerance"]
    assert reproduced == 0, \
        "the nearest real competitor reproduces %d graded case(s)" % reproduced

    ledger = EXPECTED["control_gaps"]
    assert ledger["flat_14h_duty_day"]["graded_cases_reproduced"] == 0
    smallest = min(v for entry in ledger.values() for k, v in entry.items()
                   if k.endswith("_min_nonzero_gap_over_tol") and v > 0)
    assert abs(smallest - EXPECTED["smallest_wrong_path_gap_multiple"]) < 1e-09


def test_plausibility_envelope_holds_on_every_pairing():
    """Declared bounds.

    The two GRADED margins are bounded at half a day in size, because the
    largest published duty ceiling is under twenty hours and the smallest is
    nine, so anything larger is a unit slip or a dropped day-wrap. The remaining
    margins are slack against rolling ceilings measured over weeks, so their
    expected range is the width of those ceilings rather than of a duty period.
    """
    lo, hi = -720, 720
    for pid, row in ROSTER.items():
        margins = REGULATION.margins(row)
        binding_margin = REGULATION.binding(row)[1]
        for graded in (margins["flight_duty_period"], binding_margin):
            assert lo <= graded <= hi, "%s: graded margin %d is outside %d..%d" % (
                pid, graded, lo, hi)
        for code, margin in margins.items():
            assert -1440 <= margin <= REGULATION.limits["cumulative_fdp_672_max_min"], \
                "%s/%s = %d is outside the rolling-ceiling envelope" % (
                    pid, code, margin)
        elapsed = REGULATION.elapsed_minutes(row)
        assert 240 <= elapsed <= 1200, "%s: elapsed %d minutes" % (pid, elapsed)
        assert REG.hhmm_to_min(row["scheduled_flight_time"]) < elapsed


def test_task_md_placeholders_fail_every_graded_case():
    """6.7: every placeholder in the prompt must be obviously fake.

    Reads the shipped prompt, pulls every numeric literal and every quoted
    string out of the JSON shape example, and asserts that none of them would
    pass any graded case. An 'illustrative' placeholder that happens to be close
    has been copied straight into an answer before now.
    """
    import re
    with open(os.path.join(BUNDLE, "instruction.md")) as fh:
        body = fh.read().split("---", 2)[-1]
    fence = re.search(r"```json\n(.*?)```", body, re.S)
    assert fence, "the prompt no longer carries a JSON shape example"
    block = fence.group(1)

    numbers = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", block)]
    strings = re.findall(r'"([^"]+)"', block)
    assert numbers and strings, "the shape example carries no placeholders"

    for item in ITEMS:
        if item["kind"] == "margin":
            for n in numbers:
                assert abs(n - item["ref"]) > item["tolerance"], \
                    "placeholder %g passes %s" % (n, _case_id(item))
        else:
            for s in strings:
                assert s != item["ref"], "placeholder %r passes %s" % (s, _case_id(item))

    # the placeholder pairing key must not name a real pairing either
    assert not (set(strings) & set(ROSTER)), \
        "the shape example names a real pairing: %s" % sorted(set(strings) & set(ROSTER))
    # and every numeric literal anywhere in the prompt must miss every margin
    for n in (float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", body)):
        for item in ITEMS:
            if item["kind"] == "margin":
                assert abs(n - item["ref"]) > item["tolerance"], \
                    "the prompt states %g, which passes %s" % (n, _case_id(item))
