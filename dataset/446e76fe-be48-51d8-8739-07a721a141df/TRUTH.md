# TRUTH.md — local magnitude (ML) from a broadband record (golden trajectory)

The ordered moves a competent run makes, from opening the task to writing the
answer. Each step says **what to do and why**; **no step states what it evaluates
to**. Derived from `oracle/solve.sh` (the reference solution) with every value
stripped out — it names no amplitude, no distance, no magnitude.

**Method constants are kept; step answers are stripped.** The Wood-Anderson
constants and the distance-correction coefficients below are constants *inside a
relation* — they define the regime the task falls into and are published, so a
reader needs them to follow the path at all. Nothing read from this task's inputs,
and nothing a step produces, appears anywhere in this file.

---

## Step 0 — Read the inputs

**Do:** Open `/root/data/question.json` and take the event origin, the station,
the epicentral distance and the event depth. Read the waveform from
`/root/data/waveform.mseed` and the instrument metadata from
`/root/data/station.xml`.

**Why:** Everything the magnitude depends on is in these three files. The task
exists to measure whether the run *measures* a magnitude rather than *recalls*
one.

**Do not:** Substitute a magnitude from any source other than this record. The
event is real and catalogued, so a published magnitude for it may be recallable —
but a catalogue magnitude is generally a different quantity (commonly Mw) arrived
at by a different method, and a number that was not measured from this waveform is
not an answer to this task however close it lands.

## Step 1 — Select the horizontal components

**Do:** Keep only the horizontal components of the record — the channels whose
component code is North/East or the numeric equivalents (`N`, `E`, `1`, `2`) —
and discard the vertical.

**Why:** The Southern-California local-magnitude scale is defined on horizontal
Wood-Anderson amplitudes. Including the vertical, or using it instead, measures a
quantity the scale was never calibrated against.

**Do not:** Merge components into one trace, or take the vertical as a substitute
when a horizontal looks clipped.

**Where more than one route is admissible.** The record may carry the same
horizontal ground motion on more than one band code (a broadband and a
higher-rate channel set from the same sensor). The oracle does not privilege one
band; either set is an admissible route provided the components used are
horizontal.

## Step 2 — Prepare the traces

**Do:** Remove the linear trend and apply a modest taper to each horizontal trace
before any spectral operation.

**Why:** Response removal is a deconvolution in the frequency domain. An offset or
trend puts energy at zero frequency and an abrupt trace edge rings; both leak into
the passband and inflate the peak amplitude that Step 5 measures.

**Do not:** Skip detrending because the trace "looks flat".

## Step 3 — Remove the instrument response  *(to DISPLACEMENT)*

**Do:** Deconvolve the full instrument response supplied in the StationXML,
requesting **displacement** output. Stabilise the deconvolution with a
band-limiting pre-filter and a water level — the pre-filter as a four-corner
cosine taper whose flat passband covers the band in which the event actually has
signal, with its corners set inside the recording band at both ends, and the
water level in the conventional decibel-down sense.

**Why:** The Wood-Anderson instrument is a *displacement* seismograph, so the
signal fed to Step 4 must be displacement in metres. Asking for velocity or
acceleration produces a trace of the wrong physical dimension, and the magnitude
that follows is wrong by an amount no later step can detect. Without a water level
the deconvolution divides by near-zero response at the band edges and amplifies
noise without limit.

**Do not:** Divide by a single scalar sensitivity instead of deconvolving the full
response. Do not leave the output in counts.

**What this step does and does not pin.** The *output units* are pinned — the
chain below is written for displacement. The exact corner frequencies are not:
the oracle picks one four-corner band, and any band that keeps the event's signal
and excludes the deconvolution's unstable edges reaches the same magnitude to
well inside the graded tolerance. Do not read a different but sane pre-filter, or
a run that let the deconvolution default its stabilisation, as a failed step.

## Step 4 — Simulate the Wood-Anderson seismograph  *(CRUX)*

**Do:** Convolve the displacement traces with the response of a standard
Wood-Anderson torsion seismograph, specified by the **IASPEI standard** constants:
static magnification 2080, free period 0.8 s. Expressed as poles-and-zeros this is
**two zeros at the origin** and a conjugate pole pair whose real and imaginary parts
follow from the free period and the damping.

**Why:** This is the step the task exists to measure. Everything before it is
bookkeeping. ML is *defined* as the amplitude a Wood-Anderson instrument would
have written. Skipping the simulation and measuring the response-removed
displacement directly omits the instrument's static magnification and its
resonance entirely, and the number that results is not a Wood-Anderson amplitude
at all.

**Why two zeros — this is the crux.** The instrument's response to ground
*displacement* is `H(s) = G·s²/(s² + 2hω₀s + ω₀²)`: the numerator is `s²`, so there
are two zeros at the origin. Step 3 has already converted the trace to displacement,
so both factors of `s` must be supplied here. The **one-zero** form is the response to
*velocity* — velocity has already absorbed one factor of `s` — and it is what most
circulated code for this pipeline contains. Applying it to a displacement trace leaves
the amplitude short by `|2πf|` at the dominant frequency: a factor of ~6.26 near 1 Hz,
which is 0.80 in magnitude, well beyond the graded tolerance.

**The step carries its own proof.** A Wood-Anderson is *defined* by its static
magnification, so the paz can be checked without any seismological judgement: drive it
with a 1 mm ground-displacement sinusoid well above the 1.25 Hz corner and the
deflection must be ~2080 mm. Two zeros give ~2034; one zero gives ~65. A trajectory
that ran this check, in any spelling, has done the single most load-bearing piece of
verification available on this task.

**Do not:** Treat the simulation as an optional refinement, and do not accept a
single origin zero on a displacement input.

**A caution against over-reading this step.** Substituting the older magnification
2800 for the IASPEI 2080 is a *method* error worth naming, but on this instance it
moves the magnitude by well under the graded tolerance. Do not treat a run that
used it as having failed the measurement; it took a defensible historical
convention and still lands inside the tolerance. The same holds for the damping
convention: h = 0.8 (which the IASPEI pole pair encodes) and the widely quoted
h = 0.7 differ by 0.037 here, far inside tolerance. Neither is the crux; the zero
count is.

## Step 5 — Measure the peak amplitude, in millimetres

**Do:** On each simulated horizontal trace take the maximum absolute deflection —
a **zero-to-peak** amplitude, not peak-to-peak — convert from metres to
millimetres, and take the **larger of the two horizontals** as the amplitude that
enters the magnitude relation.

**Why:** The Southern-California scale is calibrated on the maximum horizontal
zero-to-peak Wood-Anderson amplitude in millimetres. Halving a peak-to-peak
reading, or leaving the amplitude in metres, each shift the magnitude by a fixed
offset that looks entirely plausible; the metres-for-millimetres slip in
particular moves it by a full order of magnitude in amplitude and is invisible
downstream.

**Do not:** Use peak-to-peak without halving it. Do not skip the unit conversion.

**A caution against over-reading this step.** Taking the larger of the two
horizontals is the oracle's route. Averaging the two horizontal amplitudes, or
averaging the two per-component magnitudes, is a recognised station convention
and on this instance it moves the magnitude by a small fraction of the graded
tolerance. A run that averaged has not failed the measurement and must not be
marked as though it had.

## Step 6 — Form the distance correction

**Do:** Compute the **hypocentral** distance from the epicentral distance and the
event depth by combining them in quadrature, then evaluate the Hutton & Boore
(1987) Southern-California `−log A₀` distance correction, whose form is

    1.110 · log₁₀(r / 100) + 0.00189 · (r − 100) + 3.0

with `r` the hypocentral distance in kilometres.

**Why:** The correction is a *regional* calibration — this is the Southern
California scale, and the coefficients above are what make it that scale rather
than a generic attenuation curve. At the distances this task works at, the two
distance-dependent terms are both large enough to matter: dropping them and
keeping only the 100-km reference constant moves the magnitude by several times
the graded tolerance.

**Do not:** Substitute a generic `log(r)`-only attenuation, or the bare 100-km
reference constant. Do not rescale the coefficients for another region.

**A caution against over-reading this step.** Combining epicentral distance with
depth in quadrature is the oracle's route and the physically correct one, but on
*this* instance the event is shallow relative to its epicentral distance, so
using the epicentral distance directly moves the magnitude by a small fraction of
the graded tolerance. A run that used epicentral distance has taken a route that
still lands well inside tolerance — it has not failed the measurement, and must
not be marked as though it had.

## Step 7 — Combine into the magnitude

**Do:** Add the base-10 logarithm of the peak amplitude in millimetres to the
distance correction of Step 6.

**Why:** That sum *is* the local magnitude under this scale. The two terms carry
their units implicitly — amplitude in millimetres, distance in kilometres — so a
unit slip in either term propagates straight into the magnitude with no symptom.

**Do not:** Introduce a station correction, or add the catalogue magnitude in any
form.

## Step 8 — Verify before reporting

**Do:** Sanity-check the result independently of the pipeline that produced it.
Confirm the magnitude is in a physically sensible range for the recorded distance
and that it is **not** simply the catalogue value. Confirm the amplitude that
entered Step 7 came from a horizontal, in millimetres, after Wood-Anderson
simulation. Re-measure the peak on the second horizontal, or repeat the whole
chain on the other band code, and check the two agree to within the spread
expected between components.

**Why:** Every failure mode above returns a well-formed number of the right order
of magnitude. Nothing about the output looks wrong, so only an independent check
distinguishes a measured magnitude from a confidently wrong one — or from the
catalogue value copied through.

**Which checks discriminate, and which do not:**

| Check | Can it disagree with a wrong chain? |
|---|---|
| Re-running the same script and getting the same number | **No.** It re-executes the same convention. |
| "The magnitude is between 3 and 6, so it is plausible" | **No.** Every failure mode in Steps 3–6 except the unit slip lands in that band. |
| "It is close to the published magnitude for this event" | **No — worse than useless.** A catalogue magnitude is generally a different quantity reached by a different method. On some events the two happen to agree closely, so agreement is not evidence of a correct measurement; it is not evidence of anything. |
| Driving the simulated instrument with a known 1 mm displacement and checking it deflects the static magnification | **Yes, decisively.** This is the instrument's definition, it needs no seismology, and it is the one check that separates the correct response from the velocity-form response that most circulated code carries. |
| Second horizontal component, same chain | **Partly.** Catches a corrupt trace; blind to every convention error, which hits both components identically. |
| Same chain on the other band code of the same sensor | **Partly.** Same blindness, but it does catch a band-specific pre-filter mistake. |
| Recomputing with the other distance convention and seeing how far the answer moves | **Yes, for that one branch** — it bounds the size of that choice instead of assuming it. |
| Checking the simulated peak amplitude is of the size a Wood-Anderson drum would actually have written for a shock of this size at this distance | **Yes.** This is the check that catches a dropped magnification or a unit slip, because both move the amplitude by orders of magnitude. |

**Do not:** Treat "the script ran" as verification, or accept a result that
coincides with the catalogue magnitude without asking why.

## Step 9 — Emit the output contract

**Do:** Write the results file named in the task with exactly the single key the
contract specifies, holding one number.

**Why:** The grader keys on that name and reads a scalar. A run whose whole chain
is right but whose file or key is not the contracted one scores zero.

**Do not:** Add extra keys, nest the value, or emit a string.

## Step 10 — Working conditions

**Do:** Work from the shipped inputs, in place, with the libraries the image
already provides.

**Why:** The container declares no network, so a fetch or a package install cannot
succeed; it only costs the run time. The inputs are the record the reported
magnitude claims to be a measurement *of* — mutating them severs the reported
number from the thing it describes.

**Do not:** Attempt a download or an install. Do not write into, delete from, or
edit in place anything under the input directory. Copying the inputs *out* to a
scratch location is fine and changes nothing.

---

## Closing properties (hold for a correct run, and state no values)

- The reported magnitude is a *measurement* from this station's record, not the
  catalogue value carried in the input.
- The amplitude entering the magnitude relation is a horizontal, zero-to-peak,
  Wood-Anderson displacement expressed in millimetres.
- The distance correction is the Southern-California regional relation, evaluated
  at a distance derived from the fields the input supplies.
- The response was deconvolved to displacement, not velocity or acceleration.
- The results file exists at the contracted path, with the contracted key, holding
  a single finite number.
- The input directory is byte-identical to how it shipped.
- Re-running the same pipeline on the same inputs reproduces the same magnitude.
