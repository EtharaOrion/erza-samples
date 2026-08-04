# TRUTH — golden trajectory for task `903d6f33-74c0-554d-b210-9c2b3a5138fb`

**What this is.** The thinking process a model should follow, in order, to solve this
task efficiently and correctly. Each step says *what to do and why*, and gives the
relations it needs symbolically.

**No step states what it evaluates to.** There are no coordinates, no header values, and
no derived results anywhere in this file. A reader still has to read the inputs and do
every calculation.

**Method constants vs step answers.** Relations and the constants inside them — a
degree/radian factor, a projection family's fiducial native coordinates, the modulus of
the final wrap — are *method*, and they are stated here, because without them this
document is not followable. What is withheld is everything the run is supposed to
*produce or derive*: the header's values, the pole longitude this task's condition
resolves to, and the sixteen answers.

**Self-contained by requirement.** Following this file, plus the task statement's output
contract and the shipped input files, must land on the oracle's answer exactly — with no
other document consulted. Verified: an implementation written from these steps alone
reproduces the frozen expected values to 0.0e+00 degrees.

**What it is for.** It is the spec the process rubric is derived from, and the context
the LLM judge reads when grading how a run reasoned. It is a grader artifact and is
never shown to the agent under evaluation.

**How it differs from `SKILL.md`.** The Skill is the generalised, transferable guide for
the whole class of problem — any TAN WCS, any header — and is what we *give* the agent.
This is the trajectory for *this* task: the specific sequence of moves, in the order a
competent run makes them, with the traps flagged at the point they bite.

**How it was built.** From `task.md` (what is asked), `oracle/wcs_pipeline.py` (the
reference chain, and its `ALL_BUGS` tuple which names the four failure modes the task
was built to discriminate), `environment/data/image.hdr` (which cards are and are not
present), and the 32 recorded trajectories (which steps runs actually skip).

---

## Step 0 — Read the task and inventory what you were given

**Do:** Establish what is being asked for (a sky position per catalogued source), in what
frame, in what units, and in what output shape. Then look at what is actually on disk
before planning anything.

**Why:** The output contract — key names, id spelling, wrapper structure — is part of the
task, and a correct calculation serialised into the wrong shape scores zero.

---

## Step 1 — Read the header rather than assuming its contents

**Do:** Open the header file and read the cards. Parse it properly if you are going to
parse it: split each card on the *first* `=` only; if the remaining value opens with a
quote, take the quoted string **before** stripping the trailing comment. Note that some
keys contain hyphens, and that a blank line and the `END` card are not cards.

**Why:** Comment-stripping before quote-handling truncates any string value containing a
slash. Guessing which keywords are present is the beginning of every failure on this task.

**Note:** Transcribing the constants into your source rather than parsing the file is
acceptable here — the values are frozen — but you must have *looked* at them first.

---

## Step 2 — Determine the projection from the header, then use what that buys you

**Do:** Read the axis-type cards to learn which world axis is longitude, which is
latitude, and which projection code is in force. Establish from the projection code
which family the projection belongs to.

**Why:** The family determines the fiducial point's native coordinates, and therefore how
much of the general pole-rotation machinery you can discard. Assuming axis order rather
than reading it is one of the four failure modes this task discriminates.

---

## Step 3 — Name the whole chain before writing any code

**Do:** Write down the four transformations you are about to compose, in the order the
standard defines them: pixel coordinates → intermediate world coordinates → native
spherical coordinates → celestial coordinates. Decide which is likely to be the hard one
and budget accordingly.

**Why:** Runs that treat this as one undifferentiated conversion collapse the third
transformation into "reference value plus offset" and produce answers that look plausible
and are uniformly wrong. Naming the stages first is what prevents that.

**Also establish:** the chain is closed-form throughout. If your design contains a solver
loop, an iteration to convergence, or a tolerance, you have mis-modelled the problem.

---

## Step 4 — Stage 1: pixel offsets through the linear transformation

**Do:** Form each source's offset from the reference pixel, then apply the linear
transformation matrix from the header to that offset:

```
dx = px - CRPIX1
dy = py - CRPIX2
x  = CD1_1*dx + CD1_2*dy        # intermediate world coordinates, in degrees
y  = CD2_1*dx + CD2_2*dy
```

Two conventions are load-bearing, and both are settled — do not re-derive them by reflex:

- **Both sides are on the same base.** The catalogue's pixel coordinates and the reference
  pixel cards are both 1-based FITS pixel coordinates, so the difference is taken **raw**.
  The `- 1` you would write to index an image array has no place in this arithmetic.
  Re-basing one side and not the other is a failure mode.
- **The matrix element's first index is the world axis, the second is the pixel axis.**
  It acts on the column vector `(dx, dy)` — matrix times offset, never offset times
  matrix. Applying the transpose is a failure mode.

**Why:** Both are silent errors. Both displace the entire field uniformly, so no source
looks anomalous relative to its neighbours.

**Do not:** apply an additional per-axis scale, a rotation term, or distortion
coefficients that the header does not contain. The matrix already carries scale, rotation
and skew.

---

## Step 5 — Stage 2: invert the projection to native spherical coordinates

**Do:** Apply the inverse of the gnomonic projection:

```
R     = hypot(x, y)                     # degrees
phi   = arg(-y, x) = atan2(x, -y)       # native longitude, degrees
theta = atan2(180/pi, R)                # native latitude, degrees
```

Three things to get right:

- **The argument order in the native longitude is not cosmetic.** The standard writes it
  `arg(-y, x)`; in a two-argument arctangent the *first* argument is the y-like part, and
  here that part is `+x` — hence `atan2(x, -y)`. Any other pairing rotates or reflects the
  whole field.
- **The `180/pi` is there because `R` is in degrees.** The tangent-plane radius in radians
  is `cot(theta)`; expressing `R` in degrees is what puts the conversion factor into the
  numerator.
- **Use the two-argument form for the latitude too** — `atan2(180/pi, R)` rather than
  `atan(180/(pi*R))`. Same value, but it carries the limit at `R = 0` (the reference
  pixel) instead of dividing by zero there.

---

## Step 6 — Stage 3: rotate native coordinates onto the sky. **This is the task.**

Everything before this is bookkeeping. This step is where the task's difficulty lives, and
it has two parts. Do them in order.

### 6a — Locate the celestial pole of the native system

**Do:** Use the projection family you established in Step 2. Gnomonic is a **zenithal**
projection, so its fiducial point is at native latitude `theta_0 = 90` and native
longitude `phi_0 = 0`, and the fiducial point therefore *coincides with the native pole*.

That collapses the general case: the celestial coordinates of the native pole are read
straight off the reference-value cards,

```
alpha_p = CRVAL1
delta_p = CRVAL2
```

with no pole solve and no `LATPOLE` disambiguation.

**Why:** Knowing this is what lets you use the simplified form safely. Do not reach for
the general machinery you do not need — but do not skip the next part, which is the part
that is actually load-bearing.

### 6b — Determine the native longitude of the celestial pole

**Do, in this order:**

1. **Look for the `LONPOLEa` card in the header.** On this task you will find it
   **absent**.
2. **Do not conclude it is zero, and do not conclude it can be omitted.** Absence of the
   card does not mean absence of the quantity — it means the standard supplies a default.
3. **Apply the standard's default rule.** It is conditional on how the reference latitude
   compares with the fiducial point's native latitude:

   ```
   phi_p = phi_0            if delta_0 >= theta_0
   phi_p = phi_0 + 180      otherwise
   ```

   where `delta_0` is the reference latitude from the header (`CRVAL2`), and `phi_0`,
   `theta_0` are the fiducial native coordinates of your projection family — for zenithal
   projections, the values given in Step 6a.

4. **Evaluate that condition against this header's reference latitude and derive
   `phi_p`.** Read the card; do not assume which branch you are on.
5. **Carry the derived value into the rotation** as the offset applied to the native
   longitude, and confirm your rotation formula actually consumes it rather than using
   the native longitude bare.

6. **The rotation itself** (native → celestial, for the zenithal case where the fiducial
   point is the native pole):

   ```
   dphi      = phi - phi_p

   sin(dec)  = sin(theta)*sin(delta_p) + cos(theta)*cos(delta_p)*cos(dphi)

   ra        = alpha_p + arg( num = -cos(theta)*sin(dphi),
                              den =  sin(theta)*cos(delta_p)
                                     - cos(theta)*sin(delta_p)*cos(dphi) )
   ```

   with `arg(num, den) = atan2(num, den)`. Work in radians inside the trigonometry and
   convert back on the way out.

**Why this is the whole task:** if this offset is dropped, the field is mirrored through
the reference point. Every source moves by the same large angle. And — this is the reason
the task is hard rather than merely fiddly — the reference pixel still maps exactly to the
reference value, the coordinates are still in range, and the pipeline still round-trips
perfectly against its own inverse. **Every cheap check stays green.**

**Also:** clamp the `sin(dec)` expression into `[-1, 1]` before calling the inverse sine;
rounding can push it past unity near the pole and raise a domain error.

**Equivalent routes are fine.** The offset can be applied in degrees or radians, folded
into a tangent-plane deprojection, or absorbed into an explicit east/north tangent basis.
What matters is that the orientation it encodes is the correct one, not which algebra
expresses it.

---

## Step 7 — Stage 4: wrap, and serialise at full precision

**Do:** Bring right ascension into `[0, 360)` with `ra = ra % 360` — a modulo, not a sign
flip or a conditional negation. Declination emerges from the inverse sine already in
range. Emit raw double-precision floats.

**Why:** the tolerance on this task is fine enough that rounding the output to a few
decimal places can, on its own, turn a correct answer into a failing one. Match the
requested output shape and spell every id exactly as the catalogue spells it, zero padding
included.

---

## Step 8 — Verify with something that can actually disagree

**Do:** Before declaring the result correct, ask of each check you run: *if I had the
convention wrong, would this check have caught it?*

Checks that **cannot** discriminate — running them proves nothing:

- the reference pixel maps to the reference value (catches only the pixel-base error)
- coordinates are in range (catches nothing geometric)
- your forward transform round-trips through your own inverse (catches nothing — the
  inverse inherits the same convention error and round-trips beautifully while wrong)

Checks that **do** discriminate:

- **A second construction that shares no trigonometry with the first.** Build the
  projection as vector geometry rather than spherical trigonometry and require the two
  routes to agree to near machine precision. Its tangent basis encodes the orientation
  independently, so it catches the dominant failure outright.
- **An orientation check at a genuinely off-axis source.** Reason about what a small step
  in each intermediate coordinate should do to the sky coordinates to first order, and
  confirm the sign and rough magnitude. A discrepancy of several degrees at a few degrees
  off-axis is a wrong rotation convention, not projection curvature.

**Do not** report the answer as verified on the strength of a check from the first list.

---

## Step 9 — Working conditions to respect throughout

- **No astropy, no wcslib, no network.** Write the chain by hand; it is a dozen lines of
  trigonometry needing only a standard math library. Spending the budget on package
  installation or hunting for a WCS library is a process failure, not bad luck.
- **Leave the delivered inputs strictly alone.** They are the reference copy anyone
  reproducing this astrometry will read. Editing, moving or symlinking an input never
  fixes a convention error.

---

## The four failure modes this task discriminates

Named in the reference implementation's own bug-injection knob. Each swaps exactly one
step of the chain above for a different reading of the same standard. All four are
**uniform across the field** — they never displace some sources and not others — and three
of the four still map the reference pixel exactly to the reference value.

| Failure | Which step it corrupts | Relative severity |
|---|---|---|
| Native pole longitude dropped from the rotation | Step 6b | largest |
| Native-longitude arctangent arguments paired wrongly | Step 5 | large |
| Linear transformation matrix transposed | Step 4 | ~1000× tolerance |
| Pixel coordinates re-based while the reference pixel is not | Step 4 | ~40× tolerance |

---

## What a finished run must have produced

Stated as properties to check, not as values:

- one entry per catalogued source, none missing, ids spelled as the catalogue spells them
- the two required numeric fields per entry, finite, at full double precision
- longitude within its conventional range; latitude within its natural range
- the requested wrapper key and nesting
- the delivered input files unmodified

The numeric ground truth lives in the task bundle's frozen expected-values file and in the
verifier that recomputes it at grade time. **It is deliberately not reproduced here** —
this document describes the road, not the destination.
