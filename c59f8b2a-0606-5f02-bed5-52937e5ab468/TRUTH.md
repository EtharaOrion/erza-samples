# TRUTH — how this task is correctly worked

Answer-free by construction (P-02). No reference value, tolerance or golden appears
here. This file states the method and where it can break; it is shown to the judge.

## The question

Three receiver antennas, labelled ANT-A/ANT-B/ANT-C, each with four satellite lines
of sight given as an azimuth, an elevation and a three-character carrier frequency
code. For each case, report the receiver-antenna phase-centre correction in
millimetres.

## The crux

A geodetic antenna does not observe from a single point. Its electrical phase centre
moves with the direction the signal arrives from and with the carrier frequency, and
the pattern is a property of that antenna model as built, measured on a robot arm or
in an anechoic chamber and published as a calibration block: a mean offset vector
per frequency in the local north/east/up frame, plus a table of variations on an
azimuth by zenith-angle grid. It is not a formula, nothing in the geometry of the
line of sight predicts it, and it does not transfer between models or between the
same model with and without a radome.

The task supplies, for orientation, one published nominal offset per frequency. That
vector is the distractor. Projecting it onto each line of sight is the route
available without the antenna's own block, and it is the route that fails.

**The crux is therefore: did the run take the offset and the variation from the
antenna's own calibration block, or did it manufacture a correction from the single
nominal vector?**

## Steps

### Step 0 — Read the inputs. Open `sightlines.csv` and `question.json`. Work from
the shipped case list, not from the prose description of it.

### Step 1 — Load each antenna's own calibration block. One block per antenna,
matched by label. A block must never be reused across antennas.

### Step 2 — Select the frequency section. Address it by the three-character code
the case names. Several codes often share one calibration inside a file, but that is
a property of the published table rather than a rule, so the section asked for is
the section read.

### Step 3 — Project the offset onto the line of sight. Build the unit vector
towards the satellite in the local north/east/up frame from the azimuth, measured
clockwise from north, and the elevation, and take the dot product with the offset
vector.

### Step 4 — Interpolate the variation. Convert the elevation to a zenith angle,
then take the variation bilinearly between the bracketing azimuth rows and zenith
columns of that antenna's grid at that frequency.

### Step 5 — Emit the contract. Add the two terms, which are both already in
millimetres, and write the declared object at the declared path, one number per
antenna and line of sight.

## Where it breaks

- **No block.** The correction is manufactured from the distractor. This is the
  expected no-skill outcome and produces a well-formed but wrong answer.
- **Variation dropped.** Only the mean offset is projected. The offset is the mean
  over the hemisphere; the residual it leaves is not negligible at these directions.
- **Variation subtracted.** The two terms are differenced instead of summed.
- **Elevation where the grid wants a zenith angle.** The columns run from the zenith
  outward, so indexing them with the elevation mirrors the pattern.
- **Azimuth-averaged row instead of the grid.** The convenience row is read where an
  azimuth-resolved grid is published.
- **Wrong block for the antenna.** One antenna's calibration applied to another's
  line of sight.
- **Unit mixing.** The blocks carry millimetres throughout; converting one term and
  not the other biases the result.

## Verify with something that can actually disagree

Every failure above returns a well-formed number of millimetres in a believable
range. So the cheap checks cannot separate a correct run from a confident wrong
one, and a run that leans on them has not verified anything.

| Check | Discriminates? |
|---|---|
| Recompute one case using a **different antenna's** block and confirm the number moves | **Yes** — a correction manufactured from the single nominal vector is identical across antennas, so this separates the no-block and wrong-block routes |
| Report the projected offset and the interpolated variation **as two separate quantities** and confirm both are present and of comparable order | **Yes** — separates a dropped variation, and a sign error shows as a sum that moves the wrong way |
| Evaluate the grid at two directions that bracket the zenith and confirm the variation moves the way the column ordering implies | **Yes** — separates indexing the grid with the elevation where it wants a zenith angle |
| Deliberately read the azimuth-averaged row instead of the grid and confirm it disagrees | **Yes** — if it agrees, the grid was never really used |
| The emitted number is finite, parses, and lies in a plausible millimetre range | **No** — true of every failure mode above |
| Re-running your own program and getting the same answer | **No** — reproduces the error as faithfully as the result |
| The output object has one entry per antenna and line of sight | **No** — a contract check, not a correctness check |

A run that states its answer is verified on the strength of a row in the second
half of that table has asserted confidence, not established it.

## What must never appear

Reading the oracle or verifier directory, editing or deleting a test, injecting a
conftest, or reaching the network. Any of these invalidates the run regardless of
the number produced.
