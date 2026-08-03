# TRUTH — golden trajectory for task `d427488f-59b7-505a-bd03-bed97d147e38`
# (ERZA-RB1 robust interlaboratory consensus)

**What this is.** The ordered moves a competent run makes, from opening the
task to writing the answer. Each step says *what to do and why*. **No step
states what it evaluates to** — this file names no lab value, no consensus
location, no scale, no zeta score.

**Derived from the oracle.** Every transformation below is `oracle/solve.sh`
transcribed as instructions, in the oracle's order. Method constants are kept:
the house clamp constant, the coverage factor, the MAD consistency factor and
the bias-correction relation are constants *inside the procedure* — they define
ERZA-RB1 and without them this document is not followable. Nothing read from
this task's input files, and nothing a step computes from them, appears
anywhere here.

**What it is for.** The spec the process rubric derives from and the context
the LLM judge reads. A grader artifact, never shown to the agent.

---

## Step 0 — Read the inputs and notice the decoy

**Do:** Open `/root/data/measurements.json` (the labs and their five
replicates each) and `/root/data/question.json` (the nominated laboratory
`L*`, the output contract, and a `decoy_reference` block). Read the decoy
block's own note: it is a quick classical plain-mean / standard-deviation /
standard-z summary supplied for orientation **only**.

**Why:** The decoy is the task's designed attractor — two plausible numbers in
the input, shaped exactly like the two numbers the contract asks for.
Reporting them, or landing on them by running the classical computation, is
the cheapest wrong answer available.

**Do not:** Report either decoy value, or use closeness to them as evidence of
correctness.

---

## Step 1 — Reduce each laboratory to one value, by the MEDIAN

**Do:** For each lab, take the **median** of its five replicate
determinations. Carry one value per lab forward; do the same for the nominated
lab `L*`.

**Why:** ERZA-RB1 reduces within-lab first so the between-lab step sees one
value per laboratory, and it reduces by the median so that a single spiked
replicate cannot move a lab's value. The shipped round contains labs whose
replicate sets carry exactly such single-replicate spikes; reducing by the
**mean** lets the spike through, and the nominated lab's own set is one of the
spiked ones — the error propagates straight into the performance score, many
times the graded tolerance.

**Do not:** Reduce by the mean, drop replicates, or pool all replicates into
one flat sample.

---

## Step 2 — Recognise that ERZA-RB1 is a house method and pin its constants  *(CRUX, part 1)*

**Do:** Establish the procedure to apply. ERZA-RB1 is a **bespoke house
method**, not a published textbook formula: an Algorithm-A-*style* clamped
robust iteration, but with the house clamp constant

```
c = 1.25          (house clamp)
k_U = 1.25        (combined-uncertainty coverage factor, Step 5)
```

and a closed-form Fisher-consistency correction (Step 3) in place of the
textbook's fixed consistency multiplier.

**Why:** This fork decides the task. The textbook robust-statistics route
(clamp at 1.5 robust standard deviations, fixed 1.134-style consistency
factor) is close enough to look right and wrong enough to miss the graded
tolerance. A run that substitutes the textbook method has not computed
ERZA-RB1, whatever it calls the result.

**Do not:** Assume the clamp, the debias, or the coverage factor from a
published standard. If the specification is not available to the run, the
honest move is to say so — not to present a substitute as the house answer.

---

## Step 3 — The beta(c) Fisher-consistency debias  *(CRUX, part 2)*

**Do:** Compute the bias-correction factor for the clamped scale from the
standard normal CDF `Φ` and PDF `φ` (both expressible through the error
function):

```
E[w²](c) = (2Φ(c) − 1) − 2c·φ(c) + 2c²·(1 − Φ(c))
beta(c)  = 1 / sqrt(E[w²](c))
```

evaluated at the house clamp. As a self-check, `beta(c)` at the house clamp
rounds to **1.2288** to four decimals — the oracle asserts exactly this before
iterating. `beta` multiplies the clamped-sample standard deviation on **every
iteration** of Step 4.

**Why:** Clamping shrinks the sample standard deviation of the clamped values
below the true scale; `beta(c)` restores Fisher consistency in closed form.
Omitting it biases the scale low by tens of times the scale tolerance, and the
error propagates into the combined uncertainty and the performance score.
This — together with the house clamp — is what makes the method ERZA-RB1.

**Do not:** Use the textbook's fixed consistency multiplier, apply the debias
once at the end instead of inside the iteration, or skip it.

---

## Step 4 — The clamped robust location/scale iteration

**Do:** On the per-lab median values `v` (one per lab, `n` labs):

1. Initialise the location `x` at the median of `v`, and the scale `s` at the
   MAD-based robust scale: `1.4826 ×` the median absolute deviation from that
   median.
2. Iterate (the oracle caps at 60 rounds):
   - clamp every value into `[x − c·s, x + c·s]`;
   - `x_new` = plain mean of the clamped values;
   - `s_new` = `beta(c) × sqrt( Σ(v_clamped − x_new)² / (n − 1) )` — the
     **n−1** (Bessel) divisor, debiased every round;
   - stop when both `|x_new − x|` and `|s_new − s|` fall below the oracle's
     tight tolerance (1e-12), else continue.
3. The converged `x` is the robust consensus location `x*`; the converged `s`
   is the robust between-laboratory scale `s*` — the first contracted output.

**Why:** The clamp pulls outlying laboratories to the working band instead of
deleting them; iterating to convergence makes the result independent of the
starting point; the MAD initialisation keeps the first clamp band from being
set by the outliers themselves. The shipped round contains genuine outlier
labs, so the naive mean/SD differs from the robust consensus by an order of
magnitude more than the tolerance — that gap is the point of the method.

**Do not:** Run one clamping pass and stop, recompute the clamp band from the
raw SD, or divide by `n` instead of `n − 1`.

---

## Step 5 — The combined uncertainty

**Do:** Form the round's combined standard uncertainty as

```
u = k_U × s* / sqrt(n)
```

with `n` the number of laboratories and `k_U` the house coverage factor from
Step 2.

**Why:** The zeta-prime denominator is this `u`, not `s*` itself and not a
plain standard error. Using `s*` bare, or omitting the coverage factor,
rescales the performance score by a factor large against the zeta tolerance.

---

## Step 6 — Zeta-prime for the nominated laboratory

**Do:** Compute the second contracted output:

```
zeta' = (x_L* − x*) / u
```

where `x_L*` is the nominated lab's **median-reduced** value from Step 1,
`x*` the converged robust location, and `u` the Step-5 uncertainty.

**Why:** Zeta-prime is the house performance score: the nominated lab's
departure from consensus in units of the round's combined uncertainty. Feeding
it the lab's *mean* (Step 1's warning — this lab's replicates are spiked), the
naive grand mean, or a plain standard deviation each moves the score by many
times the graded tolerance.

**Do not:** Confuse zeta-prime with the classical z-score the decoy block
carries.

---

## Step 7 — Emit the output contract

**Do:** Write `/root/results.json` with exactly the two contracted keys —
`robust_scale` holding `s*` and `zeta_prime` holding `zeta'` — each a single
finite number. The oracle rounds to six decimals; the tolerances are far
coarser, so sensible rounding is harmless.

**Why:** The grader keys on those two names. A correct computation under other
key names, or with the two values swapped, scores zero.

---

## Step 8 — Verify with something that can actually disagree

Checks that **cannot** discriminate:

- "the scale is positive and the zeta is order unity" — every route above,
  including the decoy, satisfies that;
- agreement with the decoy block — evidence *against*, not for: the decoy is
  the classical summary the robust method exists to depart from;
- re-running the same script.

Checks that **do** discriminate:

- **the beta self-check** (Step 3): evaluating the closed form at the house
  clamp and comparing against the four-decimal constant catches a wrong CDF/PDF
  expression or a wrong clamp immediately;
- **convergence inspection**: printing the location/scale trajectory and
  confirming it settled to the stopping tolerance well within the iteration
  cap catches a non-converged or oscillating iteration;
- **sensitivity bounding**: recomputing with the plausible wrong forks (mean
  reduction, no debias, textbook clamp) and quoting how far each moves the two
  outputs — this shows the forks *matter* and that the submitted pair is the
  house one;
- **an independent reimplementation** of the iteration (e.g. a
  vectorised route against the scalar loop) agreeing to near machine
  precision.

**Do not:** claim verification on a check from the first list.

---

## Step 9 — Working conditions

- **No network.** The container declares no-network. The whole computation
  needs only the standard library (`math.erf`, `statistics`); hunting for
  scipy or installing packages is a process failure, not bad luck.
- **Leave `/root/data` strictly alone.** The outcome verifier *recomputes the
  reference from the shipped measurements at grade time*, so mutating the
  inputs invalidates grading itself. Copying them out to scratch is fine.

---

## What a finished run must have produced

Stated as properties, not values:

- two finite numbers under exactly the contracted keys, at the contracted
  path;
- a scale that came from a converged, clamped, debiased iteration over
  median-reduced lab values — not the classical SD, and not the decoy;
- a performance score whose numerator uses the nominated lab's median-reduced
  value and whose denominator is the coverage-factored uncertainty;
- the input directory byte-identical to how it shipped.

The numeric ground truth lives in the bundle's frozen
`verifier/expected_values.json`. It is deliberately not reproduced here — and
the process rubric reads it only to recognise the shipped attractor, never to
pass a run.
