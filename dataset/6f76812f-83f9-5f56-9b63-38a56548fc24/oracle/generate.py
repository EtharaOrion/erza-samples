#!/usr/bin/env python3
"""Bake the observation record, the golden and the grading ledger.

Author-time only; never invoked inside the task container.  The differential
signal biases are read from the anonymised extracts of the published CAS/IGG
Bias-SINEX product that build/extract_dsb.py wrote; nothing in this file
invents a bias.  Everything else -- geometry, ionosphere, receiver noise -- is
a seeded simulation, so the record is synthetic but the calibration constants
that make it solvable are real.

Run from the bundle root:  python3 oracle/generate.py
"""
import csv
import datetime as dt
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import dsb  # noqa: E402
import tec  # noqa: E402

SEED_BASE = 20260514
# First offset from SEED_BASE whose baked record contains no faithful
# rendering of any reference value; found with --find-seed, whose only
# criterion is leak-freeness (it never inspects separation or tolerance).
SEED = 20260518
RNG_SIGMA_M = 0.12          # per-observable code scatter, metres
EPOCH_STEP_S = 60
N_EPOCHS = 121

STATION_SIGNALS = {
    "RX-1": ("C1C", "C2W"),
    "RX-2": ("C1W", "C2W"),
    "RX-3": ("C1C", "C2L"),
}
ARCS = {
    "RX-1": ["SV-K", "SV-P", "SV-R", "SV-W"],
    "RX-2": ["SV-M", "SV-R", "SV-T", "SV-W"],
    "RX-3": ["SV-K", "SV-M", "SV-P", "SV-T"],
}
WINDOW_START = {
    "RX-1": "2026-05-14T02:00:00Z",
    "RX-2": "2026-05-14T09:15:00Z",
    "RX-3": "2026-05-14T17:30:00Z",
}
# receiver clock offsets, metres -- common to both observables, cancels in the
# geometry-free combination; present only so the ranges look like a real file
CLOCK_OFFSET_M = {"RX-1": 41277.418, "RX-2": -18904.663, "RX-3": 7735.209}

ORBIT_ALT_M = 20200e3
EARTH_R_M = 6371.0e3
TOLERANCE_TECU = 0.05
FREEZE_EPS = 1e-9


def geometric_range(elev_deg):
    """Range to a circular orbit at ORBIT_ALT_M seen at this elevation."""
    s = np.sin(np.radians(elev_deg))
    r = EARTH_R_M + ORBIT_ALT_M
    return np.sqrt(EARTH_R_M ** 2 * s ** 2 + r ** 2 - EARTH_R_M ** 2) - EARTH_R_M * s


def tropo_delay(elev_deg):
    return 2.35 / np.sin(np.radians(elev_deg) + 0.065)


def build_arc_profiles(rng):
    """Elevation track and true vertical content for every arc."""
    profiles = {}
    for station, sats in ARCS.items():
        for sat in sats:
            # a monotone rising or setting pass, so the sampling is even in
            # elevation as well as in time
            u = np.linspace(-0.5, 0.5, N_EPOCHS)
            low = rng.uniform(42.0, 54.0)
            span = rng.uniform(20.0, 26.0)
            rising = bool(rng.integers(0, 2))
            elev = low + span * (u + 0.5) if rising else low + span * (0.5 - u)
            v0 = rng.uniform(12.0, 40.0)
            a1 = rng.uniform(-3.0, 3.0)
            a2 = rng.uniform(-0.6, 0.6)
            vtec_true = v0 + a1 * u + a2 * u * u
            profiles[(station, sat)] = (elev, vtec_true)
    return profiles


def total_bias_ns(sat_rows, rec_rows, signals):
    obs1, obs2 = signals
    return dsb.resolve(sat_rows, obs1, obs2) + dsb.resolve(rec_rows, obs1, obs2)


def build_rows(rng, sat_tables, rec_tables):
    """The baked observation rows, exactly as they are written to disk."""
    profiles = build_arc_profiles(rng)
    obs_rows = []
    for station in sorted(ARCS):
        t0 = dt.datetime.strptime(WINDOW_START[station], "%Y-%m-%dT%H:%M:%SZ")
        obs1, obs2 = STATION_SIGNALS[station]
        for sat in ARCS[station]:
            elev, vtec_true = profiles[(station, sat)]
            bias = total_bias_ns(sat_tables[sat], rec_tables[station],
                                 (obs1, obs2))
            oblique = np.array([tec.obliquity(e) for e in elev])
            stec_true = vtec_true / oblique
            n_e = stec_true * tec.TECU
            i1 = tec.KAPPA * n_e / tec.F1_HZ ** 2
            i2 = tec.KAPPA * n_e / tec.F2_HZ ** 2
            rho = geometric_range(elev) + tropo_delay(elev) + CLOCK_OFFSET_M[station]
            noise1 = rng.normal(0.0, RNG_SIGMA_M, N_EPOCHS)
            noise2 = rng.normal(0.0, RNG_SIGMA_M, N_EPOCHS)
            r1 = rho + i1 + noise1
            r2 = rho + i2 + noise2 - tec.C_LIGHT * bias * 1e-9
            for k in range(N_EPOCHS):
                stamp = (t0 + dt.timedelta(seconds=EPOCH_STEP_S * k))
                obs_rows.append({
                    "station_label": station,
                    "sv_label": sat,
                    "epoch_utc": stamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "range_l1_m": "%.3f" % r1[k],
                    "range_l2_m": "%.3f" % r2[k],
                    "elevation_deg": "%.3f" % elev[k],
                })
    return obs_rows


def _probe(seed, sat_tables, rec_tables):
    """Goldens and the record text for one candidate seed, without writing."""
    rows = build_rows(np.random.default_rng(seed), sat_tables, rec_tables)
    body = "\n".join(",".join(r[c] for c in (
        "station_label", "sv_label", "epoch_utc",
        "range_l1_m", "range_l2_m", "elevation_deg")) for r in rows)
    arcs = {}
    for r in rows:
        arcs.setdefault((r["station_label"], r["sv_label"]), []).append(
            (float(r["range_l1_m"]), float(r["range_l2_m"]),
             float(r["elevation_deg"])))
    golden = {}
    for station in sorted(ARCS):
        golden[station] = {}
        for sat in ARCS[station]:
            bias = total_bias_ns(sat_tables[sat], rec_tables[station],
                                 STATION_SIGNALS[station])
            golden[station][sat] = tec.arc_mean_vtec(arcs[(station, sat)], bias)
    return golden, body


def find_seed(span=400):
    """First seed whose record contains no faithful rendering of any reference.

    The ONLY criterion is leak-freeness of the baked record. Separation,
    tolerance and the control ledger are not consulted here, so this cannot
    select for a favourable result - only against an answer sitting in the
    agent's own input.
    """
    tables_dir = os.path.join(HERE, "dsb")
    sat_tables = {s: dsb.load_label(tables_dir, "sat", s)
                  for s in sorted({s for v in ARCS.values() for s in v})}
    rec_tables = {r: dsb.load_label(tables_dir, "rec", r) for r in sorted(ARCS)}
    for offset in range(span):
        seed = SEED_BASE + offset
        golden, body = _probe(seed, sat_tables, rec_tables)
        hits = leaked_forms(golden, {"observations.csv": body})
        print("seed %d: %d leaked rendering(s)%s"
              % (seed, len(hits), "" if hits else "   <- clean"))
        if not hits:
            return 0
    print("no clean seed within %d of %d" % (span, SEED_BASE))
    return 1


def faithful_forms(value, min_digits=3):
    """Every decimal rendering of `value` that round-trips faithfully.

    Mirrors the leak scanner's own rule: a rendering counts only if it recovers
    the value to within max(|v| * 1e-4, 5e-7), so a lossy rounding is not
    treated as a leak. Used to keep any reference value out of the baked record.
    """
    forms = {str(value), repr(float(value)), "%g" % float(value),
             "%e" % float(value)}
    f = float(value)
    if f.is_integer():
        forms.add(str(int(f)))
        forms.add("{:,}".format(int(f)))
    for prec in range(1, 7):
        forms.add("%.*f" % (prec, f))
    tol = max(abs(f) * 1e-4, 5e-7)
    out = set()
    for s in forms:
        if len(s.strip("-.")) < min_digits:
            continue
        try:
            if abs(float(s) - f) <= tol:
                out.add(s)
        except ValueError:
            continue
    return out


def leaked_forms(golden, texts):
    """Reference renderings that occur verbatim in the agent-visible record."""
    hits = []
    for station, block in golden.items():
        for sat, value in block.items():
            for form in sorted(faithful_forms(value)):
                for name, body in texts.items():
                    if form in body:
                        hits.append((station, sat, form, name))
    return hits


def main():
    if "--find-seed" in sys.argv:
        return find_seed()
    rng = np.random.default_rng(SEED)
    tables_dir = os.path.join(HERE, "dsb")
    sat_tables = {s: dsb.load_label(tables_dir, "sat", s)
                  for s in sorted({s for v in ARCS.values() for s in v})}
    rec_tables = {r: dsb.load_label(tables_dir, "rec", r) for r in sorted(ARCS)}

    # the chain used when the observed pair is absent must be unique
    for station, sats in ARCS.items():
        obs1, obs2 = STATION_SIGNALS[station]
        for table, name in ((rec_tables[station], station),
                            *[(sat_tables[s], s) for s in sats]):
            n = dsb.chain_count(table, obs1, obs2)
            if n > 1:
                raise SystemExit("chain for %s %s-%s is not unique (%d)"
                                 % (name, obs1, obs2, n))

    obs_rows = build_rows(rng, sat_tables, rec_tables)

    data_dir = os.path.join(ROOT, "environment", "data")
    with open(os.path.join(data_dir, "observations.csv"), "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=[
            "station_label", "sv_label", "epoch_utc",
            "range_l1_m", "range_l2_m", "elevation_deg"])
        writer.writeheader()
        writer.writerows(obs_rows)

    with open(os.path.join(data_dir, "receivers.csv"), "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["station_label", "l1_signal", "l2_signal",
                         "window_start_utc", "window_end_utc"])
        for station in sorted(ARCS):
            t0 = dt.datetime.strptime(WINDOW_START[station], "%Y-%m-%dT%H:%M:%SZ")
            t1 = t0 + dt.timedelta(seconds=EPOCH_STEP_S * (N_EPOCHS - 1))
            writer.writerow([station, *STATION_SIGNALS[station],
                             t0.strftime("%Y-%m-%dT%H:%M:%SZ"),
                             t1.strftime("%Y-%m-%dT%H:%M:%SZ")])

    # ---- read the baked files back and derive everything from them ----
    epochs = read_epochs(os.path.join(data_dir, "observations.csv"))
    golden, detail = {}, []
    for station in sorted(ARCS):
        golden[station] = {}
        for sat in ARCS[station]:
            bias = total_bias_ns(sat_tables[sat], rec_tables[station],
                                 STATION_SIGNALS[station])
            value = tec.arc_mean_vtec(epochs[(station, sat)], bias)
            golden[station][sat] = value
            arc = epochs[(station, sat)]
            detail.append({
                "station_label": station,
                "sv_label": sat,
                "n_epochs": len(arc),
                "elevation_min_deg": min(e[2] for e in arc),
                "elevation_max_deg": max(e[2] for e in arc),
                "mean_obliquity": sum(tec.obliquity(e[2]) for e in arc) / len(arc),
                "total_bias_ns": bias,
                "ref_arc_mean_vtec_tecu": value,
            })

    decoy = {}
    for station in sorted(ARCS):
        decoy[station] = {}
        for sat in ARCS[station]:
            arc = epochs[(station, sat)]
            vals = [tec.slant_tec(r1, r2, 0.0) for r1, r2, _ in arc]
            decoy[station][sat] = round(sum(vals) / len(vals), 3)

    question = {
        "output_path": "/root/results.json",
        "output_key": "arc_mean_vtec_tecu",
        "unit": "TECU (10^16 electrons per square metre)",
        "arcs": [{"station_label": s, "sv_label": v} for s in sorted(ARCS)
                 for v in ARCS[s]],
        "decoy_reference": {
            "description": (
                "Mean slant total electron content over each arc obtained "
                "straight from the recorded ranges, with no instrumental term "
                "removed and no slant-to-vertical reduction applied. Supplied "
                "for orientation."),
            "uncorrected_mean_slant_tec_tecu": decoy,
        },
    }
    with open(os.path.join(data_dir, "question.json"), "w") as fh:
        json.dump(question, fh, indent=2, sort_keys=True)
        fh.write("\n")

    with open(os.path.join(ROOT, "verifier", "golden.json"), "w") as fh:
        json.dump({"arc_mean_vtec_tecu": golden}, fh, indent=2, sort_keys=True)
        fh.write("\n")

    # hard anti-leak invariant: no faithful rendering of any reference value may
    # occur anywhere in what the agent reads (QC B-09).
    agent_visible = {}
    for name in ("observations.csv", "receivers.csv", "question.json"):
        with open(os.path.join(data_dir, name)) as fh:
            agent_visible[name] = fh.read()
    leaks = leaked_forms(golden, agent_visible)
    if leaks:
        raise SystemExit("reference value leaked into agent-visible input: %s"
                         % leaks[:5])

    expected = build_expected(epochs, sat_tables, rec_tables, golden, detail, decoy)
    with open(os.path.join(ROOT, "verifier", "expected_values.json"), "w") as fh:
        json.dump(expected, fh, indent=2, sort_keys=True)
        fh.write("\n")

    print("baked %d observation rows over %d arcs" % (len(obs_rows), len(detail)))
    for key, gap in sorted(expected["control_gaps"].items()):
        if "arc_mean_vtec_tecu_gap_over_tol" in gap:
            print("  control %-42s %8.2f x tol" % (
                key, gap["arc_mean_vtec_tecu_gap_over_tol"]))
    for key, gap in sorted(expected["convention_variants"].items()):
        print("  variant %-42s %8.4f x tol" % (
            key, gap["worst_deviation_over_tol"]))
    print("  BAND lo  defensible-reading spread   = %.6g TECU over %d draws"
          % (expected["published_precision_ambiguity_arc_mean_vtec_tecu_maxabs"],
             expected["published_precision_ambiguity_draws"]))
    print("  BAND lo  pinned-variant spread       = %.6g TECU"
          % expected["convention_variant_spread_arc_mean_vtec_tecu_maxabs"])
    print("  TOLERANCE                            = %.6g TECU" % TOLERANCE_TECU)
    print("  BAND hi  smallest wrong-path gap     = %.6g TECU over %d draws"
          % (expected["smallest_wrong_path_gap_arc_mean_vtec_tecu_minabs"],
             expected["smallest_wrong_path_gap_draws"]))


def read_epochs(path):
    epochs = {}
    with open(path) as fh:
        for row in csv.DictReader(fh):
            key = (row["station_label"], row["sv_label"])
            epochs.setdefault(key, []).append((
                float(row["range_l1_m"]), float(row["range_l2_m"]),
                float(row["elevation_deg"])))
    return epochs


# --------------------------------------------------------------------------
# alternative bias resolutions, used for the control ledger
# --------------------------------------------------------------------------
def alt_bias(kind, sat_rows, rec_rows, signals):
    """Total bias, ns, that a named wrong path would use. None = unaffected."""
    obs1, obs2 = signals
    true_sat = dsb.resolve(sat_rows, obs1, obs2)
    true_rec = dsb.resolve(rec_rows, obs1, obs2)
    if kind == "no_instrumental_term_removed":
        return 0.0
    if kind == "space_vehicle_entry_only":
        return true_sat
    if kind == "receiver_entry_only":
        return true_rec
    if kind == "removal_sign_reversed":
        return -(true_sat + true_rec)
    if kind == "chained_although_direct_row_present":
        def chained(rows):
            """Value obtained by chaining with the direct row struck out."""
            trimmed = {k: v for k, v in rows.items()
                       if k not in ((obs1, obs2), (obs2, obs1))}
            chains = dsb._shortest_chains(trimmed, obs1, obs2)
            if not chains:
                return None
            chains.sort(key=lambda c: (
                sum(1 for n in c[1:-1] if n not in dsb.REFERENCE_OBSERVABLES), c))
            return dsb._chain_value(trimmed, chains[0])
        direct_present = ((obs1, obs2) in sat_rows or (obs2, obs1) in sat_rows
                          or (obs1, obs2) in rec_rows or (obs2, obs1) in rec_rows)
        if not direct_present:
            return None
        cs, cr = chained(sat_rows), chained(rec_rows)
        if cs is None and cr is None:
            return None
        return (cs if cs is not None else true_sat) + \
               (cr if cr is not None else true_rec)
    if kind == "chain_terms_added_not_signed":
        def unsigned(rows, truth):
            if (obs1, obs2) in rows or (obs2, obs1) in rows:
                return truth
            chains = dsb._shortest_chains(rows, obs1, obs2)
            chains.sort(key=lambda c: (
                sum(1 for n in c[1:-1] if n not in dsb.REFERENCE_OBSERVABLES), c))
            chain = chains[0]
            total = 0.0
            for left, right in zip(chain, chain[1:]):
                total += rows[(left, right)] if (left, right) in rows \
                    else rows[(right, left)]
            return total
        us, ur = unsigned(sat_rows, true_sat), unsigned(rec_rows, true_rec)
        if abs(us - true_sat) + abs(ur - true_rec) < 1e-12:
            return None
        return us + ur
    if kind == "intra_frequency_step_skipped":
        sub1 = obs1 if obs1 in dsb.REFERENCE_OBSERVABLES else "C1W"
        sub2 = obs2 if obs2 in dsb.REFERENCE_OBSERVABLES else "C2W"
        if (sub1, sub2) == (obs1, obs2):
            return None
        return dsb.resolve(sat_rows, sub1, sub2) + dsb.resolve(rec_rows, sub1, sub2)
    raise KeyError(kind)


CONTROL_NOTES = {
    "no_instrumental_term_removed": (
        True,
        "reduce the recorded ranges straight to vertical content with no "
        "instrumental term removed at all -- the route an analyst without the "
        "published bias product is left with, and the one the orientation "
        "figure anchors. Not a strawman: it is the nearest producible "
        "alternative and it is what the standard textbook geometry-free "
        "expression gives when the bias term is unavailable."),
    "space_vehicle_entry_only": (
        False,
        "remove the space-vehicle entry and nothing else, leaving the receiver "
        "entry in the observable. A published competitor habit: single-station "
        "users routinely have satellite values and no receiver values."),
    "receiver_entry_only": (
        False,
        "remove the receiver entry only, leaving the space-vehicle term in."),
    "removal_sign_reversed": (
        False,
        "add the total entry to the geometry-free observable instead of "
        "removing it. This is the defensible-looking reading of a bias as a "
        "correction rather than as an error, and the standard's own numerical "
        "example is the only thing that settles it."),
    "chained_although_direct_row_present": (
        False,
        "rebuild every differential by chaining through the reference "
        "observables even where the product publishes the exact ordered pair. "
        "A genuinely defensible alternative convention -- the published rows "
        "are independent estimates and are not algebraically consistent, so "
        "the chained and direct values differ; it is pinned in the mounted "
        "reference so nobody who reads that reference can land here."),
    "chain_terms_added_not_signed": (
        False,
        "sum the magnitudes of the chained rows instead of following each "
        "row's own ordered-pair sign."),
    "intra_frequency_step_skipped": (
        False,
        "treat a non-reference observable as though it were the reference "
        "observable of its frequency, skipping the intra-frequency row."),
}


def build_expected(epochs, sat_tables, rec_tables, golden, detail, decoy):
    keys = [(s, v) for s in sorted(ARCS) for v in ARCS[s]]
    expected = {
        "method": (
            "per epoch, geometry-free code combination of the two reported "
            "ranges; the total differential signal bias for the reported "
            "observable pair (space-vehicle entry plus receiver entry, "
            "resolved against the published product) removed from it; the "
            "residual converted to slant content and reduced to vertical "
            "content with the single-layer obliquity factor; the arc value is "
            "the arithmetic mean of the per-epoch vertical content"),
        "seed": SEED,
        "freeze_tol_tecu": FREEZE_EPS,
        "graded_output": "arc_mean_vtec_tecu",
        "n_cases": len(keys),
    }
    for station, sat in keys:
        expected["ref_%s_%s_arc_mean_vtec_tecu" % (station, sat)] = golden[station][sat]
        expected["tolerance_%s_%s_arc_mean_vtec_tecu_abs" % (station, sat)] = \
            TOLERANCE_TECU
    expected["items"] = [{
        "station_label": s, "sv_label": v,
        "ref_arc_mean_vtec_tecu": golden[s][v],
        "tolerance_tecu": TOLERANCE_TECU,
    } for s, v in keys]
    expected["arc_detail"] = detail

    # ---- control ledger: recomputed live, never trusted from a note ----
    controls, variants = {}, {}
    for kind, (no_skill, note) in CONTROL_NOTES.items():
        gaps = []
        for station, sat in keys:
            alt = alt_bias(kind, sat_tables[sat], rec_tables[station],
                           STATION_SIGNALS[station])
            if alt is None:
                continue
            value = tec.arc_mean_vtec(epochs[(station, sat)], alt)
            gaps.append(abs(value - golden[station][sat]))
        if not gaps:
            raise SystemExit("route %s alters no arc" % kind)
        worst = min(gaps) / TOLERANCE_TECU
        entry = {
            "description": note.split(".")[0],
            "note": note + " Figure is the worst (smallest) separation over the "
                          "%d of %d arcs this route alters; the remaining arcs "
                          "are untouched by it." % (len(gaps), len(keys)),
            "arcs_altered": len(gaps),
        }
        if no_skill:
            entry["no_skill_route"] = True
        if worst >= 2.0:
            entry["arc_mean_vtec_tecu_gap_over_tol"] = round(worst, 3)
            controls[kind] = entry
        else:
            entry["worst_deviation_over_tol"] = round(worst, 4)
            entry["must_not_false_fail"] = True
            variants[kind] = entry

    # echoing the orientation figure
    gaps = [abs(decoy[s][v] - golden[s][v]) for s, v in keys]
    controls["orientation_figure_echoed"] = {
        "description": "report the uncorrected slant figure supplied for orientation",
        "note": "report the orientation figure from question.json unchanged. "
                "Worst (smallest) separation over all %d arcs." % len(keys),
        "no_skill_route": True,
        "arcs_altered": len(keys),
        "arc_mean_vtec_tecu_gap_over_tol": round(min(gaps) / TOLERANCE_TECU, 3),
    }

    # a reduction convention that is defensible and must NOT false-fail:
    # weighting each epoch by its obliquity instead of averaging plainly
    dev = []
    for station, sat in keys:
        arc = epochs[(station, sat)]
        bias = dsb.resolve(sat_tables[sat], *STATION_SIGNALS[station]) + \
            dsb.resolve(rec_tables[station], *STATION_SIGNALS[station])
        vals = [tec.vertical_tec(r1, r2, el, bias) for r1, r2, el in arc]
        mid = sorted(vals)[len(vals) // 2] if len(vals) % 2 else \
            0.5 * (sorted(vals)[len(vals) // 2 - 1] + sorted(vals)[len(vals) // 2])
        del mid
        half = sum(vals[1:-1]) + 0.5 * (vals[0] + vals[-1])
        trapezoid = half / (len(vals) - 1)
        dev.append(abs(trapezoid - golden[station][sat]))
    variants["trapezoidal_arc_average"] = {
        "description": "average the per-epoch vertical content trapezoidally "
                       "over the evenly spaced arc rather than plainly",
        "note": "a defensible alternative reduction convention on an evenly "
                "sampled arc; the prompt pins the plain arithmetic mean, so "
                "this costs the unaided arm nothing and is not part of the "
                "lever.",
        "worst_deviation_over_tol": round(max(dev) / TOLERANCE_TECU, 4),
        "must_not_false_fail": True,
    }
    expected["control_gaps"] = controls
    expected["convention_variants"] = variants

    band, draws = published_precision_band(epochs, sat_tables, rec_tables, golden)
    expected["published_precision_ambiguity_arc_mean_vtec_tecu_maxabs"] = band
    expected["published_precision_ambiguity_draws"] = draws
    expected["tolerance_arc_mean_vtec_tecu_abs"] = TOLERANCE_TECU

    gap_lo, gap_draws, variant_hi = wrong_path_band(
        epochs, sat_tables, rec_tables, golden, list(CONTROL_NOTES))
    expected["smallest_wrong_path_gap_arc_mean_vtec_tecu_minabs"] = gap_lo
    expected["smallest_wrong_path_gap_draws"] = gap_draws
    expected["convention_variant_spread_arc_mean_vtec_tecu_maxabs"] = variant_hi

    smallest = min(
        [g["arc_mean_vtec_tecu_gap_over_tol"] for g in controls.values()])
    expected["tolerance_rationale"] = (
        "One absolute tolerance, %.3f TECU, on the single graded quantity. "
        "LOWER BOUND (defensible-reading spread): over %d draws that jitter "
        "every consumed bias row inside the half-ulp of its printed precision "
        "and swap the ionospheric constant and the shell radius for their "
        "common alternative spellings, two faithful readings of the same "
        "published inputs never differ by more than %.3e TECU; the widest "
        "pinned-convention variant (trapezoidal instead of plain arc "
        "averaging) adds %.3e TECU. The tolerance sits %.1fx above the larger "
        "of the two. UPPER BOUND (smallest wrong-path gap): over %d draws of "
        "the same jitter, the closest any named wrong path in control_gaps "
        "ever comes to the reference on any arc is %.3f TECU, which is %.1fx "
        "the tolerance; the deterministic worst case is %.2fx. The ordering "
        "that matters is spread %.3e < variant %.3e < tolerance %.3f < gap "
        "%.3f: %.1fx of headroom above the reading spread, %.1fx above the "
        "widest pinned variant, %.1fx below the closest wrong path. Routes "
        "that do not separate are recorded under convention_variants, never "
        "here, and must not false-fail."
        % (TOLERANCE_TECU, draws, band, variant_hi,
           TOLERANCE_TECU / max(band, variant_hi), gap_draws, gap_lo,
           gap_lo / TOLERANCE_TECU, smallest, band, variant_hi,
           TOLERANCE_TECU, gap_lo, TOLERANCE_TECU / band,
           TOLERANCE_TECU / variant_hi, gap_lo / TOLERANCE_TECU))
    return expected


def wrong_path_band(epochs, sat_tables, rec_tables, golden, kinds, draws=120):
    """Closest approach of any named wrong path, under reading jitter."""
    rng = np.random.default_rng(SEED + 2)
    keys = [(s, v) for s in sorted(ARCS) for v in ARCS[s]]
    closest = float("inf")
    variant_worst = 0.0
    for _ in range(draws):
        js = {s: {k: v + rng.uniform(-5e-5, 5e-5) for k, v in rows.items()}
              for s, rows in sat_tables.items()}
        jr = {r: {k: v + rng.uniform(-5e-5, 5e-5) for k, v in rows.items()}
              for r, rows in rec_tables.items()}
        for station, sat in keys:
            arc = epochs[(station, sat)]
            for kind in kinds:
                alt = alt_bias(kind, js[sat], jr[station],
                               STATION_SIGNALS[station])
                if alt is None:
                    continue
                value = tec.arc_mean_vtec(arc, alt)
                closest = min(closest, abs(value - golden[station][sat]))
            bias = dsb.resolve(js[sat], *STATION_SIGNALS[station]) + \
                dsb.resolve(jr[station], *STATION_SIGNALS[station])
            vals = [tec.vertical_tec(r1, r2, el, bias) for r1, r2, el in arc]
            trapezoid = (sum(vals[1:-1]) + 0.5 * (vals[0] + vals[-1])) \
                / (len(vals) - 1)
            variant_worst = max(variant_worst,
                                abs(trapezoid - golden[station][sat]))
    return closest, draws, variant_worst


def published_precision_band(epochs, sat_tables, rec_tables, golden, draws=200):
    """Widest |dVTEC| between two faithful readings of the same inputs."""
    rng = np.random.default_rng(SEED + 1)
    keys = [(s, v) for s in sorted(ARCS) for v in ARCS[s]]
    worst = 0.0
    for _ in range(draws):
        jitter_sat = {s: {k: v + rng.uniform(-5e-5, 5e-5)
                          for k, v in rows.items()}
                      for s, rows in sat_tables.items()}
        jitter_rec = {r: {k: v + rng.uniform(-5e-5, 5e-5)
                          for k, v in rows.items()}
                      for r, rows in rec_tables.items()}
        kappa = rng.choice([40.3082, 40.3, 40.30821, 40.308])
        radius = rng.choice([6371.0, 6378.137, 6371.008])
        for station, sat in keys:
            bias = dsb.resolve(jitter_sat[sat], *STATION_SIGNALS[station]) + \
                dsb.resolve(jitter_rec[station], *STATION_SIGNALS[station])
            value = variant_arc_mean(epochs[(station, sat)], bias, kappa, radius)
            worst = max(worst, abs(value - golden[station][sat]))
    return worst, draws


def variant_arc_mean(arc, bias_ns, kappa, radius_km):
    import math
    scale = (tec.F1_HZ ** 2 * tec.F2_HZ ** 2
             / (kappa * (tec.F1_HZ ** 2 - tec.F2_HZ ** 2)) / tec.TECU)
    ratio = radius_km / (radius_km + tec.SHELL_HEIGHT_KM)
    out = []
    for r1, r2, el in arc:
        stec = -scale * ((r1 - r2) - tec.C_LIGHT * bias_ns * 1e-9)
        sin_zp = ratio * math.cos(math.radians(el))
        out.append(stec * math.sqrt(1.0 - sin_zp * sin_zp))
    return sum(out) / len(out)


if __name__ == "__main__":
    main()
