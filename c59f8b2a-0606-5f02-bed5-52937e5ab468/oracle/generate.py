"""Bake the frozen instance for antenna-phase-centre-correction.

AUTHOR-SIDE TOOLING - NOT RE-RUNNABLE FROM THE PUBLISHED SAMPLE, AND IT DOES
NOT NEED TO BE. This script's raw-input directory - `.omo/igs`, the
un-anonymised IGS20 ANTEX source it reads its antenna blocks from, located
through SRC below - is deliberately NOT published, matching this repository's
practice of withholding author-side material. A consumer therefore cannot
execute this file: SRC names a path that does not exist in the published
sample. Nothing is lost by that, because what the script produces is already
here and frozen: the anonymised calibration blocks shipped in
`oracle/antennas/`, in `tests/`, and in the skill's `references/`, alongside
the agent-visible data and the frozen golden. Those exact bytes are what this
bundle's `canonical_content_hash` seal certifies, so they can be verified
without re-running anything. This file ships as the readable record of HOW the
shipped bytes were derived, not as a step anyone downstream is expected to run.

Run once at authoring time, never inside the container. Reads the retrieved IGS20
ANTEX antenna blocks from .omo/igs/, anonymises them to ANT-A/ANT-B/ANT-C, and
writes: the agent-visible data, the calibration blocks carried by the skill and by
the grader, the frozen golden, and the grader-side identity map.

Source retrieval (2026-07-27, International GNSS Service, IGS20 antenna model):
  https://files.igs.org/pub/station/general/igs20.atx

Instance selection rules, fixed before any measurement was taken and applied
uniformly to all three antennas:
  frequencies  the four ANTEX frequency codes G01, G02, G05, E06, in that order,
               one line of sight each
  direction    azimuth drawn uniformly on [0, 360) and elevation on [10, 75],
               both rounded to 0.1 deg, from a generator seeded with SEED
  rejection    a draw is rejected if the azimuth or the zenith angle falls within
               0.5 deg of a grid node (so the bilinear step is load-bearing), or
               if the phase-centre variation at that direction is below
               PCV_FLOOR_MM in magnitude (so the variation term is exercised)
  nominal      the orientation offset shown in the input is the real IGS20 mean
               phase-centre offset of a fourth published geodetic antenna, at the
               same four frequency codes
"""

import csv
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(ROOT, "..", "..", ".."))
SRC = os.path.join(REPO, ".omo", "igs")

sys.path.insert(0, HERE)
from antex import parse_antex, correction, pco_projection, pcv_at  # noqa: E402

SEED = 20260727
TOL_MM = 0.05          # absolute, millimetres; see verifier/truth.md "Tolerance"
REF_DP = 9             # the reference is the correction rounded to this many places
PCV_FLOOR_MM = 1.0     # selection rule: the variation term must be exercised
NODE_GUARD_DEG = 0.5   # selection rule: keep the direction off the grid nodes

# label -> the real IGS20 antenna the block was taken from
ANTENNAS = [
    ("ANT-A", "TRM57971.00     NONE", "antenna_TRM5797100_____NONE.atx"),
    ("ANT-B", "LEIAR25.R4      LEIT", "antenna_LEIAR25R4______LEIT.atx"),
    ("ANT-C", "ASH701945C_M    NONE", "antenna_ASH701945C_M____NONE.atx"),
]
NOMINAL = ("JAVRINGANT_DM   NONE", "antenna_JAVRINGANT_DM___NONE.atx")

FREQS = [
    ("G01", "GPS L1"),
    ("G02", "GPS L2"),
    ("G05", "GPS L5"),
    ("E06", "Galileo E6"),
]


# --------------------------------------------------------------------------- #
# anonymised ANTEX writer
# --------------------------------------------------------------------------- #

def _rec(body, label):
    return "%-60s%-20s" % (body, label)


def write_anonymised(path, src_lines, label):
    """Re-emit one ANTEX antenna block with every identifying field replaced.

    Dropped: the manufacturer type and radome code, the calibrating agency, the
    calibration date and sample counts, and the numeric suffix of the SINEX code.
    Kept: the grid geometry and every frequency block, byte-for-byte.
    """
    out = []
    for line in src_lines:
        line = line.rstrip("\n")
        if not line.strip():
            continue
        tag = line[60:].strip()
        if tag == "START OF ANTENNA":
            out.append(_rec("", "START OF ANTENNA"))
        elif tag == "TYPE / SERIAL NO":
            out.append(_rec("%-20s" % label, "TYPE / SERIAL NO"))
        elif tag == "METH / BY / # / DATE":
            out.append(_rec("%-20s" % "ROBOT", "METH / BY / # / DATE"))
        elif tag == "SINEX CODE":
            out.append(_rec("%-10s" % "IGS20", "SINEX CODE"))
        elif tag == "COMMENT":
            continue
        elif tag in ("DAZI", "ZEN1 / ZEN2 / DZEN", "# OF FREQUENCIES",
                     "START OF FREQUENCY", "NORTH / EAST / UP",
                     "END OF FREQUENCY", "END OF ANTENNA"):
            out.append(line)
        else:
            out.append(line)
    with open(path, "w") as fh:
        fh.write("\n".join(out) + "\n")


# --------------------------------------------------------------------------- #
# wrong-route implementations, evaluated live so the ledger cannot drift
# --------------------------------------------------------------------------- #

def route_nominal_offset(blocks, nominal, item):
    """Project the supplied nominal offset; apply no variation."""
    return pco_projection(nominal, item["frequency_code"],
                          item["azimuth_deg"], item["elevation_deg"])


def route_no_correction(blocks, nominal, item):
    return 0.0


def route_pco_only(blocks, nominal, item):
    return pco_projection(blocks[item["antenna_id"]], item["frequency_code"],
                          item["azimuth_deg"], item["elevation_deg"])


def route_variation_subtracted(blocks, nominal, item):
    """Subtract the variation from the offset projection instead of adding it."""
    block = blocks[item["antenna_id"]]
    return (pco_projection(block, item["frequency_code"],
                           item["azimuth_deg"], item["elevation_deg"])
            - pcv_at(block, item["frequency_code"], item["azimuth_deg"],
                     90.0 - item["elevation_deg"]))


def route_elevation_as_zenith(blocks, nominal, item):
    """Read the variation grid at the elevation angle instead of the zenith angle."""
    block = blocks[item["antenna_id"]]
    return (pco_projection(block, item["frequency_code"],
                           item["azimuth_deg"], item["elevation_deg"])
            + pcv_at(block, item["frequency_code"],
                     item["azimuth_deg"], item["elevation_deg"]))


def route_noazi_column(blocks, nominal, item):
    """Use the azimuth-independent NOAZI row instead of the azimuth-resolved grid."""
    block = blocks[item["antenna_id"]]
    values = block["freqs"][item["frequency_code"]]["noazi"]
    zen = 90.0 - item["elevation_deg"]
    j = int((zen - block["zen1"]) / block["dzen"])
    j = max(0, min(j, len(values) - 2))
    f = (zen - (block["zen1"] + j * block["dzen"])) / block["dzen"]
    return (pco_projection(block, item["frequency_code"], item["azimuth_deg"],
                           item["elevation_deg"])
            + (1.0 - f) * values[j] + f * values[j + 1])


def route_other_antenna(blocks, nominal, item):
    order = [lab for lab, _t, _f in ANTENNAS]
    other = order[(order.index(item["antenna_id"]) + 1) % len(order)]
    return correction(blocks[other], item["frequency_code"],
                      item["azimuth_deg"], item["elevation_deg"])


def variant_rounded_to_antex_precision(blocks, nominal, item):
    """Report at the 0.01 mm precision at which ANTEX tabulates."""
    return round(correction(blocks[item["antenna_id"]], item["frequency_code"],
                            item["azimuth_deg"], item["elevation_deg"]), 2)


def variant_zenith_first_bilinear(blocks, nominal, item):
    """Interpolate in zenith angle first, then in azimuth."""
    block = blocks[item["antenna_id"]]
    freq = block["freqs"][item["frequency_code"]]
    grid = freq["grid"]
    azimuths = sorted(grid)
    zen = 90.0 - item["elevation_deg"]
    j = int((zen - block["zen1"]) / block["dzen"])
    j = max(0, min(j, len(grid[azimuths[0]]) - 2))
    fz = (zen - (block["zen1"] + j * block["dzen"])) / block["dzen"]
    i = int((item["azimuth_deg"] - azimuths[0]) / block["dazi"])
    i = max(0, min(i, len(azimuths) - 2))
    fa = (item["azimuth_deg"] - azimuths[i]) / block["dazi"]
    lo = (1.0 - fz) * grid[azimuths[i]][j] + fz * grid[azimuths[i]][j + 1]
    hi = (1.0 - fz) * grid[azimuths[i + 1]][j] + fz * grid[azimuths[i + 1]][j + 1]
    return (pco_projection(block, item["frequency_code"], item["azimuth_deg"],
                           item["elevation_deg"]) + (1.0 - fa) * lo + fa * hi)


CONTROLS = [
    ("nominal_offset_without_variation", route_nominal_offset, True,
     "project the nominal phase-centre offset supplied for orientation onto the line "
     "of sight and apply no phase-centre variation",
     "NEAREST REAL COMPETITOR: substituting a published calibration for a similar "
     "geodetic antenna is what an analyst without the antenna's own block actually "
     "does, and the route the recall probe showed the model takes unprompted. Not a "
     "strawman."),
    ("no_correction_applied", route_no_correction, True,
     "report zero, the value ANTEX assigns to an antenna carrying no calibration entry",
     ""),
    ("pco_projection_without_variation", route_pco_only, False,
     "project the antenna's own offset vector but drop the phase-centre variation term",
     ""),
    ("variation_subtracted_instead_of_added", route_variation_subtracted, False,
     "subtract the phase-centre variation from the offset projection instead of "
     "adding it",
     ""),
    ("other_antenna_calibration", route_other_antenna, False,
     "apply one antenna's calibration block to another antenna's line of sight",
     ""),
]

# Wrong routes that were measured and did NOT clear the 2x-tolerance floor on every
# case. They are recorded here rather than in the ledger, because a control that does
# not separate everywhere would overstate the separation (V-04).
NON_SEPARATING = [
    ("elevation_used_as_zenith_angle", route_elevation_as_zenith,
     "index the variation grid with the elevation angle instead of the zenith angle"),
    ("noazi_row_instead_of_azimuth_grid", route_noazi_column,
     "read the azimuth-independent NOAZI row instead of the azimuth-resolved grid"),
]

VARIANTS = [
    ("reported_at_antex_precision", variant_rounded_to_antex_precision,
     "report the correction at the 0.01 mm precision at which ANTEX tabulates its "
     "own values"),
    ("bilinear_evaluated_zenith_first", variant_zenith_first_bilinear,
     "evaluate the bilinear interpolation in zenith angle first and azimuth second "
     "rather than azimuth first"),
]


def main():
    blocks = {}
    identity = {}
    for label, real_type, fname in ANTENNAS:
        src = os.path.join(SRC, fname)
        with open(src) as fh:
            lines = fh.readlines()
        for dest in ("oracle/antennas", "verifier/antennas",
                     "environment/skills/antex-receiver-antenna-calibration/references"):
            write_anonymised(os.path.join(ROOT, dest, "antenna_%s.atx" % label),
                             lines, label)
        blocks[label] = parse_antex(
            os.path.join(ROOT, "verifier", "antennas", "antenna_%s.atx" % label))
        identity[label] = {
            "igs20_antenna_type": real_type,
            "source": "https://files.igs.org/pub/station/general/igs20.atx",
            "retrieved": "2026-07-27",
            "frequency_blocks": len(blocks[label]["freqs"]),
            "dazi_deg": blocks[label]["dazi"],
            "zenith_grid_deg": [blocks[label]["zen1"], blocks[label]["zen2"],
                                blocks[label]["dzen"]],
        }
    nominal = parse_antex(os.path.join(SRC, NOMINAL[1]))

    # ---- instance selection ------------------------------------------------
    rng = random.Random(SEED)
    items = []
    for label, _type, _fname in ANTENNAS:
        block = blocks[label]
        for k, (code, _name) in enumerate(FREQS):
            while True:
                az = round(rng.uniform(0.0, 360.0), 1)
                el = round(rng.uniform(10.0, 75.0), 1)
                zen = 90.0 - el
                if min(az % block["dazi"], block["dazi"] - az % block["dazi"]) \
                        < NODE_GUARD_DEG:
                    continue
                if min(zen % block["dzen"], block["dzen"] - zen % block["dzen"]) \
                        < NODE_GUARD_DEG:
                    continue
                if abs(pcv_at(block, code, az, zen)) < PCV_FLOOR_MM:
                    continue
                break
            ref = round(correction(block, code, az, el), REF_DP)
            items.append({
                "antenna_id": label,
                "sight_id": "s%d" % (k + 1),
                "frequency_code": code,
                "azimuth_deg": az,
                "elevation_deg": el,
                "ref_correction_mm": ref,
                "tolerance_mm": TOL_MM,
            })

    expected = {
        "method": (
            "receiver-antenna phase-centre correction in millimetres: the antenna's own "
            "IGS20 mean phase-centre offset vector projected onto the line of sight in "
            "the local North/East/Up frame, plus the phase-centre variation interpolated "
            "bilinearly on that antenna's azimuth by zenith-angle grid at the same "
            "frequency"),
        "seed": SEED,
        "rounding_decimal_places": REF_DP,
        "freeze_tol_mm": 1e-06,
    }
    for it in items:
        stem = "%s_%s" % (it["antenna_id"], it["sight_id"])
        expected["ref_%s_correction_mm" % stem] = it["ref_correction_mm"]
        expected["tolerance_%s_correction_mm_abs" % stem] = it["tolerance_mm"]
    expected["items"] = items

    expected["antenna_detail"] = [
        {"antenna_id": lab,
         "frequency_blocks": len(blocks[lab]["freqs"]),
         "azimuth_step_deg": blocks[lab]["dazi"],
         "zenith_nodes": len(blocks[lab]["freqs"][FREQS[0][0]]["noazi"])}
        for lab, _t, _f in ANTENNAS
    ]

    # ---- control ledger, recomputed live so it cannot drift (V-18) ---------
    control_gaps = {}
    for name, fn, no_skill, description, competitor in CONTROLS:
        worst = min(abs(fn(blocks, nominal, it) - it["ref_correction_mm"])
                    / it["tolerance_mm"] for it in items)
        control_gaps[name] = {
            "description": description,
            "no_skill_route": no_skill,
            "correction_mm_gap_over_tol": round(worst, 3),
            "note": ("worst (smallest) separation over all %d cases, in tolerance units. "
                     % len(items) + competitor).strip(),
        }
    expected["control_gaps"] = control_gaps

    convention_variants = {}
    for name, fn, description in VARIANTS:
        worst = max(abs(fn(blocks, nominal, it) - it["ref_correction_mm"])
                    / it["tolerance_mm"] for it in items)
        convention_variants[name] = {
            "description": description,
            "worst_deviation_over_tol": round(worst, 3),
            "must_not_false_fail": True,
            "note": ("V-06 evidence: a defensible alternative reporting or evaluation "
                     "convention. It stays inside tolerance on every case, so it costs "
                     "no arm anything and is not part of the lever. The lever is the "
                     "per-antenna calibration block alone."),
        }
    expected["convention_variants"] = convention_variants

    non_separating = {}
    for name, fn, description in NON_SEPARATING:
        vals = [abs(fn(blocks, nominal, it) - it["ref_correction_mm"]) / it["tolerance_mm"]
                for it in items]
        non_separating[name] = {
            "description": description,
            "worst_case_gap_over_tol": round(min(vals), 3),
            "best_case_gap_over_tol": round(max(vals), 3),
            "in_control_ledger": False,
            "note": ("Measured and deliberately kept out of control_gaps: it fails to "
                     "clear the 2x-tolerance floor on at least one case, so counting it "
                     "as a control would overstate the separation (V-04). It stays in "
                     "the rubric failure-mode catalogue for attribution."),
        }
    expected["non_separating_routes"] = non_separating

    # ---- agent-visible data -------------------------------------------------
    with open(os.path.join(ROOT, "environment/data/antennas.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["antenna_id", "calibration_model", "correction_unit"])
        for label, _t, _f in ANTENNAS:
            w.writerow([label, "IGS20 absolute receiver-antenna model", "millimetre"])

    with open(os.path.join(ROOT, "environment/data/sightlines.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["antenna_id", "sight_id", "frequency_code", "frequency_label",
                    "azimuth_deg", "elevation_deg"])
        names = dict(FREQS)
        for it in items:
            w.writerow([it["antenna_id"], it["sight_id"], it["frequency_code"],
                        names[it["frequency_code"]],
                        "%.1f" % it["azimuth_deg"], "%.1f" % it["elevation_deg"]])

    decoy = {}
    for code, name in FREQS:
        n, e, u = nominal["freqs"][code]["pco"]
        decoy[code] = {"frequency_label": name, "north_mm": n, "east_mm": e, "up_mm": u}

    question = {
        "output_path": "/root/results.json",
        "cases": [{"antenna_id": it["antenna_id"], "sight_id": it["sight_id"],
                   "frequency_code": it["frequency_code"],
                   "azimuth_deg": it["azimuth_deg"],
                   "elevation_deg": it["elevation_deg"]} for it in items],
        "output_contract": {
            "phase_centre_correction_mm": {
                "<antenna_id>": {"<sight_id>": "number, correction in millimetres"}
            }
        },
        "method_note": (
            "For each case report the phase-centre correction in millimetres as "
            "(N*e_N + E*e_E + U*e_U) + PCV, where (N, E, U) is the antenna's mean "
            "phase-centre offset for that frequency in the local North/East/Up frame, "
            "e = (cos(el)*cos(az), cos(el)*sin(az), sin(el)) is the line-of-sight unit "
            "vector in the same frame with azimuth measured clockwise from geodetic "
            "north, and PCV is the antenna's phase-centre variation for that frequency "
            "at that azimuth and at the zenith angle 90 - el, taken bilinearly on the "
            "tabulated azimuth by zenith-angle grid."),
        "nominal_reference": {
            "note": ("Shown for orientation only. The nominal phase-centre offset for a "
                     "published geodetic antenna, in the local North/East/Up frame, at "
                     "each frequency code listed in this task."),
            "nominal_phase_centre_offset_mm": decoy,
        },
    }
    with open(os.path.join(ROOT, "environment/data/question.json"), "w") as fh:
        json.dump(question, fh, indent=2)
        fh.write("\n")

    # ---- grading artifacts --------------------------------------------------
    with open(os.path.join(ROOT, "verifier/expected_values.json"), "w") as fh:
        json.dump(expected, fh, indent=2)
        fh.write("\n")

    golden = {"phase_centre_correction_mm": {}}
    for it in items:
        golden["phase_centre_correction_mm"].setdefault(it["antenna_id"], {})[
            it["sight_id"]] = it["ref_correction_mm"]
    with open(os.path.join(ROOT, "verifier/golden.json"), "w") as fh:
        json.dump(golden, fh, indent=2)
        fh.write("\n")

    with open(os.path.join(ROOT, "build/antenna_map.json"), "w") as fh:
        json.dump({
            "note": ("Grader-side identity map. The agent-visible data name the antennas "
                     "ANT-A/ANT-B/ANT-C only; this file records which real IGS20 antenna "
                     "model each label is, so the constants stay citable without being "
                     "fetchable from the container."),
            "license": ("IGS products are made available to the public without charge or "
                        "restriction under the IGS data and product policy; the IGS asks "
                        "that the service be acknowledged."),
            "source": "https://files.igs.org/pub/station/general/igs20.atx",
            "antennas": identity,
            "nominal_reference_antenna": {
                "igs20_antenna_type": NOMINAL[0],
                "role": ("supplies the orientation offset shown in "
                         "environment/data/question.json; it is not one of the three "
                         "graded antennas"),
                "source": "https://files.igs.org/pub/station/general/igs20.atx",
                "retrieved": "2026-07-27",
            },
        }, fh, indent=2)
        fh.write("\n")

    print("items: %d" % len(items))
    for it in items:
        print("  %s %s %s az=%6.1f el=%5.1f  ref=%14.9f tol=%.4f"
              % (it["antenna_id"], it["sight_id"], it["frequency_code"],
                 it["azimuth_deg"], it["elevation_deg"],
                 it["ref_correction_mm"], it["tolerance_mm"]))
    print("\ncontrol gaps (worst, tolerance units):")
    for name, spec in control_gaps.items():
        print("  %-38s %9.2f" % (name, spec["correction_mm_gap_over_tol"]))
    print("convention variants (worst deviation, tolerance units):")
    for name, spec in convention_variants.items():
        print("  %-38s %9.3f" % (name, spec["worst_deviation_over_tol"]))
    print("non-separating routes (worst .. best, tolerance units):")
    for name, spec in non_separating.items():
        print("  %-38s %9.3f .. %.2f" % (name, spec["worst_case_gap_over_tol"],
                                         spec["best_case_gap_over_tol"]))


if __name__ == "__main__":
    main()
