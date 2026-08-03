# Verifying a hand-rolled WCS

A WCS convention error is uniform: it moves every source by roughly the same amount in
roughly the same way. That makes it invisible to scatter-based sanity checks and to
anything that reuses your own transform. Choose checks by what they can *disagree* with.

## Discrimination table

| Check | Pixel base | CD transpose | Swapped axes | Dropped LONPOLE |
|---|---|---|---|---|
| CRPIX maps to CRVAL | catches | green | green | green |
| RA in [0,360), \|Dec\| ≤ 90 | green | green | green | green |
| Round-trip own forward ∘ own inverse | green | green | green | green |
| Determinant / plate-scale sanity | green | green | green | green |
| Independent vector route | catches | catches | catches | **catches** |
| First-order orientation at an off-axis source | weak | catches | catches | **catches** |

"green" means the check passes on the wrong answer. Three of the four traps sail through
everything in the top half of the table, which is why these failures come out confident.

## The independent route: gnomonic as vector geometry

The value of this check is that it shares no code, no trig identity and no intermediate
representation with the Paper II route — it never constructs `(phi, theta)` at all. It
is worth the twenty minutes.

The gnomonic projection *is* the perspective projection from the centre of the sphere
onto the plane tangent at the reference point. So:

1. Build the unit vector `p̂` pointing at `(CRVAL1, CRVAL2)` in equatorial Cartesian
   coordinates — the usual `(cos δ cos α, cos δ sin α, sin δ)`.
2. Build the local tangent basis at that point:
   - east: `ê = (-sin α₀, cos α₀, 0)`
   - north: `n̂ = (-sin δ₀ cos α₀, -sin δ₀ sin α₀, cos δ₀)`
3. Take the intermediate world coordinates `(x, y)` from stage 1 — the *same* CD step,
   this check is not meant to re-audit stage 1 — convert them to radians, and form
   `v = p̂ + radians(x)·ê + radians(y)·n̂`.
4. Normalise `v`, then read the sky back off it:
   `ra = atan2(v_y, v_x) mod 360`, `dec = atan2(v_z, hypot(v_x, v_y))`.

Note what step 2 encodes: `+x` along east and `+y` along north. That is exactly the
`phi_p = 180` orientation, arrived at from geometry rather than from a convention
lookup. If your Paper II implementation dropped LONPOLE, the two routes will disagree by
many degrees and you will see it immediately.

Agreement between a correct pair of implementations is at the floor of double precision
— think 1e-13 deg or better across a field. Set the acceptance threshold somewhere
around 1e-9 deg: tight enough that no convention error can hide under it, loose enough
that accumulated rounding never trips it.

If the two disagree, the vector route is usually the easier one to trust, because it has
fewer places to hide a sign. Diagnose the Paper II route against it rather than the
other way round.

## First-order orientation check

Pick a source that is genuinely off-axis — several intermediate degrees from the
reference point, not one of the near-centre ones, because near the centre every wrong
convention is also nearly right in absolute terms.

At that source, compare against the flat tangent-plane estimate:

    dec ≈ CRVAL2 + y
    (ra - CRVAL1) * cos(dec) ≈ x

Gnomonic curvature is a second-order effect; at a few degrees off-axis these should
agree to well under a degree. A residual of several degrees is not curvature, it is a
reflected or rotated field. A residual that grows linearly with offset in one axis only
points at the linear stage instead.

## Reading the failure signature

If you have two disagreeing implementations, the size of the disagreement narrows it
down fast:

- **~8–14°, and the reference pixel still maps to CRVAL** — dropped LONPOLE. Look for
  `dphi = phi` where it should be `phi - phi_p`, or a hand-built Euler rotation.
- **A few degrees to ~12°, varying strongly with position angle** — swapped axes in the
  `phi = arg(-y, x)` step.
- **Tenths of a degree** — transposed CD.
- **Hundredths of a degree, essentially constant across the field, and CRPIX no longer
  maps to CRVAL** — a one-pixel base error.
- **Sub-arcsecond and only in the output file** — precision lost at serialisation.

## What to check about the answer file, not the maths

Before you call it done: every requested id present and spelled exactly as specified
(zero-padded), both fields numeric and finite (no NaN from an unclamped `asin`, no
`None` from a skipped row), Dec inside [-90, 90], RA wrapped into [0, 360) with a modulo
rather than left negative, and enough decimal places written that serialisation is not
itself a source of error.
