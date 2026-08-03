#!/bin/bash
# Reference solution: ERZA-RB1 robust interlaboratory consensus.
# Pure-math (math.erf) implementation; no scipy. numpy is not required.
set -e
python3 << 'PY'
import json, math, statistics
from pathlib import Path

D = Path("/root/data")
meas = json.loads((D / "measurements.json").read_text())
q = json.loads((D / "question.json").read_text())
labs = meas["labs"]
Lstar = q["nominated_lab"]
C = 1.25          # ERZA-RB1 house clamp constant
U_FACTOR = 1.25   # ERZA-RB1 combined-uncertainty coverage factor

def phi(z):
    return math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)

def Phi(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

def beta_of_c(c):
    ew2 = (2.0*Phi(c) - 1.0) - 2.0*c*phi(c) + 2.0*c*c*(1.0 - Phi(c))
    return 1.0 / math.sqrt(ew2)

def median(xs):
    return statistics.median(xs)

def mad_scale(xs):
    m = median(xs)
    return 1.4826 * median([abs(x - m) for x in xs])

# 1. within-lab reduction: MEDIAN of each lab's replicates
lab_val = {k: median(v) for k, v in labs.items()}
vals = list(lab_val.values())
n = len(vals)

# 2-4. Algorithm-A IRLS at c=1.25 with beta(c) debias
b = beta_of_c(C)
assert round(b, 4) == 1.2288, b
x = median(vals)
s = mad_scale(vals)
for _ in range(60):
    lo, hi = x - C*s, x + C*s
    clamped = [min(max(v, lo), hi) for v in vals]
    x_new = sum(clamped) / n
    var = sum((v - x_new)**2 for v in clamped) / (n - 1)
    s_new = b * math.sqrt(var)
    if abs(x_new - x) < 1e-12 and abs(s_new - s) < 1e-12:
        x, s = x_new, s_new
        break
    x, s = x_new, s_new

# 5. combined uncertainty
u = U_FACTOR * s / math.sqrt(n)

# 6. outputs: robust scale s* and zeta' for the nominated lab
zeta = (lab_val[Lstar] - x) / u

out = {"robust_scale": round(s, 6), "zeta_prime": round(zeta, 6)}
Path("/root/results.json").write_text(json.dumps(out, indent=2) + "\n")
print("robust_scale =", out["robust_scale"], " zeta_prime =", out["zeta_prime"])
PY
