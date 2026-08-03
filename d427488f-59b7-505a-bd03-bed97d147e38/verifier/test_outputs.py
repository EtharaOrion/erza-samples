"""Outcome tests for the ERZA-RB1 robust-consensus task.

Ground truth is the ERZA-RB1 house method (expected_values.json), NOT the naive
plain-mean / standard-deviation / standard-z summary carried as a decoy in
question.json. Reporting the decoy, reducing each lab by the mean instead of the
median, omitting the beta(c) debias, or using a different clamp all miss at least
one tolerance.

Test (d) is an anti-memorization control: it recomputes the reference on a
bijectively RELABELLED instance (lab IDs permuted, values and the nominated-lab
mapping preserved) and asserts the answer is invariant, documenting that the
reference is procedure-defined rather than tied to instance lab names.
"""
import json
import math
import random
import statistics
from pathlib import Path

import pytest

RESULTS = Path("/root/results.json")
EXPECTED = Path("/verifier/expected_values.json")
MEAS = Path("/root/data/measurements.json")


@pytest.fixture(scope="module")
def cfg():
    return json.loads(EXPECTED.read_text())


@pytest.fixture(scope="module")
def res():
    d = json.loads(RESULTS.read_text())
    assert "robust_scale" in d, "results.json must have key 'robust_scale'"
    assert "zeta_prime" in d, "results.json must have key 'zeta_prime'"
    return {"robust_scale": float(d["robust_scale"]), "zeta_prime": float(d["zeta_prime"])}


# ----------------------- (a) plausibility guards -----------------------
def test_plausible(res):
    s = res["robust_scale"]
    z = res["zeta_prime"]
    assert 0.0 < s < 5.0, f"robust_scale {s} outside plausible range"
    assert -20.0 < z < 20.0, f"zeta_prime {z} outside plausible range"


# ----------------------- (b) robust-scale tolerance -----------------------
def test_robust_scale(cfg, res):
    ref = float(cfg["ref_robust_scale"])
    tol = float(cfg["tolerance_robust_scale_abs"])
    err = abs(res["robust_scale"] - ref)
    assert err <= tol, f"robust_scale {res['robust_scale']:.6f} off ref {ref:.6f} by {err:.6f} (tol {tol})"


# ----------------------- (c) zeta-prime tolerance -----------------------
def test_zeta_prime(cfg, res):
    ref = float(cfg["ref_zeta_prime"])
    tol = float(cfg["tolerance_zeta_prime_abs"])
    err = abs(res["zeta_prime"] - ref)
    assert err <= tol, f"zeta_prime {res['zeta_prime']:.6f} off ref {ref:.6f} by {err:.6f} (tol {tol})"


# ---- ERZA-RB1 recomputation for the isomorphic-invariance control ----
def _phi(z):
    return math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)


def _Phi(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _beta_of_c(c):
    ew2 = (2.0 * _Phi(c) - 1.0) - 2.0 * c * _phi(c) + 2.0 * c * c * (1.0 - _Phi(c))
    return 1.0 / math.sqrt(ew2)


def _erza_rb1(labs, lstar, c=1.25, ufac=1.25):
    lab_val = {k: statistics.median(v) for k, v in labs.items()}
    vals = list(lab_val.values())
    n = len(vals)
    b = _beta_of_c(c)
    m = statistics.median(vals)
    x = m
    s = 1.4826 * statistics.median([abs(v - m) for v in vals])
    for _ in range(60):
        lo, hi = x - c * s, x + c * s
        clamped = [min(max(v, lo), hi) for v in vals]
        xn = sum(clamped) / n
        var = sum((v - xn) ** 2 for v in clamped) / (n - 1)
        sn = b * math.sqrt(var)
        if abs(xn - x) < 1e-12 and abs(sn - s) < 1e-12:
            x, s = xn, sn
            break
        x, s = xn, sn
    u = ufac * s / math.sqrt(n)
    return s, (lab_val[lstar] - x) / u


# ----------------------- (d) IPT isomorphic-invariance control -----------------------
def test_isomorphic_invariance(cfg):
    meas = json.loads(MEAS.read_text())
    labs = meas["labs"]
    lstar = cfg["nominated_lab"]

    # reference recomputed directly on the shipped instance
    s0, z0 = _erza_rb1(labs, lstar)

    # bijective relabel: permute lab IDs, preserve values and the L* mapping
    rng = random.Random(4242)
    old = list(labs.keys())
    new = old[:]
    rng.shuffle(new)
    remap = dict(zip(old, new))
    relabelled = {remap[k]: v for k, v in labs.items()}
    s1, z1 = _erza_rb1(relabelled, remap[lstar])

    assert abs(s1 - s0) < 1e-12, f"robust_scale not invariant under relabel: {s0} vs {s1}"
    assert abs(z1 - z0) < 1e-12, f"zeta_prime not invariant under relabel: {z0} vs {z1}"
    # and the invariant recomputation must agree with the shipped reference
    assert abs(s0 - float(cfg["ref_robust_scale"])) <= 5e-6, "recomputed scale disagrees with stored reference"
    assert abs(z0 - float(cfg["ref_zeta_prime"])) <= 5e-6, "recomputed zeta disagrees with stored reference"
