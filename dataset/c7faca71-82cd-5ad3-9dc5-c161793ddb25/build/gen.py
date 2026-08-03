"""Build the flight-duty-period-legality instance.

SEED is fixed and there is no RNG: the roster is authored, not sampled, because
every pairing is placed deliberately against a named limit. The seed is recorded
so the build is reproducible in the same sense as the rest of the set.

What this script does, in order:

  1. reads the published limit tables and section limits out of the regulation
     XML shipped at verifier/part117.xml (the INDEPENDENT route);
  2. cross-checks them against oracle/part117_tables.py (the hand transcription)
     and refuses to build if the two disagree anywhere;
  3. solves each pairing's schedule and history from its TARGET margins, so the
     placement of every limit is explicit rather than reverse-engineered;
  4. derives every golden through BOTH routes and refuses to build unless they
     agree exactly;
  5. measures every control path and writes the ledger;
  6. writes environment/data/, verifier/expected_values.json and
     build/build_report.json.

Run from anywhere:  python3 build/gen.py
"""

from __future__ import annotations

import csv
import json
import os
import sys

SEED = 20260729

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "solution"))

import reg_reparse as REG          # noqa: E402  independent, XML-parsed
import part117_tables as ORACLE_T  # noqa: E402  oracle hand transcription

DATA = os.path.join(ROOT, "environment", "data")
TOL_MIN = 1.0            # minutes, on every graded margin

# ---------------------------------------------------------------------------
# The roster specification.
#
# Each pairing names its TARGET margin, in minutes, against every published
# limit. The schedule and the duty history are then solved from those targets,
# so which limit governs a pairing is a design decision recorded here rather
# than an accident of the numbers.
#
# Placement rules the instance is built to satisfy (asserted below):
#   * unaugmented pairings are governed by the flight duty period itself, and
#     carry a runner-up limit close enough above it that an inflated table entry
#     moves which limit governs;
#   * augmented pairings are governed by some OTHER limit, with the flight duty
#     period close enough above it that a deflated table entry moves it;
#   * no two limits tie inside a pairing;
#   * no margin is zero.
# ---------------------------------------------------------------------------

M = dict  # readability alias

ROSTER = [
    # ---- unaugmented, two-pilot: the flight duty period governs -----------
    dict(id="P01", report="05:34", segments=5, pilots=2, facility="none",
         acclimated="yes", rest_op=None,
         margins=M(flight_duty_period=23, flight_time=45, rest_before_duty=80,
                   free_period_168h=660, cumulative_fdp_168h=510,
                   cumulative_fdp_672h=1730, cumulative_flight_672h=1360)),
    dict(id="P02", report="04:22", segments=7, pilots=2, facility="none",
         acclimated="yes", rest_op=None,
         margins=M(flight_duty_period=-18, flight_time=115, rest_before_duty=40,
                   free_period_168h=190, cumulative_fdp_168h=380,
                   cumulative_fdp_672h=1240, cumulative_flight_672h=835)),
    dict(id="P03", report="13:12", segments=3, pilots=2, facility="none",
         acclimated="yes", rest_op=None,
         margins=M(flight_duty_period=7, flight_time=25, rest_before_duty=120,
                   free_period_168h=360, cumulative_fdp_168h=350,
                   cumulative_fdp_672h=1950, cumulative_flight_672h=785)),
    dict(id="P04", report="04:48", segments=7, pilots=2, facility="none",
         acclimated="no", rest_op=None,
         margins=M(flight_duty_period=-12, flight_time=130, rest_before_duty=85,
                   free_period_168h=120, cumulative_fdp_168h=675,
                   cumulative_fdp_672h=1875, cumulative_flight_672h=2050)),
    dict(id="P05", report="20:10", segments=3, pilots=2, facility="none",
         acclimated="yes",
         rest_op=dict(start="23:20", end="02:45", accommodation="suitable",
                      after_first_segment="yes"),
         margins=M(flight_duty_period=34, flight_time=45, rest_before_duty=105,
                   free_period_168h=480, cumulative_fdp_168h=390,
                   cumulative_fdp_672h=1470, cumulative_flight_672h=465)),
    dict(id="P06", report="19:55", segments=2, pilots=2, facility="none",
         acclimated="yes",
         rest_op=dict(start="02:30", end="05:40", accommodation="suitable",
                      after_first_segment="yes"),
         margins=M(flight_duty_period=-22, flight_time=50, rest_before_duty=30,
                   free_period_168h=240, cumulative_fdp_168h=395,
                   cumulative_fdp_672h=1775, cumulative_flight_672h=950)),
    dict(id="P07", report="21:40", segments=4, pilots=2, facility="none",
         acclimated="yes",
         rest_op=dict(start="23:50", end="02:35", accommodation="suitable",
                      after_first_segment="yes"),
         margins=M(flight_duty_period=-41, flight_time=30, rest_before_duty=60,
                   free_period_168h=420, cumulative_fdp_168h=555,
                   cumulative_fdp_672h=2115, cumulative_flight_672h=1110)),
    dict(id="P08", report="06:44", segments=5, pilots=2, facility="none",
         acclimated="no", rest_op=None,
         margins=M(flight_duty_period=-27, flight_time=65, rest_before_duty=15,
                   free_period_168h=30, cumulative_fdp_168h=300,
                   cumulative_fdp_672h=1410, cumulative_flight_672h=545)),
    dict(id="P09", report="23:40", segments=4, pilots=2, facility="none",
         acclimated="yes",
         rest_op=dict(start="01:10", end="04:20",
                      accommodation="flight_deck_seat",
                      after_first_segment="yes"),
         margins=M(flight_duty_period=9, flight_time=38, rest_before_duty=155,
                   free_period_168h=545, cumulative_fdp_168h=620,
                   cumulative_fdp_672h=1980, cumulative_flight_672h=910)),
    dict(id="P10", report="12:36", segments=6, pilots=2, facility="none",
         acclimated="yes", rest_op=None,
         margins=M(flight_duty_period=-26, flight_time=70, rest_before_duty=50,
                   free_period_168h=55, cumulative_fdp_168h=210,
                   cumulative_fdp_672h=1170, cumulative_flight_672h=615)),

    # ---- augmented: some other limit governs ------------------------------
    dict(id="P11", report="07:41", segments=3, pilots=3, facility="class_2",
         acclimated="yes", rest_op=None,
         margins=M(flight_duty_period=11, flight_time=-24, rest_before_duty=150,
                   free_period_168h=905, cumulative_fdp_168h=520,
                   cumulative_fdp_672h=2030, cumulative_flight_672h=330)),
    dict(id="P12", report="17:26", segments=2, pilots=4, facility="class_1",
         acclimated="no", rest_op=None,
         margins=M(flight_duty_period=14, flight_time=100, rest_before_duty=-19,
                   free_period_168h=1500, cumulative_fdp_168h=770,
                   cumulative_fdp_672h=3170, cumulative_flight_672h=880)),
    dict(id="P13", report="13:50", segments=2, pilots=3, facility="class_2",
         acclimated="yes", rest_op=None,
         margins=M(flight_duty_period=21, flight_time=80, rest_before_duty=150,
                   free_period_168h=840, cumulative_fdp_168h=860,
                   cumulative_fdp_672h=2780, cumulative_flight_672h=11)),
    dict(id="P14", report="09:20", segments=3, pilots=4, facility="class_1",
         acclimated="yes", rest_op=None,
         margins=M(flight_duty_period=38, flight_time=55, rest_before_duty=70,
                   free_period_168h=200, cumulative_fdp_168h=18,
                   cumulative_fdp_672h=1650, cumulative_flight_672h=530)),
    dict(id="P15", report="21:15", segments=2, pilots=3, facility="class_1",
         acclimated="yes", rest_op=None,
         margins=M(flight_duty_period=14, flight_time=60, rest_before_duty=30,
                   free_period_168h=300, cumulative_fdp_168h=430,
                   cumulative_fdp_672h=-6, cumulative_flight_672h=240)),
    dict(id="P16", report="06:12", segments=3, pilots=4, facility="class_2",
         acclimated="yes", rest_op=None,
         margins=M(flight_duty_period=-25, flight_time=150, rest_before_duty=50,
                   free_period_168h=-43, cumulative_fdp_168h=210,
                   cumulative_fdp_672h=1170, cumulative_flight_672h=615)),
    dict(id="P17", report="08:05", segments=2, pilots=3, facility="class_3",
         acclimated="yes", rest_op=None,
         margins=M(flight_duty_period=9, flight_time=-14, rest_before_duty=40,
                   free_period_168h=60, cumulative_fdp_168h=605,
                   cumulative_fdp_672h=1865, cumulative_flight_672h=700)),
]

COLUMNS = ["pairing_id", "report_local", "release_local", "segments",
           "scheduled_flight_time", "pilots_assigned", "onboard_rest_facility",
           "acclimated", "rest_opportunity_start", "rest_opportunity_end",
           "rest_opportunity_accommodation",
           "rest_opportunity_after_first_segment", "rest_before_duty",
           "longest_free_period_prior_7d", "prior_fdp_rolling_7d",
           "prior_fdp_rolling_28d", "prior_flight_rolling_28d"]


def hhmm(minutes: int) -> str:
    if minutes < 0:
        raise ValueError("negative duration %d" % minutes)
    return "%02d:%02d" % (minutes // 60, minutes % 60)


def clock(minutes: int) -> str:
    return "%02d:%02d" % ((minutes // 60) % 24, minutes % 60)


# ---------------------------------------------------------------------------
# Step 1/2: the two transcriptions must agree before anything is built
# ---------------------------------------------------------------------------

def cross_check_transcriptions(reg: REG.Regulation) -> dict:
    disagreements = []
    for minute in range(1440):
        want_a = reg.table_a_minutes(minute)
        got_a = ORACLE_T.table_a(minute)
        if want_a != got_a:
            disagreements.append("table A minute %d: xml=%d oracle=%d"
                                 % (minute, want_a, got_a))
        for seg in range(1, 10):
            want = reg.table_b_minutes(minute, seg)
            got = ORACLE_T.table_b(minute, seg)
            if want != got:
                disagreements.append("table B minute %d seg %d: xml=%d oracle=%d"
                                     % (minute, seg, want, got))
        for cls in (1, 2, 3):
            for pilots in (3, 4):
                want = reg.table_c_minutes(minute, cls, pilots)
                got = ORACLE_T.table_c(minute, cls, pilots)
                if want != got:
                    disagreements.append(
                        "table C minute %d class %d pilots %d: xml=%d oracle=%d"
                        % (minute, cls, pilots, want, got))
    for key, want in reg.limits.items():
        got = ORACLE_T.LIMITS.get(key)
        if want != got:
            disagreements.append("limit %s: xml=%r oracle=%r" % (key, want, got))
    if reg.limits != REG.PUBLISHED_LIMITS:
        disagreements.append("xml parse disagrees with the published tripwire")
    if disagreements:
        raise SystemExit("TRANSCRIPTION MISMATCH:\n  " + "\n  ".join(disagreements))
    return {"table_cells_compared": 1440 * (1 + 9 + 6),
            "section_limits_compared": len(reg.limits),
            "disagreements": 0}


# ---------------------------------------------------------------------------
# Step 3: solve each pairing from its target margins
# ---------------------------------------------------------------------------

def solve_pairing(reg: REG.Regulation, spec: dict) -> dict:
    want = spec["margins"]
    report = REG.hhmm_to_min(spec["report"])

    probe = {
        "pairing_id": spec["id"],
        "report_local": spec["report"],
        "segments": spec["segments"],
        "pilots_assigned": spec["pilots"],
        "onboard_rest_facility": spec["facility"],
        "acclimated": spec["acclimated"],
        "rest_opportunity_start": "",
        "rest_opportunity_end": "",
        "rest_opportunity_accommodation": "none",
        "rest_opportunity_after_first_segment": "",
    }
    rest_op = spec["rest_op"]
    if rest_op:
        probe["rest_opportunity_start"] = rest_op["start"]
        probe["rest_opportunity_end"] = rest_op["end"]
        probe["rest_opportunity_accommodation"] = rest_op["accommodation"]
        probe["rest_opportunity_after_first_segment"] = rest_op["after_first_segment"]

    max_fdp = reg.max_fdp_minutes(probe)
    fdp = max_fdp - want["flight_duty_period"]

    # The relief only exists if every published condition holds, and one of those
    # conditions is a ceiling on the COMBINED period, so the relief has to be
    # settled against the finished schedule rather than assumed.
    relief = 0
    if rest_op:
        trial = dict(probe)
        trial["release_local"] = clock(report + fdp)
        provisional = reg.accommodation_relief_minutes(trial)
        trial["release_local"] = clock(report + fdp + provisional)
        relief = reg.accommodation_relief_minutes(trial)

    release = report + fdp + relief
    probe["release_local"] = clock(release)

    max_flight = reg.max_flight_minutes(probe)
    flight = max_flight - want["flight_time"]
    probe["scheduled_flight_time"] = hhmm(flight)

    lim = reg.limits
    probe["rest_before_duty"] = hhmm(lim["rest_before_duty_min_min"]
                                     + want["rest_before_duty"])
    probe["longest_free_period_prior_7d"] = hhmm(
        lim["free_period_168_min_min"] + want["free_period_168h"])
    probe["prior_fdp_rolling_7d"] = hhmm(
        lim["cumulative_fdp_168_max_min"] - fdp - want["cumulative_fdp_168h"])
    probe["prior_fdp_rolling_28d"] = hhmm(
        lim["cumulative_fdp_672_max_min"] - fdp - want["cumulative_fdp_672h"])
    probe["prior_flight_rolling_28d"] = hhmm(
        lim["cumulative_flight_672_max_min"] - flight
        - want["cumulative_flight_672h"])
    return probe


def check_realism(reg: REG.Regulation, row: dict, spec: dict) -> None:
    fdp = reg.elapsed_minutes(row) - reg.accommodation_relief_minutes(row)
    flight = REG.hhmm_to_min(row["scheduled_flight_time"])
    seg = int(row["segments"])
    tag = row["pairing_id"]
    if not (2 * 60 <= flight < fdp):
        raise SystemExit("%s: flight %s does not sit inside a duty period of %s"
                         % (tag, row["scheduled_flight_time"], hhmm(fdp)))
    if flight < seg * 35:
        raise SystemExit("%s: %d segments cannot be flown in %s"
                         % (tag, seg, row["scheduled_flight_time"]))
    if int(row["pilots_assigned"]) > 2 and seg > reg.limits["augmented_max_segments"]:
        raise SystemExit("%s: augmented pairing exceeds the segment ceiling" % tag)
    if int(row["pilots_assigned"]) == 2 and row["onboard_rest_facility"] != "none":
        raise SystemExit("%s: an unaugmented pairing carries a rest facility" % tag)
    for key, lo, hi in (("rest_before_duty", 8 * 60, 30 * 60),
                        ("longest_free_period_prior_7d", 24 * 60, 90 * 60),
                        ("prior_fdp_rolling_7d", 10 * 60, 60 * 60),
                        ("prior_fdp_rolling_28d", 60 * 60, 190 * 60),
                        ("prior_flight_rolling_28d", 20 * 60, 100 * 60)):
        v = REG.hhmm_to_min(row[key])
        if not (lo <= v <= hi):
            raise SystemExit("%s: %s=%s outside the plausible envelope %s..%s"
                             % (tag, key, row[key], hhmm(lo), hhmm(hi)))


# ---------------------------------------------------------------------------
# Step 4: the oracle's own formulation, re-implemented here for the build-time
# cross-check. This mirrors oracle/solve.py and shares its arithmetic, which is
# exactly why it is NOT the anchor: the anchor is reg_reparse.
# ---------------------------------------------------------------------------

def oracle_margins(row: dict) -> dict[str, int]:
    to_min = ORACLE_T.to_minutes
    report = to_min(row["report_local"])
    release = to_min(row["release_local"])
    elapsed = (release - report) % 1440 or 1440
    lim = ORACLE_T.LIMITS

    relief = 0
    if row["rest_opportunity_start"] and row["rest_opportunity_end"]:
        start = to_min(row["rest_opportunity_start"])
        end = to_min(row["rest_opportunity_end"])
        duration = (end - start) % 1440
        window_start = lim["accommodation_window_start_min"]
        window_end = lim["accommodation_window_end_min"]
        inside = all(((start + k) % 1440 >= window_start
                      or (start + k) % 1440 <= window_end)
                     for k in range(duration + 1))
        if (int(row["pilots_assigned"]) == 2
                and row["rest_opportunity_accommodation"] == "suitable"
                and row["rest_opportunity_after_first_segment"] == "yes"
                and duration >= lim["split_min_accommodation_min"]
                and inside
                and elapsed <= lim["split_combined_max_min"]):
            relief = duration
    fdp = elapsed - relief

    pilots = int(row["pilots_assigned"])
    if pilots == 2:
        base = ORACLE_T.table_b(report, int(row["segments"]))
        cut = lim["unacclimated_reduction_min"]
        max_flight = ORACLE_T.table_a(report)
    else:
        base = ORACLE_T.table_c(report, int(row["onboard_rest_facility"][-1]),
                                pilots)
        cut = lim["unacclimated_reduction_augmented_min"]
        max_flight = (lim["three_pilot_flight_time_max_min"] if pilots == 3
                      else lim["four_pilot_flight_time_max_min"])
    max_fdp = base - (0 if row["acclimated"] == "yes" else cut)
    flight = to_min(row["scheduled_flight_time"])

    return {
        "flight_duty_period": max_fdp - fdp,
        "flight_time": max_flight - flight,
        "rest_before_duty": to_min(row["rest_before_duty"]) - lim["rest_before_duty_min_min"],
        "free_period_168h": (to_min(row["longest_free_period_prior_7d"])
                             - lim["free_period_168_min_min"]),
        "cumulative_fdp_168h": (lim["cumulative_fdp_168_max_min"]
                                - to_min(row["prior_fdp_rolling_7d"]) - fdp),
        "cumulative_fdp_672h": (lim["cumulative_fdp_672_max_min"]
                                - to_min(row["prior_fdp_rolling_28d"]) - fdp),
        "cumulative_flight_672h": (lim["cumulative_flight_672_max_min"]
                                   - to_min(row["prior_flight_rolling_28d"])
                                   - flight),
    }


def oracle_binding(row: dict) -> tuple[str, int]:
    m = oracle_margins(row)
    codes = ORACLE_T.LIMIT_CODES
    best = min(codes, key=lambda c: (m[c], codes.index(c)))
    return best, m[best]


# ---------------------------------------------------------------------------
# Step 5: control paths
# ---------------------------------------------------------------------------

def _answer(reg: REG.Regulation, rows, fdp_override=None, margin_filter=None,
            relief_override=None):
    """One competing method's full answer sheet.

    fdp_override(reg, row) -> maximum flight duty period in minutes.
    relief_override(reg, row) -> accommodation relief in minutes.
    margin_filter -> the subset of limits the method enumerates at all.
    """
    out = {}
    for row in rows:
        base = reg.margins(row)
        if relief_override is not None:
            delta = relief_override(reg, row) - reg.accommodation_relief_minutes(row)
            for code in ("flight_duty_period", "cumulative_fdp_168h",
                         "cumulative_fdp_672h"):
                base[code] += delta
        if fdp_override is not None:
            base["flight_duty_period"] += (fdp_override(reg, row)
                                           - reg.max_fdp_minutes(row))
        codes = margin_filter or REG.LIMIT_CODES
        best = min(codes, key=lambda c: (base[c], REG.LIMIT_CODES.index(c)))
        out[row["pairing_id"]] = {
            "fdp_margin_min": base["flight_duty_period"],
            "binding_limit": best,
            "binding_margin_min": base[best],
        }
    return out


def _table_b_first_column(reg, row):
    report = REG.hhmm_to_min(row["report_local"])
    base = (reg.table_b_minutes(report, 1) if int(row["pilots_assigned"]) == 2
            else reg.table_c_minutes(report, int(row["onboard_rest_facility"][-1]),
                                     int(row["pilots_assigned"])))
    cut = 0 if row["acclimated"] == "yes" else reg.limits["unacclimated_reduction_min"]
    return base - cut


def _midday_row(reg, row):
    midday = REG.hhmm_to_min("09:00")
    if int(row["pilots_assigned"]) == 2:
        base = reg.table_b_minutes(midday, int(row["segments"]))
    else:
        base = reg.table_c_minutes(midday, int(row["onboard_rest_facility"][-1]),
                                   int(row["pilots_assigned"]))
    cut = 0 if row["acclimated"] == "yes" else reg.limits["unacclimated_reduction_min"]
    return base - cut


def _unaugmented_everywhere(reg, row):
    report = REG.hhmm_to_min(row["report_local"])
    base = reg.table_b_minutes(report, int(row["segments"]))
    cut = 0 if row["acclimated"] == "yes" else reg.limits["unacclimated_reduction_min"]
    return base - cut


def control_paths(reg: REG.Regulation, rows):
    flat = reg.limits["split_combined_max_min"]          # the 14-hour figure
    return {
        "flat_14h_duty_day": dict(
            answer=_answer(reg, rows, fdp_override=lambda r, w: flat),
            nearest_real_competitor=True,
            scored_over="all",
            description="treat the maximum flight duty period as a flat 14 hours "
                        "regardless of report time, segment count, augmentation "
                        "or acclimation, while enumerating and applying every "
                        "other limit correctly",
            note="The nearest real competing method: what a scheduler who knows "
                 "the limits exist but not the matrix actually does. 14 hours is "
                 "the figure the regulation itself states for the combined "
                 "split-duty period and the figure the superseded domestic "
                 "scheduled-duty rule used, so it is the number that is reached "
                 "for. Not a strawman."),
        "segment_column_ignored": dict(
            answer=_answer(reg, rows, fdp_override=_table_b_first_column),
            scored_over="unaugmented",
            description="correct report-time row, but the single-segment column "
                        "used for every pairing",
            note="A real competing method: reading the matrix as a function of "
                 "report time alone is the most common misreading of it."),
        "report_row_ignored": dict(
            answer=_answer(reg, rows, fdp_override=_midday_row),
            scored_over="all",
            description="correct segment column, but the mid-morning report-time "
                        "row used for every pairing",
            note="A real competing method: the mid-morning row is the one quoted "
                 "in trade summaries, and using it everywhere is the mirror image "
                 "of ignoring the segment column."),
        "augmentation_ignored": dict(
            answer=_answer(reg, rows, fdp_override=_unaugmented_everywhere),
            scored_over="augmented",
            description="the unaugmented matrix applied to augmented pairings, "
                        "ignoring the rest-facility class and the extra pilots",
            note="A real competing method: an analyst who finds one matrix and "
                 "not the other applies it to everything. Scored only over the "
                 "pairings it alters, since on unaugmented pairings it is by "
                 "definition the correct route."),
        "unforeseen_extension_applied": dict(
            answer=_answer(reg, rows,
                           fdp_override=lambda r, w: r.max_fdp_minutes(w)
                           + r.limits["unforeseen_extension_max_min"]),
            scored_over="all",
            description="the two-hour unforeseen-circumstances extension added to "
                        "every scheduled pairing",
            note="A real competing method, and the most defensible-looking wrong "
                 "answer here: the extension is real and published, but it is "
                 "relief for circumstances arising after the schedule is set, so "
                 "it can never enlarge a SCHEDULED limit."),
        "unacclimated_reduction_skipped": dict(
            answer=_answer(reg, rows,
                           fdp_override=lambda r, w: r.max_fdp_minutes(w)
                           + (0 if w["acclimated"] == "yes"
                              else r.limits["unacclimated_reduction_min"])),
            scored_over="unacclimated",
            description="the acclimation reduction omitted",
            note="A real competing method: the reduction sits in a different "
                 "paragraph from the matrix and is routinely missed."),
        "split_duty_relief_skipped": dict(
            answer=_answer(reg, rows, relief_override=lambda r, w: 0),
            scored_over="split_duty_qualifying",
            description="the scheduled accommodation rest counted as duty",
            note="A real competing method: the split-duty provision is optional "
                 "relief and an analyst who does not know it is there leaves the "
                 "whole elapsed period on duty."),
        "split_duty_relief_unconditional": dict(
            answer=_answer(
                reg, rows,
                relief_override=lambda r, w: (
                    (REG.hhmm_to_min(w["rest_opportunity_end"])
                     - REG.hhmm_to_min(w["rest_opportunity_start"])) % 1440
                    if w["rest_opportunity_start"] else 0)),
            scored_over="split_duty_unqualifying",
            description="every scheduled accommodation rest excluded from duty "
                        "without testing the published conditions on it",
            note="A real competing method, and the opposite error to skipping the "
                 "relief: the conditions are a six-part conjunction and taking "
                 "the relief on sight is the standard shortcut."),
        "cumulative_limits_ignored": dict(
            answer=_answer(reg, rows, margin_filter=[
                c for c in REG.LIMIT_CODES if not c.startswith("cumulative")]),
            scored_over="all",
            description="only the per-pairing limits enumerated; the rolling "
                        "cumulative limits never checked",
            note="A real competing method: the cumulative limits need the crew "
                 "member's duty history rather than the pairing, and an analysis "
                 "that starts from the pairing sheet stops before them."),
        "flight_duty_period_only": dict(
            answer=_answer(reg, rows, margin_filter=["flight_duty_period"]),
            scored_over="all",
            description="the flight duty period treated as the only limit, so it "
                        "is always reported as the governing one",
            note="Floor-bounding strawman rather than a competing method: it is "
                 "what answering the headline limit everywhere looks like, and it "
                 "bounds how much of the graded set a run can collect without "
                 "enumerating."),
    }


SCOPES = {
    "all": lambda rows: [r["pairing_id"] for r in rows],
    "unaugmented": lambda rows: [r["pairing_id"] for r in rows
                                 if int(r["pilots_assigned"]) == 2],
    "augmented": lambda rows: [r["pairing_id"] for r in rows
                               if int(r["pilots_assigned"]) > 2],
    "unacclimated": lambda rows: [r["pairing_id"] for r in rows
                                  if r["acclimated"] == "no"],
    "split_duty": lambda rows: [r["pairing_id"] for r in rows
                                if r["rest_opportunity_start"]],
}
# Scopes that need the regulation to decide membership are filled in by main().
SCOPE_BY_RELIEF: dict[str, list[str]] = {}


def _scope_ids(name, rows):
    if name in SCOPE_BY_RELIEF:
        return SCOPE_BY_RELIEF[name]
    return SCOPES[name](rows)


def measure(golden, answer, ids):
    """Distance of one competing method from the reference, in tolerance units."""
    gaps = {"fdp_margin_min": [], "binding_margin_min": []}
    passed, total, mism = 0, 0, 0
    for pid in ids:
        g, a = golden[pid], answer[pid]
        for field in gaps:
            d = abs(a[field] - g[field]) / TOL_MIN
            gaps[field].append(d)
            total += 1
            if d <= 1.0:
                passed += 1
        total += 1
        if a["binding_limit"] == g["binding_limit"]:
            passed += 1
        else:
            mism += 1
    out = {}
    for field, vals in gaps.items():
        key = "fdp_margin" if field == "fdp_margin_min" else "binding_margin"
        out["%s_gap_over_tol" % key] = round(max(vals), 3)
        nonzero = [v for v in vals if v > 0]
        out["%s_min_nonzero_gap_over_tol" % key] = round(min(nonzero), 3) if nonzero else 0.0
        out["%s_cases_reproduced" % key] = sum(1 for v in vals if v <= 1.0)
    out["binding_limit_mismatches"] = mism
    out["graded_cases_scored"] = total
    out["graded_cases_reproduced"] = passed
    return out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    reg = REG.Regulation()
    transcription = cross_check_transcriptions(reg)

    rows = []
    for spec in ROSTER:
        row = solve_pairing(reg, spec)
        check_realism(reg, row, spec)
        rows.append(row)

    ids = [r["pairing_id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise SystemExit("duplicate pairing id")
    n = len(rows)
    if any(n % d == 0 for d in range(2, n)):
        raise SystemExit("the number of pairings must be prime, got %d" % n)

    # ---- goldens, through both routes ------------------------------------
    golden, disagreements = {}, []
    for row, spec in zip(rows, ROSTER):
        ind = reg.margins(row)
        orc = oracle_margins(row)
        for code in REG.LIMIT_CODES:
            if ind[code] != orc[code]:
                disagreements.append("%s %s: independent=%d oracle=%d"
                                     % (row["pairing_id"], code, ind[code],
                                        orc[code]))
            if ind[code] != spec["margins"][code]:
                disagreements.append("%s %s: derived %d, roster asked for %d"
                                     % (row["pairing_id"], code, ind[code],
                                        spec["margins"][code]))
        code_i, margin_i = reg.binding(row)
        code_o, margin_o = oracle_binding(row)
        if (code_i, margin_i) != (code_o, margin_o):
            disagreements.append("%s binding: independent=%s/%d oracle=%s/%d"
                                 % (row["pairing_id"], code_i, margin_i,
                                    code_o, margin_o))
        ordered = sorted(ind.values())
        if ordered[0] == ordered[1]:
            disagreements.append("%s: two limits tie at %d" % (row["pairing_id"],
                                                               ordered[0]))
        if any(v == 0 for v in ind.values()):
            disagreements.append("%s: a margin is exactly zero" % row["pairing_id"])
        golden[row["pairing_id"]] = {
            "fdp_margin_min": ind["flight_duty_period"],
            "binding_limit": code_i,
            "binding_margin_min": margin_i,
            "all_margins_min": ind,
            "compliant": margin_i >= 0,
        }
    if disagreements:
        raise SystemExit("GOLDEN DISAGREEMENT:\n  " + "\n  ".join(disagreements))

    # ---- design invariants the separation argument rests on ---------------
    design = []
    for row in rows:
        pid = row["pairing_id"]
        m = golden[pid]["all_margins_min"]
        fdp_m = m["flight_duty_period"]
        runner = sorted(m.values())[1]
        cushion = reg.max_fdp_minutes(row) - reg.limits["split_combined_max_min"]
        if int(row["pilots_assigned"]) == 2:
            if golden[pid]["binding_limit"] != "flight_duty_period":
                design.append("%s: unaugmented pairing not governed by the "
                              "flight duty period" % pid)
            if runner >= fdp_m - cushion:
                design.append("%s: runner-up %d is not inside the %d-minute "
                              "inflation an unaugmented flat reading produces"
                              % (pid, runner, -cushion))
        else:
            if golden[pid]["binding_limit"] == "flight_duty_period":
                design.append("%s: augmented pairing governed by the flight duty "
                              "period" % pid)
            if fdp_m - golden[pid]["binding_margin_min"] >= cushion:
                design.append("%s: flight-duty margin sits %d above the governing "
                              "limit, outside the %d-minute deflation"
                              % (pid, fdp_m - golden[pid]["binding_margin_min"],
                                 cushion))
    if design:
        raise SystemExit("DESIGN INVARIANT BROKEN:\n  " + "\n  ".join(design))

    # ---- control ledger ---------------------------------------------------
    SCOPE_BY_RELIEF["split_duty_qualifying"] = [
        r["pairing_id"] for r in rows
        if reg.accommodation_relief_minutes(r) > 0]
    SCOPE_BY_RELIEF["split_duty_unqualifying"] = [
        r["pairing_id"] for r in rows
        if r["rest_opportunity_start"]
        and reg.accommodation_relief_minutes(r) == 0]
    paths = control_paths(reg, rows)
    ledger, free_pass = {}, []
    for name, spec in paths.items():
        scope_ids = _scope_ids(spec["scored_over"], rows)
        stats = measure(golden, spec["answer"], scope_ids)
        entry = {"description": spec["description"], "note": spec["note"],
                 "scored_over": spec["scored_over"],
                 "pairings_scored": len(scope_ids)}
        entry.update(stats)
        if spec.get("nearest_real_competitor"):
            entry["nearest_real_competitor"] = True
            if stats["graded_cases_reproduced"]:
                free_pass.append("%s reproduces %d graded case(s)"
                                 % (name, stats["graded_cases_reproduced"]))
        ledger[name] = entry
    if free_pass:
        raise SystemExit("NEAREST COMPETITOR REPRODUCES A GRADED CASE:\n  "
                         + "\n  ".join(free_pass))

    # ---- constant-answer floors (guess resistance) ------------------------
    floors = {}
    for code in REG.LIMIT_CODES:
        floors["always_%s" % code] = sum(
            1 for pid in ids if golden[pid]["binding_limit"] == code)
    for guess in range(-180, 181, 30):
        floors["every_margin_%d" % guess] = sum(
            1 for pid in ids
            for field in ("fdp_margin_min", "binding_margin_min")
            if abs(golden[pid][field] - guess) <= TOL_MIN)

    # ---- write the agent-visible instance ---------------------------------
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "pairings.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        for row in rows:
            w.writerow({k: row[k] for k in COLUMNS})

    question = {
        "regulatory_scope": (
            "Scheduled domestic and flag passenger operations of a US air "
            "carrier certificated under 14 CFR part 121, whose flightcrew "
            "members are subject to 14 CFR part 117. Every row is a SCHEDULED "
            "pairing taken from the published bid package; none is an as-flown "
            "record, and no unforeseen operational circumstance has arisen."),
        "columns": {
            "pairing_id": "opaque label for the pairing",
            "report_local": "scheduled report time, expressed in the local time "
                            "of the theater the crew was last acclimated to",
            "release_local": "scheduled release time, same clock; earlier than "
                             "report_local means the pairing ends the next day",
            "segments": "number of scheduled flight segments",
            "scheduled_flight_time": "total scheduled flight time, h:mm",
            "pilots_assigned": "number of pilots assigned to the pairing",
            "onboard_rest_facility": "class of onboard rest facility fitted, or "
                                     "'none'",
            "acclimated": "whether the crew is acclimated to the theater the "
                          "report time is expressed in",
            "rest_opportunity_start": "start of a scheduled rest opportunity "
                                      "inside the pairing, or blank",
            "rest_opportunity_end": "end of that rest opportunity, or blank",
            "rest_opportunity_accommodation": "what the crew member is given for "
                                              "that rest opportunity",
            "rest_opportunity_after_first_segment": "whether the rest opportunity "
                                                    "is scheduled only after the "
                                                    "first segment has been flown",
            "rest_before_duty": "rest actually given immediately before report, h:mm",
            "longest_free_period_prior_7d": "longest single period free from all "
                                            "duty in the 7 days before report, h:mm",
            "prior_fdp_rolling_7d": "flight duty period hours already accrued in "
                                    "the 7 days before report, h:mm",
            "prior_fdp_rolling_28d": "flight duty period hours already accrued in "
                                     "the 28 days before report, h:mm",
            "prior_flight_rolling_28d": "flight hours already accrued in the 28 "
                                        "days before report, h:mm",
        },
        "limit_codes": list(REG.LIMIT_CODES),
        "output_path": "/root/results.json",
        "output_contract": {
            "fdp_margin_min": "signed whole minutes: the applicable maximum "
                              "flight duty period minus the scheduled flight "
                              "duty period",
            "binding_limit": "one of limit_codes: the limit with the smallest "
                             "margin, ties resolved in the order limit_codes is "
                             "given in",
            "binding_margin_min": "signed whole minutes: that smallest margin. "
                                  "The pairing complies with every limit exactly "
                                  "when this is not negative.",
        },
    }
    with open(os.path.join(DATA, "question.json"), "w") as fh:
        json.dump(question, fh, indent=2, sort_keys=True)
        fh.write("\n")

    # ---- expected values --------------------------------------------------
    items = []
    for pid in ids:
        g = golden[pid]
        items.append({"pairing": pid, "field": "fdp_margin_min",
                      "kind": "margin", "ref": g["fdp_margin_min"],
                      "tolerance": TOL_MIN})
        items.append({"pairing": pid, "field": "binding_limit",
                      "kind": "code", "ref": g["binding_limit"],
                      "tolerance": None})
        items.append({"pairing": pid, "field": "binding_margin_min",
                      "kind": "margin", "ref": g["binding_margin_min"],
                      "tolerance": TOL_MIN})

    expected = {
        "schema": "flat",
        "seed": SEED,
        "n_pairings": n,
        "n_cases": len(items),
        "pairing_ids": ids,
        "limit_codes": list(REG.LIMIT_CODES),
        "items": items,
        "binding_limit_by_pairing": {pid: golden[pid]["binding_limit"]
                                     for pid in ids},
        "compliant_by_pairing": {pid: golden[pid]["compliant"] for pid in ids},
        "all_margins_by_pairing": {pid: golden[pid]["all_margins_min"]
                                   for pid in ids},
        "constant_answer_floors": floors,
        "control_gaps": ledger,
        "tolerance_fdp_margin_min_abs": TOL_MIN,
        "tolerance_binding_margin_min_abs": TOL_MIN,
        "published_precision_ambiguity_margin_maxabs": 0.0,
        "published_precision_ambiguity_method":
            "re-derived through the second formulation and the worst "
            "disagreement taken: every margin recomputed from the limits parsed "
            "out of the published regulation XML, by the release-deadline route, "
            "and differenced against the oracle's transcription-and-subtraction "
            "route. Worst disagreement over all 119 margins: 0 minutes.",
        "published_precision_ambiguity_note":
            "Zero by construction, and this is the one place where a lookup "
            "table is easier to grade than a fitted relation. Every published "
            "cell is a whole or half hour, every scheduled time is a whole "
            "minute, and every limit is an integral number of hours, so a "
            "faithful reading has no rounding freedom at all. The tolerance is "
            "one minute purely to absorb a differently-ordered integer "
            "computation.",
        "method":
            "each pairing's margin taken against every limit the part imposes on "
            "it, the maximum flight duty period read from the matrix its report "
            "time and segment count select and reduced when the crew is not "
            "acclimated, the accommodation rest excluded from the duty period "
            "only when every published condition on it holds, and the governing "
            "limit taken as the smallest of the seven margins",
    }
    for pid in ids:
        expected["ref_%s_fdp_margin_min" % pid] = golden[pid]["fdp_margin_min"]
        expected["ref_%s_binding_margin_min" % pid] = golden[pid]["binding_margin_min"]

    smallest = min(
        min(v for k, v in entry.items()
            if k.endswith("_min_nonzero_gap_over_tol") and v > 0)
        for entry in ledger.values()
        if any(k.endswith("_min_nonzero_gap_over_tol") and v > 0
               for k, v in entry.items()))
    expected["smallest_wrong_path_gap_multiple"] = smallest
    expected["tolerance_rationale"] = (
        "One absolute tolerance, 1.000 minute, on every graded margin. LOWER "
        "BOUND (defensible-reading spread): zero. Every published cell is a "
        "whole or half hour, every clock time in the roster is a whole minute "
        "and every non-tabular limit is an integral number of hours, so two "
        "faithful readings of the cited edition cannot differ by any amount; "
        "the measured disagreement between the two independent formulations "
        "over all 119 margins is 0 minutes. The one minute allowed is there "
        "only so that an integer computation performed in a different order, or "
        "carried through a float, cannot fail. UPPER BOUND (nearest wrong "
        "route): the smallest non-zero separation any competing method achieves "
        "on any graded margin is %.3f tolerances, and the nearest real "
        "competitor reproduces none of the %d graded cases."
        % (smallest, len(items)))

    with open(os.path.join(ROOT, "tests", "expected_values.json"), "w") as fh:
        json.dump(expected, fh, indent=2, sort_keys=True)
        fh.write("\n")

    # ---- leak scan --------------------------------------------------------
    leaks = leak_scan(expected, rows)
    if leaks:
        raise SystemExit("GOLDEN LITERAL REACHABLE FROM THE AGENT SURFACE:\n  "
                         + "\n  ".join(leaks))

    print("built %d pairings, %d graded cases" % (n, len(items)))
    print("transcription cross-check: %s" % transcription)
    print("smallest non-zero wrong-path gap: %.3f tolerances" % smallest)
    for name, entry in sorted(ledger.items()):
        print("  %-34s worst %8.1fx  min>0 %7.1fx  reproduces %2d/%2d"
              % (name, max(entry["fdp_margin_gap_over_tol"],
                           entry["binding_margin_gap_over_tol"]),
                 min(v for k, v in entry.items()
                     if k.endswith("_min_nonzero_gap_over_tol")) or 0.0,
                 entry["graded_cases_reproduced"], entry["graded_cases_scored"]))
    print("constant-answer floors: %s" % json.dumps(floors, sort_keys=True))


def leak_scan(expected, rows):
    """No golden may be readable, as a literal, from anything the agent sees."""
    import re
    surface = []
    for name in ("pairings.csv", "question.json"):
        with open(os.path.join(DATA, name)) as fh:
            surface.append((name, fh.read()))
    task_md = os.path.join(ROOT, "instruction.md")
    if os.path.exists(task_md):
        with open(task_md) as fh:
            surface.append(("instruction.md", fh.read()))
    out = []
    for key, val in expected.items():
        if not key.startswith("ref_") or not isinstance(val, (int, float)):
            continue
        for form in _forms(float(val)):
            for name, text in surface:
                for m in re.finditer(re.escape(form), text):
                    i, j = m.start(), m.end()
                    if text[i - 1:i].isdigit() or text[j:j + 1].isdigit():
                        continue
                    out.append("%s=%s appears in %s as %r" % (key, val, name, form))
                    break
    return out


def _forms(f: float) -> set[str]:
    forms = {str(f), repr(f), "%g" % f}
    for prec in range(1, 7):
        forms.add("%.*f" % (prec, f))
    if f.is_integer():
        forms.add(str(int(f)))
    return {x for x in forms if len(x.strip("-.,")) >= 3}


if __name__ == "__main__":
    main()
