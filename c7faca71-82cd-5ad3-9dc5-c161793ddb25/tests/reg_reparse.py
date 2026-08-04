"""Verifier-side SECOND FORMULATION. Deliberately NOT the oracle's code.

The oracle carries a hand transcription of the three limit tables and of the
numeric limits stated in the section text, and it answers a query by scanning an
ordered list of clock ranges and subtracting the scheduled duty from the cell it
lands on.

This module shares none of that. It re-parses Tables A, B and C straight out of
the published `<GPOTABLE>` elements of the regulation XML shipped with this
bundle, re-reads every non-tabular limit out of the published section prose, and
answers the same queries through a different mechanism:

  * row selection is a 1440-entry minute-indexed array built from the published
    clock ranges, not a linear scan over tuples, so an off-by-one at a row
    boundary moves one route and not the other;
  * every duty-time margin is computed as a RELEASE DEADLINE in absolute clock
    minutes (report + allowance) differenced against the scheduled release,
    never as (maximum - scheduled duration).

A mistyped cell, a swapped row, an inverted boundary inequality or a dropped
adjustment therefore cannot agree with itself.  `validate_tables()` is a standing
tripwire on the parsed artifact itself: it asserts the shape, the tiling and the
published clock ranges of each table, so a mistranscribed source file cannot pass
silently either.

Source of the parsed bytes: US Government Publishing Office, GovInfo, annual
edition of the Code of Federal Regulations, 14 CFR part 117 (2023 edition),
https://www.govinfo.gov/content/pkg/CFR-2023-title14-vol3/xml/CFR-2023-title14-vol3-part117.xml
"""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
XML_PATH = os.environ.get("PART117_XML", os.path.join(HERE, "part117.xml"))

# ---------------------------------------------------------------------------
# Published clock ranges, as printed in the source document. These are the
# standing tripwire: if the shipped XML ever stops carrying exactly these row
# labels, in this order, every graded run fails loudly rather than quietly
# grading against a different table.
# ---------------------------------------------------------------------------
EXPECTED_ROWS_A = ("0000-0459", "0500-1959", "2000-2359")
EXPECTED_ROWS_B = ("0000-0359", "0400-0459", "0500-0559", "0600-0659",
                   "0700-1159", "1200-1259", "1300-1659", "1700-2159",
                   "2200-2259", "2300-2359")
EXPECTED_ROWS_C = ("0000-0559", "0600-0659", "0700-1259", "1300-1659",
                   "1700-2359")

# Table B is indexed by flight segments 1..6 and a final "7 +" column.
EXPECTED_B_COLS = 7
EXPECTED_C_COLS = 6      # (class 1, 2, 3) x (3 pilots, 4 pilots)
EXPECTED_A_COLS = 1

_DASH = re.compile(r"[‐-―−-]")


def _norm_range(text: str) -> str:
    return _DASH.sub("-", " ".join(text.split())).strip()


def _cell_minutes(text: str) -> int:
    """A published cell is an hour count, whole or half. Return whole minutes."""
    hours = float(" ".join(text.split()))
    minutes = hours * 60.0
    if abs(minutes - round(minutes)) > 1e-9:
        raise ValueError("cell %r is not a whole number of minutes" % text)
    return int(round(minutes))


def _range_bounds(label: str) -> tuple[int, int]:
    """'0500-0559' -> (300, 359), inclusive minute-of-day bounds."""
    m = re.fullmatch(r"(\d{2})(\d{2})-(\d{2})(\d{2})", _norm_range(label))
    if not m:
        raise ValueError("unparseable clock range %r" % label)
    h1, m1, h2, m2 = (int(g) for g in m.groups())
    return h1 * 60 + m1, h2 * 60 + m2


# ---------------------------------------------------------------------------
# XML parsing
# ---------------------------------------------------------------------------

def _read_xml() -> str:
    with open(XML_PATH, encoding="utf-8") as fh:
        return fh.read()


def _gpotables(raw: str) -> list[str]:
    return re.findall(r"<GPOTABLE.*?</GPOTABLE>", raw, re.S)


def _rows(table_xml: str) -> list[list[str]]:
    out = []
    for row in re.findall(r"<ROW>(.*?)</ROW>", table_xml, re.S):
        ents = re.findall(r"<ENT[^>]*>(.*?)</ENT>", row, re.S)
        out.append([" ".join(e.split()) for e in ents])
    return out


def _headings(table_xml: str) -> str:
    head = re.search(r"<BOXHD>(.*?)</BOXHD>", table_xml, re.S)
    if not head:
        return ""
    return " ".join(re.sub(r"<[^>]+>", " ", head.group(1)).split()).lower()


def parse_tables(xml_text: str | None = None) -> dict:
    """Every limit table, straight from the published GPOTABLE elements."""
    raw = xml_text if xml_text is not None else _read_xml()
    tables = {}
    for tbl in _gpotables(raw):
        head = _headings(tbl)
        rows = _rows(tbl)
        if "maximum flight time" in head:
            key = "A"
        elif "number of flight segments" in head:
            key = "B"
        elif "rest facility" in head:
            key = "C"
        else:
            continue
        parsed = []
        for row in rows:
            if not row:
                continue
            parsed.append((_norm_range(row[0]),
                           tuple(_cell_minutes(c) for c in row[1:])))
        if key in tables:
            raise ValueError("two GPOTABLEs claim to be table %s" % key)
        tables[key] = tuple(parsed)
    missing = [k for k in ("A", "B", "C") if k not in tables]
    if missing:
        raise ValueError("regulation XML is missing table(s): %s" % missing)
    return tables


# ---------------------------------------------------------------------------
# Standing tripwires on the parsed artifact
# ---------------------------------------------------------------------------

def _tiles_the_day(rows) -> None:
    cursor = 0
    for label, _ in rows:
        lo, hi = _range_bounds(label)
        if lo != cursor:
            raise ValueError("clock ranges do not tile the day: %r starts at "
                             "%d, expected %d" % (label, lo, cursor))
        if hi < lo:
            raise ValueError("clock range %r runs backwards" % label)
        cursor = hi + 1
    if cursor != 1440:
        raise ValueError("clock ranges cover %d minutes, expected 1440" % cursor)


def validate_tables(tables: dict) -> None:
    """Fail loudly on any drift in the shape, tiling or labels of the source."""
    shapes = {"A": (EXPECTED_ROWS_A, EXPECTED_A_COLS),
              "B": (EXPECTED_ROWS_B, EXPECTED_B_COLS),
              "C": (EXPECTED_ROWS_C, EXPECTED_C_COLS)}
    for key, (want_rows, want_cols) in shapes.items():
        rows = tables[key]
        got_rows = tuple(label for label, _ in rows)
        if got_rows != want_rows:
            raise ValueError("table %s row labels are %r, published order is %r"
                             % (key, got_rows, want_rows))
        for label, cells in rows:
            if len(cells) != want_cols:
                raise ValueError("table %s row %s has %d value columns, "
                                 "expected %d" % (key, label, len(cells),
                                                  want_cols))
            for c in cells:
                if c <= 0 or c % 30 != 0:
                    raise ValueError("table %s row %s carries %d minutes, "
                                     "which is not a positive half hour"
                                     % (key, label, c))
        _tiles_the_day(rows)

    # Table B must not increase as segments are added: more segments can only
    # shorten the permitted duty period. A transposed or shifted row breaks this.
    for label, cells in tables["B"]:
        for i in range(1, len(cells)):
            if cells[i] > cells[i - 1]:
                raise ValueError("table B row %s increases from %d to %d "
                                 "between segment columns %d and %d"
                                 % (label, cells[i - 1], cells[i], i, i + 1))

    # Augmentation can never shorten the permitted duty period: at every minute
    # of the day the smallest augmented cell must still exceed the largest
    # unaugmented one.
    b_idx = minute_index(tables["B"])
    c_idx = minute_index(tables["C"])
    for minute in range(1440):
        if min(c_idx[minute]) <= max(b_idx[minute]):
            raise ValueError("augmented table does not dominate the "
                             "unaugmented table at minute %d" % minute)


def minute_index(rows) -> list[tuple[int, ...]]:
    """1440-entry minute-of-day -> row cells array.

    This is the mechanism that replaces the oracle's ordered linear scan. Every
    minute is written exactly once; a gap or an overlap in the published clock
    ranges raises rather than silently resolving to a neighbouring row.
    """
    out: list[tuple[int, ...] | None] = [None] * 1440
    for label, cells in rows:
        lo, hi = _range_bounds(label)
        for minute in range(lo, hi + 1):
            if out[minute] is not None:
                raise ValueError("minute %d is claimed by two clock ranges"
                                 % minute)
            out[minute] = cells
    if any(v is None for v in out):
        raise ValueError("clock ranges leave at least one minute unassigned")
    return out  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Non-tabular limits, re-read from the published section prose
# ---------------------------------------------------------------------------

def _sections(raw: str) -> dict[str, str]:
    out = {}
    for block in re.findall(r"<SECTION>(.*?)</SECTION>", raw, re.S):
        num = re.search(r"<SECTNO>(.*?)</SECTNO>", block, re.S)
        if not num:
            continue
        label = re.sub(r"<[^>]+>", " ", num.group(1))
        label = label.replace("§", " ").strip()
        text = re.sub(r"<[^>]+>", " ", block)
        text = text.replace("–", "-").replace("—", "-")
        out[label] = " ".join(text.split())
    return out


def _one(pattern: str, text: str, what: str) -> str:
    hits = re.findall(pattern, text, re.I)
    if len(hits) != 1:
        raise ValueError("%s: expected exactly one match for %r, found %d"
                         % (what, pattern, len(hits)))
    return hits[0]


def parse_section_limits(xml_text: str | None = None) -> dict:
    """Every numeric limit this task grades, read out of the published prose.

    The oracle hard-codes the same numbers. If either transcription is wrong the
    two disagree and the run is gated to zero.
    """
    raw = xml_text if xml_text is not None else _read_xml()
    sec = _sections(raw)
    s11, s13, s15 = sec["117.11"], sec["117.13"], sec["117.15"]
    s17, s19, s23, s25 = sec["117.17"], sec["117.19"], sec["117.23"], sec["117.25"]

    three_pilot_h = _one(r"exceed (\d+) hours if the operation is conducted "
                         r"with a 3-pilot", s11, "117.11(a)(2)")
    four_pilot_h = _one(r"exceed (\d+) hours if the operation is conducted "
                        r"with a 4-pilot", s11, "117.11(a)(3)")
    unacclimated_b = _one(r"Table B of this part is reduced by (\d+) minutes",
                          s13, "117.13(b)(1)")
    unacclimated_c = _one(r"Table C of this part is reduced by (\d+) minutes",
                          s17, "117.17(b)(1)")
    rest_window = re.search(r"between the hours of (\d{2}):(\d{2}) and "
                            r"(\d{2}):(\d{2}) local time", s15, re.I)
    if not rest_window:
        raise ValueError("117.15(a): could not read the accommodation window")
    split_min_h = _one(r"suitable accommodation is at least (\d+) hours", s15,
                       "117.15(b)")
    split_combined_h = _one(r"rest opportunity provided in this section does "
                            r"not exceed (\d+) hours", s15, "117.15(f)")
    aug_segments = _one(r"assignment involving more than (three|\d+) flight "
                        r"segments", s17, "117.17(d)")
    extension_h = _one(r"permitted in Tables B or C of this part up to (\d+) "
                       r"hours", s19, "117.19(a)(1)")
    flight_672_h = _one(r"(\d+) hours in any 672 consecutive hours", s23,
                        "117.23(b)(1)")
    fdp_168_h = _one(r"(\d+) flight duty period hours in any 168 consecutive "
                     r"hours", s23, "117.23(c)(1)")
    fdp_672_h = _one(r"(\d+) flight duty period hours in any 672 consecutive "
                     r"hours", s23, "117.23(c)(2)")
    free_h = _one(r"at least (\d+) consecutive hours free from all duty within "
                  r"the past 168 consecutive hour period", s25, "117.25(b)")
    rest_before_h = _one(r"rest period of at least (\d+) consecutive hours "
                         r"immediately before", s25, "117.25(e)")

    words = {"three": 3, "four": 4}
    return {
        "three_pilot_flight_time_max_min": int(three_pilot_h) * 60,
        "four_pilot_flight_time_max_min": int(four_pilot_h) * 60,
        "unacclimated_reduction_min": int(unacclimated_b),
        "unacclimated_reduction_augmented_min": int(unacclimated_c),
        "accommodation_window_start_min": (int(rest_window.group(1)) * 60
                                           + int(rest_window.group(2))),
        "accommodation_window_end_min": (int(rest_window.group(3)) * 60
                                         + int(rest_window.group(4))),
        "split_min_accommodation_min": int(split_min_h) * 60,
        "split_combined_max_min": int(split_combined_h) * 60,
        "augmented_max_segments": words.get(aug_segments, None)
        if not aug_segments.isdigit() else int(aug_segments),
        "unforeseen_extension_max_min": int(extension_h) * 60,
        "cumulative_flight_672_max_min": int(flight_672_h) * 60,
        "cumulative_fdp_168_max_min": int(fdp_168_h) * 60,
        "cumulative_fdp_672_max_min": int(fdp_672_h) * 60,
        "free_period_168_min_min": int(free_h) * 60,
        "rest_before_duty_min_min": int(rest_before_h) * 60,
    }


# Published values, held here as a standing tripwire on the parse itself so that
# a regex that silently starts matching the wrong sentence cannot change what is
# graded. Each is quoted from 14 CFR part 117 (2023 edition) at the section shown.
PUBLISHED_LIMITS = {
    "three_pilot_flight_time_max_min": 780,          # 117.11(a)(2), 13 hours
    "four_pilot_flight_time_max_min": 1020,          # 117.11(a)(3), 17 hours
    "unacclimated_reduction_min": 30,                # 117.13(b)(1)
    "unacclimated_reduction_augmented_min": 30,      # 117.17(b)(1)
    "accommodation_window_start_min": 1320,          # 117.15(a), 22:00
    "accommodation_window_end_min": 300,             # 117.15(a), 05:00
    "split_min_accommodation_min": 180,              # 117.15(b), 3 hours
    "split_combined_max_min": 840,                   # 117.15(f), 14 hours
    "augmented_max_segments": 3,                     # 117.17(d)
    "unforeseen_extension_max_min": 120,             # 117.19(a)(1), 2 hours
    "cumulative_flight_672_max_min": 6000,           # 117.23(b)(1), 100 hours
    "cumulative_fdp_168_max_min": 3600,              # 117.23(c)(1), 60 hours
    "cumulative_fdp_672_max_min": 11400,             # 117.23(c)(2), 190 hours
    "free_period_168_min_min": 1800,                 # 117.25(b), 30 hours
    "rest_before_duty_min_min": 600,                 # 117.25(e), 10 hours
}


# ---------------------------------------------------------------------------
# Derivation, through the deadline formulation
# ---------------------------------------------------------------------------

LIMIT_CODES = (
    "flight_duty_period",
    "flight_time",
    "rest_before_duty",
    "free_period_168h",
    "cumulative_fdp_168h",
    "cumulative_fdp_672h",
    "cumulative_flight_672h",
)


def hhmm_to_min(text: str) -> int:
    m = re.fullmatch(r"(\d{1,3}):([0-5]\d)", str(text).strip())
    if not m:
        raise ValueError("not an h:mm duration or clock time: %r" % (text,))
    return int(m.group(1)) * 60 + int(m.group(2))


class Regulation:
    """One immutable view of the published limits, built from the shipped XML."""

    def __init__(self, xml_text: str | None = None):
        raw = xml_text if xml_text is not None else _read_xml()
        self.tables = parse_tables(raw)
        validate_tables(self.tables)
        self.limits = parse_section_limits(raw)
        self._a = minute_index(self.tables["A"])
        self._b = minute_index(self.tables["B"])
        self._c = minute_index(self.tables["C"])

    # -- table queries -----------------------------------------------------
    def table_a_minutes(self, report_min: int) -> int:
        return self._a[report_min % 1440][0]

    def table_b_minutes(self, report_min: int, segments: int) -> int:
        if segments < 1:
            raise ValueError("a pairing has at least one flight segment")
        col = min(segments, EXPECTED_B_COLS) - 1
        return self._b[report_min % 1440][col]

    def table_c_minutes(self, report_min: int, facility_class: int,
                        pilots: int) -> int:
        if facility_class not in (1, 2, 3) or pilots not in (3, 4):
            raise ValueError("augmented lookup needs a rest facility class "
                             "1-3 and 3 or 4 pilots")
        col = (facility_class - 1) * 2 + (pilots - 3)
        return self._c[report_min % 1440][col]

    # -- pairing derivation ------------------------------------------------
    def accommodation_relief_minutes(self, p: dict) -> int:
        """Minutes excluded from the duty period under the split-duty section.

        Every published condition must hold; any one failing leaves the whole
        elapsed period on duty.
        """
        start, end = p["rest_opportunity_start"], p["rest_opportunity_end"]
        if not start or not end:
            return 0
        if int(p["pilots_assigned"]) != 2:
            return 0                   # unaugmented operations only
        if p["rest_opportunity_accommodation"] != "suitable":
            return 0
        if p["rest_opportunity_after_first_segment"] != "yes":
            return 0
        s, e = hhmm_to_min(start), hhmm_to_min(end)
        duration = (e - s) % 1440
        if duration < self.limits["split_min_accommodation_min"]:
            return 0
        # The window 22:00 -> 05:00 wraps midnight; walk it minute by minute
        # rather than comparing endpoints, so a rest that straddles either edge
        # is rejected for the right reason.
        w_start = self.limits["accommodation_window_start_min"]
        w_end = self.limits["accommodation_window_end_min"]
        allowed = set()
        minute = w_start
        while True:
            allowed.add(minute % 1440)
            if minute % 1440 == w_end:
                break
            minute += 1
        for offset in range(duration + 1):
            if (s + offset) % 1440 not in allowed:
                return 0
        if self.elapsed_minutes(p) > self.limits["split_combined_max_min"]:
            return 0
        return duration

    def elapsed_minutes(self, p: dict) -> int:
        report = hhmm_to_min(p["report_local"])
        release = hhmm_to_min(p["release_local"])
        span = (release - report) % 1440
        return span if span else 1440

    def max_fdp_minutes(self, p: dict) -> int:
        report = hhmm_to_min(p["report_local"])
        if int(p["pilots_assigned"]) == 2:
            base = self.table_b_minutes(report, int(p["segments"]))
            cut = self.limits["unacclimated_reduction_min"]
        else:
            facility = p["onboard_rest_facility"]
            if not facility.startswith("class_"):
                raise ValueError("an augmented pairing needs a rest facility")
            base = self.table_c_minutes(report, int(facility[-1]),
                                        int(p["pilots_assigned"]))
            cut = self.limits["unacclimated_reduction_augmented_min"]
        return base - (0 if p["acclimated"] == "yes" else cut)

    def max_flight_minutes(self, p: dict) -> int:
        pilots = int(p["pilots_assigned"])
        if pilots == 2:
            return self.table_a_minutes(hhmm_to_min(p["report_local"]))
        if pilots == 3:
            return self.limits["three_pilot_flight_time_max_min"]
        if pilots == 4:
            return self.limits["four_pilot_flight_time_max_min"]
        raise ValueError("unsupported flightcrew size %r" % pilots)

    def margins(self, p: dict) -> dict[str, int]:
        """Every graded margin, in minutes, by the deadline formulation.

        The three duty-time limits are expressed as the latest clock minute the
        pairing may be released at, differenced against the scheduled release.
        Nothing here forms the quantity `maximum - scheduled duration`.
        """
        report = hhmm_to_min(p["report_local"])
        release_abs = report + self.elapsed_minutes(p)
        relief = self.accommodation_relief_minutes(p)
        lim = self.limits

        deadlines = {
            "flight_duty_period": report + self.max_fdp_minutes(p) + relief,
            "cumulative_fdp_168h": (
                report + (lim["cumulative_fdp_168_max_min"]
                          - hhmm_to_min(p["prior_fdp_rolling_7d"])) + relief),
            "cumulative_fdp_672h": (
                report + (lim["cumulative_fdp_672_max_min"]
                          - hhmm_to_min(p["prior_fdp_rolling_28d"])) + relief),
        }
        out = {code: deadline - release_abs for code, deadline in deadlines.items()}
        out["flight_time"] = (self.max_flight_minutes(p)
                              - hhmm_to_min(p["scheduled_flight_time"]))
        out["rest_before_duty"] = (hhmm_to_min(p["rest_before_duty"])
                                   - lim["rest_before_duty_min_min"])
        out["free_period_168h"] = (hhmm_to_min(p["longest_free_period_prior_7d"])
                                   - lim["free_period_168_min_min"])
        out["cumulative_flight_672h"] = (
            lim["cumulative_flight_672_max_min"]
            - hhmm_to_min(p["prior_flight_rolling_28d"])
            - hhmm_to_min(p["scheduled_flight_time"]))
        if set(out) != set(LIMIT_CODES):
            raise ValueError("margin set does not cover the published limits")
        return out

    def binding(self, p: dict) -> tuple[str, int]:
        """(code, margin) of the limit with the smallest margin.

        Ties resolve to the first code in the published order, which is the rule
        the task states. The instance is built so no tie occurs; the process
        verifier asserts that separately.
        """
        m = self.margins(p)
        best = min(LIMIT_CODES, key=lambda code: (m[code], LIMIT_CODES.index(code)))
        return best, m[best]
