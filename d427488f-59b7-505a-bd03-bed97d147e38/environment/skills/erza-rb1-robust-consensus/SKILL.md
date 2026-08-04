---
name: erza-rb1-robust-consensus
description: Compute an interlaboratory proficiency-testing consensus with the ERZA-RB1 house robust method - within-lab median reduction, an Algorithm-A style iteratively reweighted (clamped) robust location and scale with the ERZA-RB1 clamp constant and its analytic bias-correction factor beta(c), a combined standard uncertainty of the assigned value, and a robust zeta-prime performance score for a nominated laboratory. Use when a task gives replicate measurements from many labs and asks for the ERZA-RB1 robust scale and/or a zeta-prime score. Not for the naive plain-mean / sample-standard-deviation / standard-z summary, and not for classical grand-mean ANOVA consensus.
license: MIT
---

# ERZA-RB1 robust interlaboratory consensus

ERZA-RB1 is a bespoke house standard operating procedure for proficiency-testing
rounds. It is deliberately robust: gross-outlier labs and single spurious replicates
must not move the assigned value or its uncertainty. You cannot read the answer off a
plain mean and sample standard deviation - those are inflated by the very outliers the
method is designed to reject, and they are only a decoy here.

The method is **procedure-defined**: the answer depends only on the multiset of lab
records and which lab is nominated, never on lab names or ordering.

## Step 1 - within-lab reduction (median, not mean)

Reduce each laboratory's replicate vector to a single value using the **median** of its
replicates, not the mean. The median ignores a single spiked replicate; the mean does
not. This choice is load-bearing - a mean reduction changes the reported per-lab value
whenever a lab has an odd replicate.

```python
lab_value = {lab: median(replicates) for lab, replicates in labs.items()}
vals = list(lab_value.values())
n = len(vals)
```

## Step 2 - the ERZA-RB1 clamp constant

ERZA-RB1 fixes the clamp (winsorizing) constant as a house parameter:

```
c = 1.25
```

It is a fixed constant of the SOP, not something you fit from the data. (It is a
comparatively weak lever - a nearby clamp gives a similar scale because the
bias-correction in Step 4 keeps the estimator consistent - but you must use the house
value for a conforming result.)

## Step 3 - Algorithm-A robust location and scale (iterate to convergence)

Estimate the robust location `x*` and robust scale `s*` by iteratively clamping each
lab value to a band around the current location, then recomputing:

```python
x = median(vals)
s = 1.4826 * median([abs(v - x) for v in vals])   # MAD-based start
for _ in range(60):                                # cap iterations
    lo, hi = x - c*s, x + c*s
    clamped = [min(max(v, lo), hi) for v in vals]  # winsorize to the band
    x_new = sum(clamped) / n                        # location = mean of clamped
    var = sum((v - x_new)**2 for v in clamped) / (n - 1)
    s_new = beta_c * sqrt(var)                       # scale = debiased sd of clamped
    if abs(x_new - x) < 1e-12 and abs(s_new - s) < 1e-12:
        x, s = x_new, s_new; break
    x, s = x_new, s_new
```

- Location update is the **mean of the clamped values**.
- Scale update is the sample standard deviation of the clamped values, then multiplied
  by the bias-correction factor `beta_c` from Step 4. Converge on both `x` and `s`
  (tolerance ~1e-12), capping the iterations.

## Step 4 - the analytic bias-correction beta(c)

Clamping (winsorizing) shrinks the variance, so the clamped standard deviation
under-estimates the true scale. ERZA-RB1 corrects it with the closed-form Fisher
consistency factor for a symmetrically clamped standard normal:

```
E[W^2] = (2*Phi(c) - 1) - 2*c*phi(c) + 2*c^2*(1 - Phi(c))
beta(c) = 1 / sqrt(E[W^2])
```

where `Phi` and `phi` are the standard-normal CDF and PDF. Compute them from the error
function - `phi(z) = exp(-z^2/2)/sqrt(2*pi)` and `Phi(z) = 0.5*(1 + erf(z/sqrt(2)))`
(`math.erf`); no special-function library is needed. **Omitting beta biases the scale
low** and corrupts every downstream number. Evaluate `beta(c)` at the house `c` and
carry it as `beta_c` in Step 3.

## Step 5 - combined standard uncertainty of the assigned value

The assigned-value combined standard uncertainty uses the ERZA-RB1 coverage factor:

```
u = 1.25 * s* / sqrt(n)
```

with `n` the number of participating labs.

## Step 6 - the outputs

- **Robust scale**: report `s*` from Step 3 (the robust between-lab scale). This is the
  round's dispersion estimate - not the location `x*`, and not `u`.
- **zeta-prime** for the nominated lab `L*`:

```
zeta' = (x_Lstar - x*) / u
```

where `x_Lstar` is that lab's **Step-1 median value** and `x*`, `u` are the robust
location and combined uncertainty above. A `|zeta'|` near or below ~2 is consistent
performance; larger magnitudes flag the lab.

## Sanity checks

- The robust scale is typically much **smaller** than the plain sample standard
  deviation of the lab means when gross outliers are present - if they are equal you
  probably skipped the robust iteration.
- `beta(c) > 1` always (it inflates the shrunken scale). If your `beta` is below 1 the
  formula is inverted.
- zeta-prime uses the **median** lab value and the **robust** `u`; using the lab mean or
  the plain standard deviation gives the decoy standard-z instead.
