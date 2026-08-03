"""Reference solution for bridged-race-population-estimates.

Reads the shipped records and area profile, evaluates the published assignment
models for each record, and writes /root/results.json.

Run through oracle/solve.sh, which is the entrypoint that mentions
/root/results.json.
"""
from __future__ import annotations

import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bridging_models as models  # noqa: E402

DATA = os.environ.get("DATA_DIR", "/root/data")
RESULTS = os.environ.get("RESULTS_PATH", "/root/results.json")


def load_areas(data_dir=DATA):
    out = {}
    with open(os.path.join(data_dir, "area_profile.csv")) as fh:
        for row in csv.DictReader(fh):
            for key in ("pct_aian_alone", "pct_api_alone", "pct_black_alone",
                        "pct_white_alone", "pct_multiple_response"):
                row[key] = float(row[key])
            out[row["area_id"]] = row
    return out


def load_records(data_dir=DATA):
    with open(os.path.join(data_dir, "response_records.csv")) as fh:
        return list(csv.DictReader(fh))


def group_key(label):
    """`AIAN+API+WHITE` -> `AIAN_API_WHITE`, the key the model tables use."""
    return "_".join(part.strip().upper() for part in label.split("+"))


def solve(data_dir=DATA):
    areas = load_areas(data_dir)
    out = {}
    for record in load_records(data_dir):
        area = areas[record["area_id"]]
        shares = models.proportions(
            group_key(record["response_group"]), area,
            int(record["age_years"]),
            record["sex"].strip().lower() == "male",
            record["hispanic_origin"].strip().lower() == "hispanic")
        out[record["record_id"]] = shares[record["target_category"].strip().upper()]
    return out


def main():
    shares = solve()
    with open(RESULTS, "w") as fh:
        json.dump({"assignment_share": shares}, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print("wrote %s with %d assignment shares" % (RESULTS, len(shares)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
