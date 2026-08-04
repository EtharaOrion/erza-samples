"""Reference solution.

Reads the listed satellite lines of sight, loads each antenna's own calibration
block, and reports the phase-centre correction for every case. Nothing is read from
the verifier and no golden is embedded - the answer is derived.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from antex import parse_antex, correction  # noqa: E402

DATA = "/root/data"
BLOCKS = os.path.join(HERE, "antennas")
OUT = "/root/results.json"


def main():
    with open(os.path.join(DATA, "question.json")) as fh:
        question = json.load(fh)

    blocks = {}
    out = {}
    for case in question["cases"]:
        label = case["antenna_id"]
        if label not in blocks:
            blocks[label] = parse_antex(
                os.path.join(BLOCKS, "antenna_%s.atx" % label))
        value = correction(blocks[label], case["frequency_code"],
                           case["azimuth_deg"], case["elevation_deg"])
        out.setdefault(label, {})[case["sight_id"]] = round(value, 9)

    with open(OUT, "w") as fh:
        json.dump({"phase_centre_correction_mm": out}, fh, indent=2)
        fh.write("\n")


if __name__ == "__main__":
    main()
