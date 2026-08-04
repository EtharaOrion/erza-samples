# TRUTH.md — tidal harmonic prediction at three anonymised gauges (golden trajectory)

The moves a competent run makes, in order, from opening the task to writing the twelve
predicted heights. Each step says **what to do and why**. **No step says what it
evaluates to** — no height, no datum offset, no constituent amplitude or phase lag, no
value read from the shipped inputs.

**Derived from the oracle and from nothing else.** Every transformation below is
`oracle/tide_predict.py` and `oracle/solve.py` transcribed as instructions, in the
oracle's order, with the oracle's conventions pinned in words. It is **not** derived
from the skill the with-skill arm mounts.

**Grader-side only.** Never mounted, never shipped to the agent.

## What "no numbers" means here, precisely

Two kinds of number look alike, and this file keeps one and strips the other.

| Kept — **method** | Stripped — **step answers** |
|---|---|
| The relations, written symbolically | Any value read from `stations.csv` or `question.json` |
| The coefficients *inside* those relations — the Schureman mean-longitude polynomials, the node-longitude polynomial, the nodal factor/angle table | Every per-gauge harmonic constant (amplitude, Greenwich phase lag, datum offset) |
| The time origin and the wrap moduli that define the Schureman family | The single recent water level the input carries for orientation |
| Structural counts (six mean longitudes, six Doodson numbers) | The twelve predicted heights, in whole or in part |

Every numeric literal below is a published Schureman/Meeus method constant. None is
read from this task's inputs; none is a quantity a step is supposed to produce.

**Self-contained modulo the withheld lever.** Following this file, the shipped inputs,
the output contract, and **the two constant tables the run must obtain** (the per-gauge
harmonic constants and the constituent definitions) lands on the oracle's answer
bit-identically. That is not asserted, it is executed:
`verification/rederivation_test.py` reimplements every step below from this text alone
and reproduces all twelve reference heights to 1e-6 m.

---

## Step 0 — Read the task and inventory the shipped inputs

**Do:** Open both files under the input directory. `stations.csv` has a header and
exactly two columns — the gauge label and the name of the vertical datum the heights are
referenced to; it carries **no coordinates and no constants**. `question.json` carries
the list of target instants as UTC timestamp strings, the output path, the output
contract, and a `decoy_reference` block.

**Why:** the gauge labels, the target instants and the exact timestamp spelling are data,
not prose — the task statement names none of them. The answer keys must be spelled
exactly as the input spells them, so they have to be read rather than reconstructed.

**Do not:** assume the gauges are identifiable. The labels are opaque by construction;
their real-world identities are grader-side and are not recoverable from anything in the
container.

## Step 1 — Name the whole chain, then author and run your own solver

**Do:** State the chain end to end before writing code: gauge constants → astronomical
mean longitudes at the instant → per-constituent equilibrium argument → nodal factor and
angle → weighted cosine sum → datum offset → emit. Then write the solver as a file, a
heredoc, or an inline program, and execute it.

**Why:** the working conditions force this. The container has Python 3 with numpy and
**no tide library, no harmonic-constant database and no network**. Nothing in the image
computes a tide height, so a submission exists only if the run authored and ran its own
code. Everything here is closed form: there is no fitting and no iteration, so a solver
loop means the problem has been mis-modelled.

## Step 2 — Recognise the height must come from the gauge's own harmonic constants, and obtain them  *(CRUX)*

**Everything before this is orientation. This step is the task.**

**Do:** Establish that a tide height at prediction precision is a superposition of that
gauge's tidal constituents, each carrying an **amplitude** and a **Greenwich phase lag**
measured at that gauge, plus a datum offset. Obtain that per-gauge constant table, and
the constituent-definition table that gives each constituent its Doodson numbers, its
`semi` phase constant and its node-factor group label.

**Why:** the constants are empirical, gauge-specific, and set by local bathymetry and
resonance. The same constituent is centimetres at one gauge and metres at another, there
is no closed form for them, and no offline library ships them. Without them the harmonic
sum cannot be evaluated **at all** — not badly, but not at all. This is the fork the
task exists to measure, and it is the fork that separates the recorded arms.

**Do not** substitute any of the following. Each is a measured control, and the figures
are re-derived and asserted in `verification/rederivation_test.py`:

| Substitute | Distance from the reference |
|---|---|
| the single recent observed water level, reported at every instant | mean 8.43× the graded tolerance; 11 of 12 cases outside |
| the gauge's long-term mean water level, reported at every instant | mean 7.31× tolerance; 12 of 12 cases outside |
| any recalled or estimated constant | the tide swings across its full range between the listed instants; no constant can sit inside tolerance at all four |

The recent water level is a *single earlier instant*, not a level. Reading it, printing
it and reasoning about it is what this step asks for. Adopting it as the answer is the
intended failure.

## Step 3 — Astronomical mean longitudes at the requested instant

**Do:** Convert the UTC timestamp to days `d` since the Schureman epoch — **1899-12-31
12:00 UT**, not J2000 and not the Unix epoch — and put `D = d/10000`. Evaluate the five
mean-longitude polynomials in degrees, reduce each modulo 360, and divide by 360 so
every one is expressed in **cycles**:

```
s   = 270.434164  + 13.1763965268*d - 8.50e-5*D^2  + 3.9e-8*D^3      moon mean longitude
h   = 279.696678  +  0.9856473354*d + 2.267e-5*D^2                   sun mean longitude
p   = 334.329556  +  0.1114040803*d - 7.739e-4*D^2 - 2.6e-7*D^3      lunar perigee
N'  = -259.183275 +  0.0529539222*d - 1.557e-4*D^2 - 5.0e-8*D^3      negative lunar node term
pp  = 281.220844  +  4.70684e-5*d   + 3.39e-5*D^2  + 7.0e-8*D^3      solar perigee
```

Then form mean lunar time, also in cycles, from the UT fraction of the day:

```
tau = frac( UT_day_fraction + h/360 - s/360 )
```

and assemble the six-vector in this order: `[tau, s, h, p, N', pp]`, all in cycles.

**Why:** the time origin and the units are both load-bearing and both silent. Evaluating
the same polynomials from J2000 instead of the Schureman epoch is **19.67× the graded
tolerance** and puts all twelve cases outside it; from the Unix epoch, 25.36×. Leaving
the longitudes in degrees rather than cycles mis-scales every argument. Neither error
announces itself: the heights that come out are still smooth, still oscillatory, and
still of the right order.

**Do not** use local time, and do not apply a timezone shift — the timestamps are UTC
and the phase lags are referenced to Greenwich.

## Step 4 — Per-constituent equilibrium argument

**Do:** For each constituent in the gauge's table, look its definition up **by name** and
take the dot product of its six Doodson numbers with the six mean longitudes of Step 3,
then add its `semi` phase constant. The result `V` is in **cycles**.

```
V_i = doodson_i · [tau, s, h, p, N', pp]  +  semi_i
```

Constituents present in the gauge table but absent from the definition table contribute
nothing and are skipped; this is the oracle's behaviour and it is deliberate.

**Why:** `V` is the entire time dependence of the prediction. A run that never forms it
emits something that does not vary with the instant at all — **24.22× tolerance**,
11 of 12 cases outside. Dropping only the `semi` constant, keeping the dot product, is
still **5.64× tolerance**: `semi` is not decoration.

**Do not** convert `V` to degrees and then feed it to a cosine expecting radians, and do
not reorder the six-vector — the Doodson numbers are positional.

## Step 5 — Nodal factor and angle

**Do:** Compute the ascending-node longitude `N` in degrees at the instant from the
Meeus polynomial in Julian centuries `T` since J2000.0:

```
N = 125.04452 - 1934.136261*T + 0.0020708*T^2      (mod 360)
```

Then take the Schureman node factor `f` (dimensionless) and node angle `u` (degrees) for
the constituent's **node-factor group**, not for the constituent itself:

```
f_M2  = 1.0004 - 0.0373*cosN + 0.0002*cos2N                       u_M2  = -2.14*sinN
f_K1  = 1.0060 + 0.1150*cosN - 0.0088*cos2N + 0.0006*cos3N        u_K1  = -8.86*sinN + 0.68*sin2N - 0.07*sin3N
f_O1  = 1.0089 + 0.1871*cosN - 0.0147*cos2N + 0.0014*cos3N        u_O1  = 10.80*sinN - 1.34*sin2N + 0.19*sin3N
f_K2  = 1.0241 + 0.2863*cosN + 0.0083*cos2N - 0.0015*cos3N        u_K2  = -17.74*sinN + 0.68*sin2N - 0.04*sin3N
f_J1  = 1.1029 + 0.1676*cosN - 0.0170*cos2N + 0.0016*cos3N        u_J1  = -12.94*sinN + 1.34*sin2N - 0.19*sin3N
f_OO1 = 1.1027 + 0.6504*cosN + 0.0317*cos2N - 0.0014*cos3N        u_OO1 = -36.68*sinN + 4.02*sin2N - 0.57*sin3N
f_MF  = 1.0429 + 0.4135*cosN - 0.0040*cos2N                       u_MF  = -23.74*sinN + 2.68*sin2N - 0.38*sin3N
f_MM  = 1.0000 - 0.1300*cosN + 0.0013*cos2N                       u_MM  = 0
f_SOL = 1                                                          u_SOL = 0
```

and build the compound groups from those:

```
M2^2 -> (f_M2^2, 2*u_M2)      M2^3 -> (f_M2^3, 3*u_M2)      M2^4 -> (f_M2^4, 4*u_M2)
MS4  -> (f_M2,   u_M2)        M3   -> (f_M2^1.5, 1.5*u_M2)
MK3  -> (f_M2*f_K1, u_M2 + u_K1)          2MK3 -> (f_M2^2*f_K1, 2*u_M2 - u_K1)
```

Any group label not in that table takes `f = 1, u = 0`.

**Why:** these are the 18.6-year modulation of amplitude and phase from the regression of
the moon's node.

**Say honestly what this step is worth on this instance.** Setting `f = 1, u = 0`
everywhere is measured at **0.93× the graded tolerance — the largest single case error
is inside tolerance, and no case fails.** The nodal terms are correct method and this
file pins them, but on *these* twelve instants they are a refinement, not a fork. A
rubric that treats omitting them as an outcome-breaking failure is over-reading the
measurement.

**Do not** apply a constituent's own name as its group label — the mapping is
many-to-one and it is carried in the definition table.

## Step 6 — Sum the constituents onto the datum offset

**Do:** Start the height at the gauge's datum offset — mean sea level above the chart
datum, the `msl_minus_mllw_m` field of the constant table — and add one term per
constituent:

```
height = Z0 + Σ_i  f_i * H_i * cos( 2π*V_i + radians(u_i) - radians(g_i) )
```

`V` enters in cycles and is multiplied by 2π; `u` and the Greenwich phase lag `g` are in
degrees and are converted to radians. The phase lag is **subtracted**.

Use **every** constituent the gauge table lists.

**Why:** two things break here quietly.

- **Dropping `Z0`** shifts every height by the whole datum offset: **17.28× tolerance**,
  12 of 12 cases outside. The answer is still a well-formed oscillation about zero.
- **Truncating the constituent set** is a graded failure, and the grading is measured.
  Keeping the five classical majors is **3.20× tolerance** with 9 of 12 cases outside;
  the measured curve crosses the tolerance between **9 constituents (1.26×, one case
  outside)** and **10 constituents (0.92×, no case outside)**. Below ten, the truncation
  is a real error; at ten and above it is not.

**Do not** add the phase lag instead of subtracting it, and do not mix degrees into the
cosine without converting.

## Step 7 — Emit under the output contract

**Do:** Write the contracted results file at the contracted path, carrying a
`predictions` object with one entry per gauge label from `stations.csv`, each mapping
every target timestamp — **spelled exactly as `target_times_utc` spells it** — to the
predicted height in metres above that gauge's chart datum, as a number.

**Why:** the outcome verifier looks the gauge label up in `predictions` and then the
timestamp inside it, and fails the case before it ever compares a number if either key
is missing or differently spelled. A perfect computation under the wrong keys scores
zero.

## Step 8 — Verify with something that can actually disagree

**Do:** Use the check the input hands you. The `decoy_reference` block reports an
observed water level at a stated earlier instant. Run the *same harmonic method* at
*that* timestamp and compare the two: they are the same physical quantity at the same
place and time, and the comparison is independent of everything you computed for the
target instants. Agreement to within the local surge/meteorological residual corroborates
the constants, the time origin, the phase convention and the datum together.

**Which checks discriminate, and which do not:**

| Check | Discriminates? |
|---|---|
| Reproduce the recent observation at its own timestamp from the harmonic sum | **Yes** — it is an independent measurement, and it fails loudly under a wrong time origin, a sign-flipped phase, or a missing datum offset |
| Re-run the same script and get the same number | No — it re-executes the same defect |
| "The values look plausible" / "they are in a reasonable range" | No — every measured failure mode above returns smooth, in-range, physically plausible metres |
| Heights vary between instants | Weak — it separates a constant from a computation, and nothing finer |
| Sum sits within the gauge's tidal range about the datum offset | Weak — a wrong time origin satisfies it at every instant |

**Do not** report confidence as if it were evidence. A wrong convention here produces a
number that passes every cheap check.

## Step 9 — Working conditions, and what not to touch

**Do:** Leave the delivered input files exactly as delivered. Copying them out to a
scratch directory is fine; writing into the input directory is not.

**Why:** the outcome verifier grades against a frozen reference table and does not
recompute truth from the shipped inputs, so a mutated input does not corrupt the grade —
it destroys provenance: the reported heights would no longer describe the instants the
run claims to have predicted.

**Do not** reach for the network or install a package. The task declares no network
access; the attempt cannot succeed, cannot change the answer, and signals that the
working conditions were not read.

## The withheld lever (context, not a step)

The lever is the **per-gauge harmonic-constant table** — amplitudes and Greenwich phase
lags per constituent, plus the datum offset. It is empirical and gauge-specific, with no
closed form, and the gauges are identified only by opaque labels, so it cannot be looked
up from any public source or regenerated from a model's weights at this precision. The
shipped input carries a competing recent water level that the default route grabs. With
the table plus the method above, the twelve heights are deterministic.

## Closing properties (hold for a correct run, and state no values)

- One height per (gauge, instant), all twelve present; gauge labels and timestamps
  spelled exactly as the inputs spell them; every value a finite number.
- The heights **vary across the four instants** at each gauge, and differ from both the
  recent observed level and the gauge's mean water level.
- Each height sits within the gauge's tidal range about its datum offset.
- The delivered input files are byte-identical to what was delivered.
- The numeric ground truth lives in `verifier/expected_values.json`. It is not
  reproduced here, and no run should have seen it.
