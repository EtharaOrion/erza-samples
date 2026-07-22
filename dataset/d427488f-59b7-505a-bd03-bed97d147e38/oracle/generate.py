#!/usr/bin/env python3
"""PRIVATE deterministic data generator for the ERZA-RB1 robust-consensus task.

Emits the agent-visible inputs (environment/data/measurements.json and
environment/data/question.json) and the hidden golden / control ledger
(verifier/expected_values.json). Regenerating with the same seed reproduces
byte-identical inputs and reference values. Uses numpy only for the seeded RNG;
the ERZA-RB1 computation itself is pure-math (math.erf), no scipy.

Run:  python3 oracle/generate.py
"""
import json
import math
import statistics
from pathlib import Path

import numpy as np

SEED = 20260720
ANALYTE = "copper mass fraction in a leaded-bronze certified reference material"
UNITS = "% (mass fraction)"
NOMINATED_LAB = "L03"
C_CONST = 1.25
U_FACTOR = 1.25
TOL_SCALE = 0.004
TOL_ZETA = 0.03


# ------------------------- ERZA-RB1 core (pure math) -------------------------
def _phi(z):
    return math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)


def _Phi(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def beta_of_c(c):
    ew2 = (2.0 * _Phi(c) - 1.0) - 2.0 * c * _phi(c) + 2.0 * c * c * (1.0 - _Phi(c))
    return 1.0 / math.sqrt(ew2)


def _median(xs):
    return statistics.median(xs)


def _mad_scale(xs):
    m = _median(xs)
    return 1.4826 * _median([abs(x - m) for x in xs])


def algorithm_a(vals, c, debias=True, tol=1e-12, cap=60):
    n = len(vals)
    x = _median(vals)
    s = _mad_scale(vals)
    if s == 0:
        s = statistics.pstdev(vals) or 1.0
    b = beta_of_c(c) if debias else 1.0
    for _ in range(cap):
        lo, hi = x - c * s, x + c * s
        clamped = [min(max(v, lo), hi) for v in vals]
        x_new = sum(clamped) / n
        var = sum((v - x_new) ** 2 for v in clamped) / (n - 1)
        s_new = b * math.sqrt(var)
        if abs(x_new - x) < tol and abs(s_new - s) < tol:
            x, s = x_new, s_new
            break
        x, s = x_new, s_new
    return x, s


def erza_rb1(lab_values, lab_star_value, c=C_CONST):
    xstar, sstar = algorithm_a(lab_values, c, debias=True)
    N = len(lab_values)
    u = U_FACTOR * sstar / math.sqrt(N)
    zeta = (lab_star_value - xstar) / u
    return xstar, sstar, u, zeta


# ------------------------------ data generation ------------------------------
def generate_labs(seed=SEED):
    rng = np.random.default_rng(seed)
    mu0, sig_between, sig_within, n_labs = 5.00, 0.18, 0.045, 22
    ids = [f"L{i:02d}" for i in range(1, n_labs + 1)]
    outlier_labs = {"L05": +0.95, "L13": -1.15, "L19": +1.35}
    spike_labs = {"L08": +0.85, "L03": -0.75}
    labs = {}
    for lid in ids:
        center = mu0 + rng.normal(0, sig_between)
        if lid in outlier_labs:
            center = mu0 + outlier_labs[lid]
        reps = list(center + rng.normal(0, sig_within, 5))
        if lid in spike_labs:
            reps[int(rng.integers(0, 5))] += spike_labs[lid]
        labs[lid] = [round(float(r), 4) for r in reps]
    return labs


def main():
    here = Path(__file__).resolve().parent.parent
    data_dir = here / "environment" / "data"
    ver_dir = here / "verifier"
    data_dir.mkdir(parents=True, exist_ok=True)
    ver_dir.mkdir(parents=True, exist_ok=True)

    labs = generate_labs()
    lab_med = {k: _median(v) for k, v in labs.items()}
    lab_mean = {k: sum(v) / len(v) for k, v in labs.items()}
    med_vals = list(lab_med.values())
    mean_vals = list(lab_mean.values())
    n = len(labs)

    xstar, sstar, u, zeta = erza_rb1(med_vals, lab_med[NOMINATED_LAB])

    # decoy attractors (naive interlaboratory summary)
    grand_mean = sum(mean_vals) / n
    plain_sd = statistics.stdev(mean_vals)
    standard_z = (lab_mean[NOMINATED_LAB] - grand_mean) / plain_sd

    # controls
    _, sm, _, zm = erza_rb1(mean_vals, lab_mean[NOMINATED_LAB])
    xnd, snd = algorithm_a(med_vals, C_CONST, debias=False)
    und = U_FACTOR * snd / math.sqrt(n)
    znd = (lab_med[NOMINATED_LAB] - xnd) / und
    xh, sh = algorithm_a(med_vals, 1.5, debias=True)
    uh = U_FACTOR * sh / math.sqrt(n)
    zh = (lab_med[NOMINATED_LAB] - xh) / uh

    # ---- agent-visible: measurements.json ----
    measurements = {
        "analyte": ANALYTE,
        "units": UNITS,
        "replicates_per_lab": 5,
        "n_labs": n,
        "labs": labs,
    }
    (data_dir / "measurements.json").write_text(json.dumps(measurements, indent=2) + "\n")

    # ---- agent-visible: question.json ----
    question = {
        "analyte": ANALYTE,
        "units": UNITS,
        "n_labs": n,
        "replicates_per_lab": 5,
        "nominated_lab": NOMINATED_LAB,
        "output_path": "/root/results.json",
        "output_contract": {
            "robust_scale": (
                "the ERZA-RB1 robust between-laboratory scale s* for the round, "
                "in the analyte units, a single number"
            ),
            "zeta_prime": (
                "the ERZA-RB1 zeta-prime performance score for the nominated lab, "
                "dimensionless, a single number"
            ),
        },
        "decoy_reference": {
            "note": (
                "Quick classical interlaboratory summary provided for orientation "
                "ONLY. This is the naive plain-mean/standard-deviation route and is "
                "NOT the ERZA-RB1 answer; do not report these values."
            ),
            "plain_mean_scale": round(plain_sd, 6),
            "standard_z_nominated_lab": round(standard_z, 6),
        },
    }
    (data_dir / "question.json").write_text(json.dumps(question, indent=2) + "\n")

    # ---- hidden golden + control ledger: expected_values.json ----
    expected = {
        "ref_robust_scale": round(sstar, 6),
        "ref_zeta_prime": round(zeta, 6),
        "tolerance_robust_scale_abs": TOL_SCALE,
        "tolerance_zeta_prime_abs": TOL_ZETA,
        "nominated_lab": NOMINATED_LAB,
        "n_labs": n,
        "method_c_constant": C_CONST,
        "beta_of_c": round(beta_of_c(C_CONST), 4),
        "uncertainty_factor": U_FACTOR,
        "ref_location_xstar": round(xstar, 6),
        "ref_combined_uncertainty_u": round(u, 6),
        "decoy_plain_mean_scale": round(plain_sd, 6),
        "decoy_standard_z": round(standard_z, 6),
        "control_gaps": {
            "naive": {
                "scale_gap": round(abs(plain_sd - sstar), 6),
                "scale_gap_over_tol": round(abs(plain_sd - sstar) / TOL_SCALE, 2),
                "zeta_gap": round(abs(standard_z - zeta), 6),
                "zeta_gap_over_tol": round(abs(standard_z - zeta) / TOL_ZETA, 2),
            },
            "mean_reduction": {
                "scale_gap": round(abs(sm - sstar), 6),
                "scale_gap_over_tol": round(abs(sm - sstar) / TOL_SCALE, 2),
                "zeta_gap": round(abs(zm - zeta), 6),
                "zeta_gap_over_tol": round(abs(zm - zeta) / TOL_ZETA, 2),
            },
            "no_beta_debias": {
                "scale_gap": round(abs(snd - sstar), 6),
                "scale_gap_over_tol": round(abs(snd - sstar) / TOL_SCALE, 2),
                "zeta_gap": round(abs(znd - zeta), 6),
                "zeta_gap_over_tol": round(abs(znd - zeta) / TOL_ZETA, 2),
            },
            "huber_clamp_c1p5": {
                "scale_gap": round(abs(sh - sstar), 6),
                "scale_gap_over_tol": round(abs(sh - sstar) / TOL_SCALE, 2),
                "zeta_gap": round(abs(zh - zeta), 6),
                "zeta_gap_over_tol": round(abs(zh - zeta) / TOL_ZETA, 2),
                "note": "WEAK/decorative lever; fails both outputs only marginally by design",
            },
        },
        "method": (
            "ERZA-RB1: within-lab median reduction; Algorithm-A IRLS at c=1.25 with "
            "beta(c) debias (Phi/phi via math.erf); combined uncertainty u=1.25*s*/sqrt(N); "
            "zeta_prime=(x_Lstar - x*)/u"
        ),
    }
    (ver_dir / "expected_values.json").write_text(json.dumps(expected, indent=2) + "\n")

    # ---- validation report to stdout ----
    print(f"beta(1.25)={beta_of_c(1.25):.4f}  beta(1.5)={beta_of_c(1.5):.4f}")
    print(f"GOLDEN robust_scale={sstar:.6f}  zeta_prime={zeta:.6f}  x*={xstar:.6f}  u={u:.6f}")
    for name, ws, wz in [
        ("naive", plain_sd, standard_z),
        ("mean-reduce", sm, zm),
        ("no-debias", snd, znd),
        ("huber1.5", sh, zh),
    ]:
        ga, gz = abs(ws - sstar), abs(wz - zeta)
        print(
            f"  {name:12s} scaleGap={ga:.4f} ({ga/TOL_SCALE:5.1f}x)  "
            f"zetaGap={gz:.4f} ({gz/TOL_ZETA:6.1f}x)"
        )


if __name__ == "__main__":
    main()
