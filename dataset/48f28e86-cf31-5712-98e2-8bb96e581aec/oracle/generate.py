"""Generator for the geomagnetic-declination-survey task.

Emits the agent-visible inputs (stations.csv, question.json) and the grader-side
ground truth (verifier/expected_values.json + golden.json alias). Fully
deterministic: the station geometry and the measured magnetic azimuths are fixed
here, and the true azimuths are DERIVED from the baked IGRF-13 coefficient file
via oracle/igrf_synth.field_elements. No RNG, no network, no stored answer.

Run at authoring time only; its outputs are frozen on disk and are NOT
regenerated inside the container.
"""
import csv
import json
import os

import igrf_synth

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "environment", "data")
VERIFIER = os.path.join(ROOT, "verifier")

# Determinism: this generator uses NO randomness (station geometry and magnetic
# azimuths are fixed literals below; true azimuths are derived from the baked
# coefficients). SEED is recorded to pin that determinism explicitly.
SEED = 20260724

# Survey epoch: a single decimal year for the whole campaign. On-epoch, so the
# declination model is evaluated with no time-interpolation ambiguity.
EPOCH = 2020.0

# Tolerance on the reported true azimuth (degrees, absolute). A realistic survey
# declination-reduction tolerance; see verifier/truth.md for the rationale.
TOL = 0.1

# A single rounded declination figure printed on a decades-old regional chart,
# supplied to the agent only for orientation. It is materially different from
# the true per-station declination at the survey epoch.
CHART_DECLINATION_DEG = 6.5

# Fixed survey network: id, geodetic latitude, longitude (E+), elevation (m),
# and the measured magnetic-referenced azimuth of the station baseline (deg).
STATIONS = [
    ("GDS01", 64.20, -152.30, 210,  37.4),
    ("GDS02", 66.85, -160.10,  95, 118.9),
    ("GDS03", 61.40, -149.90, 120, 205.2),
    ("GDS04", 68.10, -133.70,  60, 291.6),
    ("GDS05", 58.30, -134.40,  15,  73.0),
    ("GDS06", 70.20, -148.50,   8, 342.8),
    ("GDS07", 60.10, -141.00, 900, 159.5),
    ("GDS08", 67.50, -115.30, 180,  12.1),
    ("GDS09", 65.00, -126.80, 140, 248.7),
    ("GDS10", 72.10, -125.90,  30,  95.3),
    ("GDS11", 62.80, -137.60, 700, 300.0),
    ("GDS12", 55.20, -131.60,  10, 224.6),
]


def compute():
    rows = []
    truth = {}
    for sid, lat, lon, elev, mag_az in STATIONS:
        fe = igrf_synth.field_elements(EPOCH, lat, lon, elev / 1000.0)
        D = fe["D"]
        true_az = (mag_az + D) % 360.0
        rows.append((sid, lat, lon, elev, mag_az))
        truth[sid] = {
            "ref_true_azimuth_deg": true_az,
            "ref_declination_deg": D,
            "latitude_deg": lat,
            "longitude_deg": lon,
            "elevation_m": elev,
            "magnetic_azimuth_deg": mag_az,
        }
    return rows, truth


def control_gaps(truth):
    """Recompute the distance (in tolerance units) of each no-skill-accessible
    wrong path, and of the with-coefficients implementation trap."""
    Ds = [truth[s]["ref_declination_deg"] for s in truth]
    chart_gap = min(abs(D - CHART_DECLINATION_DEG) for D in Ds)
    zero_gap = min(abs(D) for D in Ds)
    return {
        "apply_chart_declination": {
            "description": "apply the single old-chart declination "
                           f"({CHART_DECLINATION_DEG} deg) to every station",
            "no_skill_route": True,
            "min_abs_gap_deg": round(chart_gap, 4),
            "true_azimuth_deg_gap_over_tol": round(chart_gap / TOL, 2),
        },
        "report_magnetic_as_true": {
            "description": "report the magnetic azimuth unchanged "
                           "(declination = 0)",
            "no_skill_route": True,
            "min_abs_gap_deg": round(zero_gap, 4),
            "true_azimuth_deg_gap_over_tol": round(zero_gap / TOL, 2),
        },
        "skip_geodetic_conversion": {
            "description": "compute IGRF-13 but treat the geodetic latitude as "
                           "geocentric (omit the WGS84 geodetic->geocentric step)",
            "no_skill_route": False,
            "note": "a with-coefficients implementation trap the skill pins; "
                    "0.12-0.32 deg (1.2x-3.2x tol) across the network",
        },
        "wmm_equivalent_model": {
            "description": "a different official field model (WMM) reproduces "
                           "the same physical declination within tolerance and "
                           "also requires its own withheld coefficient set",
            "no_skill_route": False,
            "note": "documents the nearest real competitor; not a separation "
                    "threat (agrees within tol; unavailable without a model)",
        },
    }


def main():
    rows, truth = compute()
    os.makedirs(DATA, exist_ok=True)
    os.makedirs(VERIFIER, exist_ok=True)

    # stations.csv (agent-visible input)
    with open(os.path.join(DATA, "stations.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["station_id", "latitude_deg", "longitude_deg",
                    "elevation_m", "magnetic_azimuth_deg"])
        for sid, lat, lon, elev, mag_az in rows:
            w.writerow([sid, lat, lon, elev, mag_az])

    # question.json (output contract + neutral orientation distractor)
    question = {
        "survey_epoch_decimal_year": EPOCH,
        "output_path": "/root/results.json",
        "output_contract": {
            "stations": {
                "<station_id>": {
                    "true_azimuth_deg": "number, the true (geographic) azimuth "
                    "of the station baseline in degrees, wrapped into [0, 360)"
                }
            }
        },
        "azimuth_reduction": (
            "For each station the true azimuth equals the measured magnetic "
            "azimuth plus the local magnetic declination at the survey epoch, "
            "with declination positive when magnetic north lies east of true "
            "north; wrap the result into [0, 360)."
        ),
        "decoy_reference": {
            "note": (
                "Shown for orientation only. A decades-old regional chart "
                "printed a single rounded magnetic declination for this general "
                "area."
            ),
            "old_chart_declination_deg": CHART_DECLINATION_DEG,
        },
    }
    with open(os.path.join(DATA, "question.json"), "w") as f:
        json.dump(question, f, indent=2)
        f.write("\n")

    # expected_values.json (grader-side ground truth) + golden.json alias.
    # Flat top-level ref_<name> / tolerance_<name>_abs keys (one output per
    # station), plus the per-station detail block and the control-gap ledger.
    expected = {
        "method": (
            "true_azimuth = (magnetic_azimuth + D) mod 360, where D is the "
            "IGRF-13 magnetic declination at the geodetic station and survey "
            "epoch, from spherical-harmonic synthesis of the Schmidt "
            "semi-normalised Gauss coefficients to degree 13."
        ),
        "epoch_decimal_year": EPOCH,
        "freeze_tol_deg": 1e-9,
    }
    for sid in truth:
        name = f"{sid}_true_azimuth_deg"
        expected[f"ref_{name}"] = truth[sid]["ref_true_azimuth_deg"]
        expected[f"tolerance_{name}_abs"] = TOL
    expected["station_detail"] = truth
    expected["control_gaps"] = control_gaps(truth)
    with open(os.path.join(VERIFIER, "expected_values.json"), "w") as f:
        json.dump(expected, f, indent=2)
        f.write("\n")
    with open(os.path.join(VERIFIER, "golden.json"), "w") as f:
        json.dump(expected, f, indent=2)
        f.write("\n")

    print("wrote stations.csv, question.json, expected_values.json, golden.json")
    print(f"epoch={EPOCH}  tol={TOL} deg  chart={CHART_DECLINATION_DEG} deg")
    for sid in truth:
        t = truth[sid]
        print(f"  {sid}: D={t['ref_declination_deg']:+8.4f}  "
              f"mag={t['magnetic_azimuth_deg']:6.1f}  "
              f"true={t['ref_true_azimuth_deg']:8.4f}")
    cg = control_gaps(truth)
    print("control gaps (x tol):",
          f"chart={cg['apply_chart_declination']['true_azimuth_deg_gap_over_tol']},",
          f"zero={cg['report_magnetic_as_true']['true_azimuth_deg_gap_over_tol']}")


if __name__ == "__main__":
    main()
