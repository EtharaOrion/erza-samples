---
name: fits-wcs-tan-astrometry
description: Turn FITS image pixel positions into celestial coordinates (RA/Dec) under a gnomonic TAN world-coordinate system, by hand — CD matrix to intermediate world coordinates, inverse TAN to native spherical, then the LONPOLE-aware rotation onto the sky of Greisen & Calabretta (2002) Paper II. Use when a task hands you a FITS header (CTYPEn, CRPIXj, CRVALi, CDi_j) plus a catalogue of pixel x,y and asks for sky coordinates, especially in an environment with no astropy/wcslib. Not for fitting a WCS from matched stars, not for distortion (SIP/PVi_ja) solutions, and not for non-zenithal projections without re-deriving the pole rotation.
license: MIT
---

# Pixel → sky through a TAN WCS, done by hand

A FITS WCS is **not** "scale the pixel offset and add it to CRVAL". It is a chain of
four transformations defined in Greisen & Calabretta (2002), *Representations of
celestial coordinates in FITS* (Paper II), and the third link — the rotation from
native spherical coordinates onto the celestial sphere — is where hand-rolled
implementations almost always go wrong. That rotation depends on a parameter,
**LONPOLE**, whose value usually is **not in the header**: the standard supplies the
default. Get it wrong and every source lands roughly 8–14° off, while every cheap
self-check you might run still comes back green.

Budget your effort accordingly: stages 1 and 2 are bookkeeping, stage 3 is the task.

## The chain, in the standard's order

```
(px, py)  --CD-->  (x, y)  --inverse TAN-->  (phi, theta)  --rotate-->  (alpha, delta)
 pixel            intermediate               native                     celestial
                  world coords, deg          spherical, deg             RA/Dec, deg
```

Name all four stages before you write code. An implementation that collapses stage 3
into "CRVAL plus the offsets" produces answers that look plausible and are uniformly
wrong. The chain is closed-form throughout — no grid, no iteration, no convergence
tolerance, nothing to fit. If your design has a solver loop in it, you have
mis-modelled the problem.

### Stage 0 — parse the header

Cards are `KEY = VALUE / comment`. Split on the **first** `=` only. If the remaining
value begins with a quote, take the quoted string (`CTYPEn`, `CUNITn`, `RADESYS` are
quoted); **handle the quoted case before you strip the `/ comment`**, or a slash inside
a string value will amputate it. Only the unquoted remainder gets `float()`. Keys may
contain hyphens (`MJD-OBS`); skip blank lines and the `END` card.

Read `CTYPE1`/`CTYPE2` rather than assuming: they declare which world axis is
longitude and which is latitude, and characters 6–8 carry the projection code (`TAN`).

### Stage 1 — CD matrix → intermediate world coordinates

```
dx = px - CRPIX1
dy = py - CRPIX2
x  = CD1_1*dx + CD1_2*dy      # degrees
y  = CD2_1*dx + CD2_2*dy      # degrees
```

Two conventions are load-bearing here:

- **Both sides are 1-based.** Catalogue `x,y` given as FITS pixel coordinates *and*
  `CRPIXj` are 1-based. Subtract them directly. The reflex `px - 1` belongs to indexing
  a numpy image array and has no place in the WCS arithmetic.
- **CD is row-major, world-index first.** `CDi_j` = world axis *i*, pixel axis *j*,
  acting on the column vector `(dx, dy)`. In numpy that is `cd @ offset`, never
  `offset @ cd`.

The CD matrix already carries plate scale, rotation and skew. If the header supplies
CD, do not also multiply in a `CDELTn`, and do not invent `CROTA2`, `PVi_ja` or SIP
`A_`/`B_` distortion terms that are not in the file.

### Stage 2 — inverse TAN → native spherical (Paper II, Table 13)

```
R_theta = hypot(x, y)                 # degrees, because x and y are degrees
phi     = arg(-y, x) = atan2(x, -y)   # degrees
theta   = atan2(180/pi, R_theta)      # degrees
```

- The factor **180/π** appears because `R_theta` is expressed in degrees; the
  tangent-plane radius in radians is `cot(theta)`.
- Write θ as `atan2(180/pi, R_theta)` rather than `atan(180/(pi*R_theta))`. Same value,
  but it carries the R→0 limit (θ = 90° exactly at the reference pixel) instead of
  dividing by zero there.
- **The argument order in φ is not cosmetic.** `arg(-y, x)` means `atan2(x, -y)`: the
  first argument of `atan2` is the *y*-like part, and here that part is `+x`. Any other
  pairing rotates or reflects the entire field.

### Stage 3 — native → celestial (Paper II eq. 2). This is the one.

TAN is a **zenithal** projection, so θ₀ = 90° and the fiducial point *is* the native
pole. That buys you a simplification: the celestial pole of the native system is just
`(alpha_p, delta_p) = (CRVAL1, CRVAL2)`. No pole solve, no `LATPOLE` disambiguation.

What you must not skip is φ_p:

```
phi_p = LONPOLE                          # from the header if present; see below
dphi  = phi - phi_p

sin(delta) = sin(theta)*sin(delta_p) + cos(theta)*cos(delta_p)*cos(dphi)

alpha = alpha_p + arg( num = -cos(theta)*sin(dphi),
                       den =  sin(theta)*cos(delta_p)
                              - cos(theta)*sin(delta_p)*cos(dphi) )
```

with `arg(num, den) = atan2(num, den)`. Clamp the `sin(delta)` expression into
`[-1, 1]` before `asin` — rounding pushes it past unity near the pole and raises a
domain error.

**The LONPOLE default is a property of the standard, not of your file.** When the
`LONPOLEa` card is absent, Paper II specifies

> φ_p = φ₀ if δ₀ ≥ θ₀, otherwise φ_p = φ₀ + 180°

and for *every* zenithal projection (TAN, SIN, ARC, ZEA, …) φ₀ = 0 and θ₀ = 90°.
So unless your reference point sits exactly at the celestial pole, the default is
**φ_p = 180°**. In code that is nothing more than reading the card with a default —
`float(hdr.get("LONPOLE", 180.0))` — but you have to know to do it.

Geometrically: φ_p = 180° is the orientation in which the intermediate axes **+x points
east and +y points north** at the reference point. φ_p = 0 points them west and south.
That is the whole of the dominant failure: a field mirrored through the reference point.

### Stage 4 — wrap and emit

Convert to degrees, then `ra = ra % 360.0` so RA lands in [0, 360) — a modulo, not a
sign flip, and never leave it negative. Dec falls out of `asin` already in [-90, 90].

Serialise at **full double precision**. Tolerances in astrometry are arcseconds;
rounding coordinates to three decimal places injects up to 5e-4 deg of quantisation on
its own and can turn a correct answer into a failed one. Emit the raw float (or ≥ 6
decimals) and match the requested output shape and id spelling exactly — every source
present, ids spelled as the catalogue spells them (zero padding included), and whatever
wrapper key was asked for.

### Working conditions

Where `astropy` and `wcslib` are unavailable and there is no network, write the
projection out by hand rather than spending the budget on `pip` or on hunting for a
WCS package — the whole chain is a dozen lines of trigonometry and needs nothing beyond
`math`. And leave the delivered header and catalogue strictly alone: they are the
reference copy anyone reproducing your astrometry will read, and editing, moving or
symlinking an input never fixes a convention error.

## The four traps, ranked by how often they bite

| Trap | What it looks like | Cost |
|---|---|---|
| **Dropped LONPOLE** | Eq. (2) coded with `dphi = phi`; or a hand-rolled "rotate by Dec, then by RA" Euler construction | ~8–14° on every source |
| **Swapped axes** | `phi = atan2(-y, x)` or `atan2(y, x)`; treating axis 1 as Dec | ~3–12° on every source |
| **Transposed CD** | `offset @ cd`; building the array column-major | ~0.4–0.7°, over 1000× a typical tolerance |
| **0-based pixels** | `px - 1` alongside a 1-based CRPIX | ~0.02°, small-looking and still ~40× tolerance |

All four are **uniform across the field** — they do not displace "some" sources, they
displace all of them by the same convention error. You never end up with a partly-right
field to salvage: either the global convention is right, or the whole field has moved.

Three of the four (everything but the pixel-base slip) still map CRPIX exactly to CRVAL.

## Verify with something that can actually disagree

Cheap checks are green on all the wrong branches — that is precisely why these failures
are confident rather than hesitant. Know what each check does and does not catch:

- **CRPIX → CRVAL exactly.** Catches only the pixel-base slip. Green for dropped
  LONPOLE, swapped axes, and a transposed CD. Necessary, nowhere near sufficient.
- **Values in range / RA in [0,360) / |Dec| ≤ 90.** Catches nothing geometric. Green for
  all four traps.
- **Round-tripping your own forward through your own inverse.** Catches nothing. The
  inverse inherits the same convention error, so it round-trips beautifully while being
  wrong.

What does discriminate:

- **A second route that shares no trig with the first.** Build the gnomonic projection
  as pure vector geometry instead of spherical trigonometry, and require agreement with
  the Paper II route to ~1e-9 deg. The construction and its basis vectors are in
  `references/verification.md`; its east/north tangent basis encodes the φ_p = 180
  orientation independently, so it catches the dominant failure outright.
- **An orientation check at a genuinely off-axis source.** To first order, moving one
  intermediate degree in +y should move Dec by about +1°, and one degree in +x should
  move RA·cos(dec) by about +1°. A residual of several degrees at a few-degree offset is
  a wrong rotation convention, not projection curvature.

## References

- `references/paper-ii-tan.md` — where each constant comes from, the general LONPOLE
  default rule, and the zenithal simplifications you are allowed to make.
- `references/verification.md` — the independent vector-geometry route, and a
  discrimination table of checks versus failure modes.
- `references/header-and-output.md` — header card parsing edge cases, reading the source
  catalogue, working without astropy, and answer-file hygiene.
