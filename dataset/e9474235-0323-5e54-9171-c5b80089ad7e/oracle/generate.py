"""Generator for the tidal-harmonic-prediction task (authoring-time only).

Emits the agent-visible inputs (environment/data/stations.csv, question.json) and the
grader-side ground truth (verifier/expected_values.json + golden.json). Golden heights are
DERIVED here from the gauge harmonic constants via oracle/tide_predict.py; nothing hand-typed.

Stations are identified only by OPAQUE gauge labels (TG-A/B/C). The real NOAA station
identities live grader-side only (build/station_map.json, verifier/truth.md) so the
withheld harmonic constants are not fetchable by a networked no-skill agent: the constants
exist only in the skill, keyed by the opaque label. The agent-visible data carries NO NOAA
ids, names, or coordinates and NO harmonic constants.
"""
import csv, json, os
from datetime import datetime
import tide_predict as tp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "environment", "data")
VER = os.path.join(ROOT, "verifier")

SEED = 20260725          # determinism marker (no RNG anywhere)
TOL = 0.10               # metres, per-item absolute tolerance
STATIONS = ["TG-A", "TG-B", "TG-C"]   # opaque gauge labels (real identities grader-side only)
TIMES = [
    ("t1", "2025-02-10T05:00:00Z"), ("t2", "2025-05-18T16:00:00Z"),
    ("t3", "2025-08-22T09:00:00Z"), ("t4", "2025-11-14T21:00:00Z"),
]
RECENT = "2025-01-01T00:00:00Z"       # instant of the orientation-distractor observation

def parse(iso): return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ")

defs = tp.load_definitions(os.path.join(HERE, "tidal_constituents.json"))
stn = tp.load_stations(os.path.join(HERE, "harmonic_constants.json"))
MAJOR = {"M2", "S2", "N2", "K1", "O1"}

def predict(label, iso): return tp.predict_height(stn[label], defs, parse(iso))
def predict_major(label, iso):
    s = dict(stn[label]); s["constituents"] = [c for c in stn[label]["constituents"] if c["name"] in MAJOR]
    return tp.predict_height(s, defs, parse(iso))
def predict_nonodal(label, iso):
    d2 = {k: {**v, "node_factor": "SOL"} for k, v in defs.items()}
    return tp.predict_height(stn[label], d2, parse(iso))

golden = {(lab, tk): predict(lab, iso) for lab in STATIONS for tk, iso in TIMES}
recent = {lab: predict(lab, RECENT) for lab in STATIONS}
def route_gaps(fn): return [abs(golden[(lab, tk)] - fn(lab, tk, iso)) for lab in STATIONS for tk, iso in TIMES]
g_recent = route_gaps(lambda lab, tk, iso: recent[lab])
g_meanlvl = route_gaps(lambda lab, tk, iso: stn[lab]["msl_minus_mllw_m"])
g_major = route_gaps(lambda lab, tk, iso: predict_major(lab, iso))
g_nonodal = route_gaps(lambda lab, tk, iso: predict_nonodal(lab, iso))
mean = lambda xs: sum(xs) / len(xs)

def main():
    os.makedirs(DATA, exist_ok=True); os.makedirs(VER, exist_ok=True)
    with open(os.path.join(DATA, "stations.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["station_id", "prediction_datum"])
        for lab in STATIONS: w.writerow([lab, stn[lab]["datum"]])
    question = {
        "prediction_datum": "each gauge's chart datum, in metres",
        "target_times_utc": [iso for _, iso in TIMES],
        "output_path": "/root/results.json",
        "output_contract": {"predictions": {"<station_id>": {"<target_time_utc>":
            "number, predicted tide height in metres above that gauge's chart datum at that instant"}}},
        "method_note": ("For each gauge and each target time, predict the tide height above the gauge's "
            "chart datum by harmonic synthesis of that gauge's tidal constituents evaluated at the given "
            "UTC instant, with the appropriate nodal corrections and datum offset."),
        "decoy_reference": {
            "note": ("Shown for orientation only. A single recent tide-gauge water level (metres above "
                     "chart datum) reported at each gauge near the start of the year."),
            "recent_observed_water_level_m": {lab: round(recent[lab], 3) for lab in STATIONS},
            "recent_observation_time_utc": RECENT,
        },
    }
    json.dump(question, open(os.path.join(DATA, "question.json"), "w"), indent=2); open(os.path.join(DATA, "question.json"), "a").write("\n")
    expected = {
        "method": ("height = Z0 + sum_i f_i*H_i*cos(2*pi*V_i + u_i - g_i): Schureman / NOAA CO-OPS "
                   "harmonic synthesis of the gauge harmonic constants (H_i amplitude, g_i Greenwich phase "
                   "lag), V_i the equilibrium argument, f_i/u_i the nodal factor/angle, Z0 the mean-sea-level "
                   "offset above the chart datum."),
        "seed": SEED, "freeze_tol_m": 1e-6,
    }
    items = []
    for lab in STATIONS:
        for tk, iso in TIMES:
            key = f"{lab}_{tk}_height_m"
            expected[f"ref_{key}"] = round(golden[(lab, tk)], 6)
            expected[f"tolerance_{key}_abs"] = TOL
            items.append({"station_id": lab, "time_utc": iso, "timekey": tk,
                          "ref_height_m": round(golden[(lab, tk)], 6), "tolerance_m": TOL})
    expected["items"] = items
    expected["station_detail"] = {lab: {"msl_minus_mllw_m": stn[lab]["msl_minus_mllw_m"],
        "heights_m": {tk: round(golden[(lab, tk)], 6) for tk, _ in TIMES}} for lab in STATIONS}
    expected["control_gaps"] = {
        "report_recent_observation": {"description": "report the single recent observed water level for every target time",
            "no_skill_route": True, "mean_abs_gap_m": round(mean(g_recent), 4), "height_m_gap_over_tol": round(mean(g_recent) / TOL, 2)},
        "report_mean_water_level": {"description": "report the mean water level above datum for every target time",
            "no_skill_route": True, "mean_abs_gap_m": round(mean(g_meanlvl), 4), "height_m_gap_over_tol": round(mean(g_meanlvl) / TOL, 2)},
        "major_constituents_only": {"description": "synthesise using only M2,S2,N2,K1,O1", "no_skill_route": False,
            "max_abs_gap_m": round(max(g_major), 4), "note": "with-constants trap the skill pins; full set required"},
        "omit_nodal_corrections": {"description": "synthesise with f=1,u=0", "no_skill_route": False,
            "max_abs_gap_m": round(max(g_nonodal), 4), "note": "with-constants trap the skill pins"},
    }
    json.dump(expected, open(os.path.join(VER, "expected_values.json"), "w"), indent=2); open(os.path.join(VER, "expected_values.json"), "a").write("\n")
    json.dump(expected, open(os.path.join(VER, "golden.json"), "w"), indent=2); open(os.path.join(VER, "golden.json"), "a").write("\n")
    print("wrote anonymized data + golden ; TOL=%.2f" % TOL)
    for lab in STATIONS:
        print(f"  {lab}", " ".join(f"{tk}={golden[(lab,tk)]:+.3f}" for tk, _ in TIMES), f"| recent={recent[lab]:.3f}")
    print("control x tol: recent=%.1f mean=%.1f | major_max=%.3f nonodal_max=%.3f" % (
        mean(g_recent)/TOL, mean(g_meanlvl)/TOL, max(g_major), max(g_nonodal)))

if __name__ == "__main__": main()
