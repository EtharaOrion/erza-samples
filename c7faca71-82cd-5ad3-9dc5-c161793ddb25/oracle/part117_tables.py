"""Reference transcription of the published flight-and-duty limits.

Transcribed by hand from the annual edition of the Code of Federal Regulations,
14 CFR part 117 (2023 edition), published by the US Government Publishing Office
on GovInfo:
https://www.govinfo.gov/content/pkg/CFR-2023-title14-vol3/xml/CFR-2023-title14-vol3-part117.xml

Table A  - maximum flight time, unaugmented operations, by report time.
Table B  - maximum flight duty period, unaugmented, by report time x segments.
Table C  - maximum flight duty period, augmented, by report time x rest facility
           class x number of pilots.

This module is the ORACLE'S transcription and its lookup mechanism is an ordered
linear scan over clock ranges. The verifier deliberately does NOT import it: it
re-parses the same three tables and every non-tabular limit out of the shipped
regulation XML through a different code path, so a typo here cannot agree with
itself. See verifier/reg_reparse.py.

All durations are held in whole minutes.
"""

H = 60

# ---- Table A: (start "hhmm", end "hhmm", maximum flight time) --------------
TABLE_A = (
    ("0000", "0459", 8 * H),
    ("0500", "1959", 9 * H),
    ("2000", "2359", 8 * H),
)

# ---- Table B: (start, end, per-segment maxima for 1, 2, 3, 4, 5, 6, 7+) ----
TABLE_B = (
    ("0000", "0359", (9 * H, 9 * H, 9 * H, 9 * H, 9 * H, 9 * H, 9 * H)),
    ("0400", "0459", (10 * H, 10 * H, 10 * H, 10 * H, 9 * H, 9 * H, 9 * H)),
    ("0500", "0559", (12 * H, 12 * H, 12 * H, 12 * H, 690, 11 * H, 630)),
    ("0600", "0659", (13 * H, 13 * H, 12 * H, 12 * H, 690, 11 * H, 630)),
    ("0700", "1159", (14 * H, 14 * H, 13 * H, 13 * H, 750, 12 * H, 690)),
    ("1200", "1259", (13 * H, 13 * H, 13 * H, 13 * H, 750, 12 * H, 690)),
    ("1300", "1659", (12 * H, 12 * H, 12 * H, 12 * H, 690, 11 * H, 630)),
    ("1700", "2159", (12 * H, 12 * H, 11 * H, 11 * H, 10 * H, 9 * H, 9 * H)),
    ("2200", "2259", (11 * H, 11 * H, 10 * H, 10 * H, 9 * H, 9 * H, 9 * H)),
    ("2300", "2359", (10 * H, 10 * H, 10 * H, 9 * H, 9 * H, 9 * H, 9 * H)),
)

# ---- Table C: (start, end, (c1/3p, c1/4p, c2/3p, c2/4p, c3/3p, c3/4p)) -----
TABLE_C = (
    ("0000", "0559", (15 * H, 17 * H, 14 * H, 930, 13 * H, 810)),
    ("0600", "0659", (16 * H, 1110, 15 * H, 990, 14 * H, 870)),
    ("0700", "1259", (17 * H, 1140, 990, 18 * H, 15 * H, 930)),
    ("1300", "1659", (16 * H, 1110, 15 * H, 990, 14 * H, 870)),
    ("1700", "2359", (15 * H, 17 * H, 14 * H, 930, 13 * H, 810)),
)

# ---- Limits stated in the section prose rather than in a table -------------
# 117.11(a)(2)-(3), 117.13(b)(1), 117.15(a)(b)(f), 117.17(b)(1)(d),
# 117.19(a)(1), 117.23(b)(1)(c)(1)(2), 117.25(b)(e).
LIMITS = {
    "three_pilot_flight_time_max_min": 13 * H,
    "four_pilot_flight_time_max_min": 17 * H,
    "unacclimated_reduction_min": 30,
    "unacclimated_reduction_augmented_min": 30,
    "accommodation_window_start_min": 22 * H,
    "accommodation_window_end_min": 5 * H,
    "split_min_accommodation_min": 3 * H,
    "split_combined_max_min": 14 * H,
    "augmented_max_segments": 3,
    "unforeseen_extension_max_min": 2 * H,
    "cumulative_flight_672_max_min": 100 * H,
    "cumulative_fdp_168_max_min": 60 * H,
    "cumulative_fdp_672_max_min": 190 * H,
    "free_period_168_min_min": 30 * H,
    "rest_before_duty_min_min": 10 * H,
}

LIMIT_CODES = (
    "flight_duty_period",
    "flight_time",
    "rest_before_duty",
    "free_period_168h",
    "cumulative_fdp_168h",
    "cumulative_fdp_672h",
    "cumulative_flight_672h",
)


def to_minutes(text):
    """'12:45' -> 765. Accepts durations beyond 24 hours."""
    hours, minutes = str(text).strip().split(":")
    return int(hours) * 60 + int(minutes)


def _scan(table, report_min):
    """Ordered linear scan over the published clock ranges."""
    for row in table:
        lo, hi = to_minutes(row[0][:2] + ":" + row[0][2:]), \
            to_minutes(row[1][:2] + ":" + row[1][2:])
        if lo <= report_min <= hi:
            return row[2]
    raise ValueError("no clock range covers minute %d" % report_min)


def table_a(report_min):
    return _scan(TABLE_A, report_min % 1440)


def table_b(report_min, segments):
    cells = _scan(TABLE_B, report_min % 1440)
    return cells[min(int(segments), len(cells)) - 1]


def table_c(report_min, facility_class, pilots):
    cells = _scan(TABLE_C, report_min % 1440)
    return cells[(int(facility_class) - 1) * 2 + (int(pilots) - 3)]
