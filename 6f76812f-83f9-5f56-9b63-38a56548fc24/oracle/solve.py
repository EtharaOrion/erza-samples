"""Reference solution.

Reads the shipped observation record, resolves each arc's total differential
signal bias against the published product tables, clears it out of the
geometry-free code observable, reduces every epoch to the vertical and averages
each arc. Writes /root/results.json. Nothing is read from the verifier and no
golden is embedded - the answer is derived.
"""

import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dsb  # noqa: E402
import tec  # noqa: E402

DATA = "/root/data"
TABLES = os.path.join(HERE, "dsb")
OUT = "/root/results.json"


def main():
    with open(os.path.join(DATA, "question.json")) as fh:
        question = json.load(fh)

    signals = {}
    with open(os.path.join(DATA, "receivers.csv")) as fh:
        for row in csv.DictReader(fh):
            signals[row["station_label"]] = (row["l1_signal"], row["l2_signal"])

    arcs = {}
    with open(os.path.join(DATA, "observations.csv")) as fh:
        for row in csv.DictReader(fh):
            arcs.setdefault((row["station_label"], row["sv_label"]), []).append(
                (float(row["range_l1_m"]), float(row["range_l2_m"]),
                 float(row["elevation_deg"])))

    sat_rows, rec_rows = {}, {}
    out = {}
    for arc in question["arcs"]:
        station, sat = arc["station_label"], arc["sv_label"]
        obs1, obs2 = signals[station]
        if sat not in sat_rows:
            sat_rows[sat] = dsb.load_label(TABLES, "sat", sat)
        if station not in rec_rows:
            rec_rows[station] = dsb.load_label(TABLES, "rec", station)
        # Bias-SINEX 1.00 eq. (5): the two sides sum.
        total_ns = (dsb.resolve(sat_rows[sat], obs1, obs2)
                    + dsb.resolve(rec_rows[station], obs1, obs2))
        out.setdefault(station, {})[sat] = tec.arc_mean_vtec(
            arcs[(station, sat)], total_ns)

    with open(OUT, "w") as fh:
        json.dump({"arc_mean_vtec_tecu": out}, fh, indent=2, sort_keys=True)
        fh.write("\n")


if __name__ == "__main__":
    main()
