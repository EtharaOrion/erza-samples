# TRUTH — golden trajectory for task `geomagnetic-declination-survey`

**What this is.** The moves a competent run makes, in order, from opening the task to
writing the twelve true azimuths. Each step says *what to do and why* and states the
relations it needs symbolically. **No step states what it evaluates to** — no
declination, no azimuth, no field value. A reader still has to open the inputs, read the
coefficients, and do every calculation.

**Method constants vs step answers.** The relations and the constants *inside* them — the
WGS84 ellipsoid parameters, the reference radius, the Schmidt recurrence, the field-element
definitions — are *method* and are stated here. What is withheld is everything the run must
*produce*: the per-station declination and the true azimuths. The withheld lever — the
IGRF-13 Gauss coefficients — is named here only as "the coefficient set the skill supplies",
never numerically; a run gets the coefficients from the skill, not from this file.

**Self-contained by requirement.** Following this file, the task's output contract, the
shipped inputs, and the coefficient set the skill supplies must land on the oracle's answer
exactly. Verified by `verification/rederivation_test.py` (BIT-IDENTICAL).

**Grader-side only.** Never mounted, never shipped to the agent.

---

## Step 0 — Read the task and inventory the inputs

**Do:** Establish what is asked (one true geographic azimuth per station, in [0, 360)) and
the exact result keys and output path. Then open `stations.csv` (per-station geodetic
latitude, longitude, elevation, and measured magnetic azimuth) and read the survey epoch
from `question.json` before planning.

**Why:** A correct calculation written under the wrong keys or left un-wrapped scores zero.
The `decoy_reference` block in `question.json` is a single stale chart figure supplied for
orientation only — it is **not** the per-station declination and using it is the intended
failure.

## Step 1 — Recognise that declination must be *computed*, not looked up

**Do:** Note that reducing a magnetic azimuth to true needs the magnetic declination at
each station, and that declination at survey precision is a modelled quantity: it comes from
a spherical-harmonic synthesis of a large published coefficient set, not from recall, not
from the old chart, and not from a single regional value.

**Why:** The one-number chart value and any recalled ballpark are wrong at every station by
degrees. This recognition is what separates a correct run from the decoy.

**Do not:** apply the chart declination to the stations, or leave the bearings unreduced.

## Step 2 — Load the coefficients and select the epoch

**Do:** Parse the Gauss coefficients the skill supplies into `g[n,m]`, `h[n,m]`. Select the
survey epoch: on a 5-year node, read that column directly; between nodes, linearly
interpolate; beyond the final node, linearly extrapolate with the secular-variation column.

**Why:** The coefficients ARE the withheld content; without them there is no number to
compute. The epoch rule is the model's own definition of time dependence.

## Step 3 — Convert geodetic coordinates to geocentric. **Crux, part 1.**

**Do:** The station coordinates are geodetic (WGS84 latitude and height above the ellipsoid).
The synthesis is defined in geocentric spherical coordinates. Convert (latitude, height) to
(geocentric colatitude θ, radius r) using the WGS84 ellipsoid parameters.

**Why:** Treating the geodetic latitude as geocentric — using `θ = 90 − lat` and
`r = R_E + h` — is the single most common error. Geodetic and geocentric latitude differ by
up to ~0.2°, which feeds straight into the declination and moves every station past a survey
tolerance while the field magnitude still looks right.

**Do not:** use the reference radius `R_E` as the station radius; it appears only as the
ratio base in the synthesis.

## Step 4 — Build Schmidt semi-normalised Legendre functions. **Crux, part 2.**

**Do:** Compute `P_n^m(cos θ)` and `dP_n^m/dθ`, Schmidt semi-normalised, for all degrees to
the model's maximum. The robust route is the Gauss-normalised recurrence followed by an
explicit Schmidt normalisation factor.

**Why:** A wrong or folded-in normalisation typically leaves the low-degree terms about right
and corrupts the rest, so the declination comes out several to ~10° off — large, uniform, and
not obviously a bug.

## Step 5 — Synthesise the field and rotate it into the geodetic frame

**Do:** Sum the spherical-harmonic series for the geocentric components `B_r`, `B_θ`, `B_φ`
using the coefficients, `P`, `dP`, and the ratio `R_E/r`. Then rotate the `(B_θ, B_r)` pair
into the geodetic north/up frame (`B_φ` is already geographic east), giving north `X`, east
`Y`, down `Z`.

**Why:** Declination is `atan2(east, north)`, and the geodetic rotation changes the north
component, so Step 3 is not optional even though "only" the declination is needed.

## Step 6 — Declination, then reduce the azimuth

**Do:** Form `D = atan2(Y, X)` (east positive). For each station,
`true_azimuth = (magnetic_azimuth + D) mod 360`.

**Why:** The sign convention (declination east positive, true = magnetic + declination) and
the wrap are stated in the task; a `magnetic − D`, a west-positive declination, or an
un-wrapped result each fail.

**Mark the crux.** Steps 3 and 4 together are the fork among runs that *have* the
coefficients: skip the geodetic conversion or mis-normalise the Legendre functions and the
whole network shifts. Steps 1–2 are the fork against runs that *lack* the coefficients: they
fall back to the chart or leave the bearings unreduced.

## Step 7 — Emit

**Do:** Write one `true_azimuth_deg` per station as a plain JSON number under the exact keys
and path, at full double precision, ids spelled exactly as the input spells them.

## Step 8 — Verify with something that can actually disagree

**Do:** Recompute one station's field by an independent route — for instance numerically
differentiating the scalar potential instead of using the analytic derivatives — and require
agreement to a small fraction of the tolerance. Check the sign and rough magnitude of the
declination against the region.

**Do not** treat "the field magnitude is plausible" or "the reference point looks right" as
verification: a skipped geodetic conversion or a wrong normalisation passes both.

## Close — properties a correct answer has

- One true azimuth per station, all present, ids exact, each wrapped into [0, 360).
- Every declination differs materially from the single old-chart figure and from zero.
- The declinations vary station to station (they are not one constant), consistent with the
  network spanning a range of latitude and longitude.
- The delivered input files are unmodified.
