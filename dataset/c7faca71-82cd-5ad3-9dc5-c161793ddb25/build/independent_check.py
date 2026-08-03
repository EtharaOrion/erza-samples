"""Supplementary independent recompute, runnable from the shipped bundle.

This is a SUPPLEMENT, never the anchor. The anchor is inside the verifier, where
it runs on every graded run and cannot rot:
`verifier/test_outputs.py::test_frozen_reference_matches_independent_recompute`
and `::test_published_tables_are_intact`. This script exists so a reviewer can
reproduce the same claim from a fresh clone in one command.

Everything it reads is inside the bundle. Paths resolve relative to the bundle
root only, so it works from `harness/tasks/<slug>/` and from `dataset/<uuid>/`
alike. Nothing is fetched, and no route can silently skip: a missing regulation
source is a non-zero exit, not a SKIP.

What it re-derives, and how it is independent:

  * the three limit tables and the fifteen non-tabular limits come from parsing
    the published `<GPOTABLE>` elements and section prose of
    `verifier/part117.xml` - not from the oracle's hand transcription;
  * every margin is formed as a release deadline in absolute clock minutes, not
    as (maximum - scheduled duration);
  * the oracle's transcription is then compared against the parse, cell by cell,
    over every minute of the day.

    python3 build/independent_check.py     # exit 0 when everything reproduces
"""
from __future__ import annotations

import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "solution"))

import reg_reparse as REG        # noqa: E402
import part117_tables as ORACLE  # noqa: E402


def main() -> int:
    xml_path = os.path.join(ROOT, "tests", "part117.xml")
    if not os.path.isfile(xml_path):
        print("FAIL: %s is missing; the independent route cannot run" % xml_path)
        return 2

    reg = REG.Regulation()               # constructing it validates the tables
    problems: list[str] = []

    if reg.limits != REG.PUBLISHED_LIMITS:
        problems.append("parsed section limits differ from the published values")
    if ORACLE.LIMITS != reg.limits:
        problems.append("the oracle's transcription differs from the parse")

    cells = 0
    for minute in range(1440):
        if ORACLE.table_a(minute) != reg.table_a_minutes(minute):
            problems.append("table A disagrees at minute %d" % minute)
        cells += 1
        for seg in range(1, 10):
            if ORACLE.table_b(minute, seg) != reg.table_b_minutes(minute, seg):
                problems.append("table B disagrees at minute %d segment %d"
                                % (minute, seg))
            cells += 1
        for cls in (1, 2, 3):
            for pilots in (3, 4):
                if ORACLE.table_c(minute, cls, pilots) != \
                        reg.table_c_minutes(minute, cls, pilots):
                    problems.append("table C disagrees at minute %d class %d "
                                    "pilots %d" % (minute, cls, pilots))
                cells += 1

    with open(os.path.join(ROOT, "tests", "expected_values.json")) as fh:
        expected = json.load(fh)
    with open(os.path.join(ROOT, "environment", "data", "pairings.csv")) as fh:
        roster = {row["pairing_id"]: row for row in csv.DictReader(fh)}

    worst = 0
    for item in expected["items"]:
        row = roster[item["pairing"]]
        code, margin = reg.binding(row)
        got = {"fdp_margin_min": reg.margins(row)["flight_duty_period"],
               "binding_limit": code,
               "binding_margin_min": margin}[item["field"]]
        if item["kind"] == "code":
            if got != item["ref"]:
                problems.append("%s/%s: %r vs frozen %r"
                                % (item["pairing"], item["field"], got, item["ref"]))
        else:
            worst = max(worst, abs(got - item["ref"]))
            if got != item["ref"]:
                problems.append("%s/%s: %r vs frozen %r"
                                % (item["pairing"], item["field"], got, item["ref"]))

    # plausibility envelope: a graded margin larger than half a day means a unit
    # slip or a dropped day-wrap, the two ways a reference of this shape breaks
    lo, hi = -720, 720
    for item in expected["items"]:
        if item["kind"] == "margin" and not lo <= item["ref"] <= hi:
            problems.append("%s/%s = %s outside the plausible range %d..%d"
                            % (item["pairing"], item["field"], item["ref"], lo, hi))

    if problems:
        print("INDEPENDENT CHECK FAILED")
        for p in problems[:20]:
            print("  " + p)
        return 1

    print("independent check OK")
    print("  table cells compared      : %d" % cells)
    print("  section limits compared   : %d" % len(reg.limits))
    print("  graded figures reproduced : %d" % len(expected["items"]))
    print("  worst disagreement        : %d minute(s)" % worst)
    print("  plausibility envelope     : %d <= margin <= %d, all inside" % (lo, hi))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
