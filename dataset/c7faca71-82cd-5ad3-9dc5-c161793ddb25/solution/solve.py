"""Reference solution.

Derives, for every pairing in the roster, the margin against each published
limit, the limit with the smallest margin, and that margin. Nothing is stored:
the limits come from oracle/part117_tables.py, everything else from the shipped
roster.
"""

import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import part117_tables as T  # noqa: E402

DATA = os.environ.get("DATA_DIR", "/root/data")
OUT = os.environ.get("RESULTS_PATH", "/root/results.json")


def elapsed_minutes(row):
    span = (T.to_minutes(row["release_local"])
            - T.to_minutes(row["report_local"])) % 1440
    return span if span else 1440


def relief_minutes(row):
    """Minutes excluded from the duty period by the split-duty provision.

    Every published condition must hold. The window runs across midnight, so
    membership is tested minute by minute rather than by comparing endpoints.
    """
    if not row["rest_opportunity_start"] or not row["rest_opportunity_end"]:
        return 0
    if int(row["pilots_assigned"]) != 2:
        return 0
    if row["rest_opportunity_accommodation"] != "suitable":
        return 0
    if row["rest_opportunity_after_first_segment"] != "yes":
        return 0
    start = T.to_minutes(row["rest_opportunity_start"])
    end = T.to_minutes(row["rest_opportunity_end"])
    duration = (end - start) % 1440
    if duration < T.LIMITS["split_min_accommodation_min"]:
        return 0
    lo = T.LIMITS["accommodation_window_start_min"]
    hi = T.LIMITS["accommodation_window_end_min"]
    for k in range(duration + 1):
        minute = (start + k) % 1440
        if not (minute >= lo or minute <= hi):
            return 0
    if elapsed_minutes(row) > T.LIMITS["split_combined_max_min"]:
        return 0
    return duration


def max_fdp_minutes(row):
    report = T.to_minutes(row["report_local"])
    pilots = int(row["pilots_assigned"])
    if pilots == 2:
        base = T.table_b(report, int(row["segments"]))
        cut = T.LIMITS["unacclimated_reduction_min"]
    else:
        facility = row["onboard_rest_facility"]
        base = T.table_c(report, int(facility[-1]), pilots)
        cut = T.LIMITS["unacclimated_reduction_augmented_min"]
    return base - (0 if row["acclimated"] == "yes" else cut)


def max_flight_minutes(row):
    pilots = int(row["pilots_assigned"])
    if pilots == 2:
        return T.table_a(T.to_minutes(row["report_local"]))
    if pilots == 3:
        return T.LIMITS["three_pilot_flight_time_max_min"]
    return T.LIMITS["four_pilot_flight_time_max_min"]


def margins(row):
    fdp = elapsed_minutes(row) - relief_minutes(row)
    flight = T.to_minutes(row["scheduled_flight_time"])
    lim = T.LIMITS
    return {
        "flight_duty_period": max_fdp_minutes(row) - fdp,
        "flight_time": max_flight_minutes(row) - flight,
        "rest_before_duty": (T.to_minutes(row["rest_before_duty"])
                             - lim["rest_before_duty_min_min"]),
        "free_period_168h": (T.to_minutes(row["longest_free_period_prior_7d"])
                             - lim["free_period_168_min_min"]),
        "cumulative_fdp_168h": (lim["cumulative_fdp_168_max_min"]
                                - T.to_minutes(row["prior_fdp_rolling_7d"])
                                - fdp),
        "cumulative_fdp_672h": (lim["cumulative_fdp_672_max_min"]
                                - T.to_minutes(row["prior_fdp_rolling_28d"])
                                - fdp),
        "cumulative_flight_672h": (lim["cumulative_flight_672_max_min"]
                                   - T.to_minutes(row["prior_flight_rolling_28d"])
                                   - flight),
    }


def main():
    with open(os.path.join(DATA, "question.json")) as fh:
        codes = json.load(fh)["limit_codes"]

    out = {}
    with open(os.path.join(DATA, "pairings.csv")) as fh:
        for row in csv.DictReader(fh):
            m = margins(row)
            best = min(codes, key=lambda c: (m[c], codes.index(c)))
            out[row["pairing_id"]] = {
                "fdp_margin_min": m["flight_duty_period"],
                "binding_limit": best,
                "binding_margin_min": m[best],
            }

    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
    print("wrote %s for %d pairings" % (OUT, len(out)))


if __name__ == "__main__":
    main()
