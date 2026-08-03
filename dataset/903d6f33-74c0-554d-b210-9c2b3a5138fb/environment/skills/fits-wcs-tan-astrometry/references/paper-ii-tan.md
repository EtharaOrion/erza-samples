# Where the TAN constants come from

Background for the four-stage chain in `SKILL.md`. Read this when a constant looks
arbitrary, when you are tempted to "simplify" the pole rotation, or when you are
adapting the method to a projection other than TAN.

## Vocabulary

Paper II separates three coordinate systems that hand-rolled code tends to merge:

| Symbol | Name | Where it lives |
|---|---|---|
| `(px, py)` | pixel coordinates | the image / the source catalogue, 1-based |
| `(x, y)` | intermediate world coordinates | the tangent plane, in degrees |
| `(phi, theta)` | native spherical coordinates | a sphere whose pole is the projection's fiducial point |
| `(alpha, delta)` | celestial spherical coordinates | the sky (RA, Dec) |

The whole point of the native system is that the projection maths is easy in a frame
where the fiducial point is the pole; the rotation onto the sky is then a separate,
purely spherical step. If your code never constructs `(phi, theta)`, you have merged
stages 2 and 3 and you are almost certainly missing a convention.

## The linear stage

`CDi_j` is a full 2×2 linear map from pixel offsets to intermediate world coordinates
in degrees. It absorbs plate scale, rotation, and any skew or non-orthogonality between
the detector axes. That last part matters for debugging: because a real field has shear,
`CD1_2 != CD2_1`, so `CD` and `CDᵀ` are genuinely different transforms — but they share
a determinant and both map the reference pixel to the reference point, so neither
det-based nor CRPIX-based checks will tell them apart.

A structural check that does: a unit step along pixel axis 1, i.e. `(dx, dy) = (1, 0)`,
must give `(x, y) = (CD1_1, CD2_1)` — first column, not first row. If your code gives
`(CD1_1, CD1_2)`, you have transposed it.

Older headers express the same information as `CDELTn` plus `CROTA2`, and newer ones as
`PCi_j` plus `CDELTn`. These are alternatives, not supplements. If the header carries
`CDi_j`, apply it alone. Similarly, distortion conventions (`PVi_ja` for the projection
parameters, SIP `A_ORDER`/`A_p_q`/`B_p_q` arrays) only exist if the header declares
them. Adding a distortion model that is not in the file is over-modelling and moves
every source.

## The inverse TAN

The gnomonic projection places the observer at the centre of the sphere and projects
onto the plane tangent at the fiducial point. The forward relation for a zenithal
projection is `R_theta = (180/pi) * cot(theta)` when `R_theta` is in degrees — the
`180/pi` is a pure unit conversion, present because Paper II works in degrees while
`cot(theta)` is dimensionless.

Inverting: `theta = atan(180 / (pi * R_theta))`. Prefer the two-argument form
`atan2(180/pi, R_theta)`. It is identical in value for `R_theta > 0`, and at the
reference pixel, where `R_theta = 0`, it returns exactly 90° instead of raising.

The native longitude is `phi = arg(-y, x)`. Paper II's `arg(a, b)` returns the angle of
the point with abscissa `a` and ordinate `b`, which in the usual `atan2(ordinate,
abscissa)` signature is `atan2(x, -y)`. Two habits produce a wrong field here:
transcribing `arg` as if its arguments were already in `atan2` order, and "tidying"
the negation. Both silently reorient the sky.

Consequence of the `-y` in the first slot: at φ_p = 180 the native longitude is measured
from the direction of *decreasing* y, which is what ultimately makes north come out
along +y after the rotation.

## The pole rotation and LONPOLE

Paper II eq. (2) rotates `(phi, theta)` onto `(alpha, delta)` given the celestial
coordinates of the native pole `(alpha_p, delta_p)` and the native longitude of the
celestial pole, `phi_p`.

For a **zenithal** projection the fiducial point is the native pole by construction
(`theta_0 = 90`), so `(alpha_p, delta_p) = (CRVAL1, CRVAL2)` immediately. There is no
pole equation to solve and `LATPOLEa` never comes into play. Do not go looking for one;
the general Paper II pole solve exists for non-zenithal projections where the fiducial
point is on the native equator.

`phi_p` comes from `LONPOLEa`. When that card is absent the standard supplies:

    phi_p = phi_0            if delta_0 >= theta_0
    phi_p = phi_0 + 180 deg  otherwise

`phi_0` and `theta_0` are the native coordinates of the fiducial point, and for every
zenithal projection they are 0 and 90 respectively. `delta_0` is the reference
declination, i.e. `CRVAL2`. So `delta_0 >= 90` only at the exact celestial pole, and in
every practical field the default is **`phi_p = 180`**.

This is the single most valuable thing to remember about hand-rolled FITS WCS: the
absence of a LONPOLE card does not mean the parameter is absent, it means the default
applies. Read the header with `float(hdr.get("LONPOLE", 180.0))` and move on.

The failure it prevents is symmetry-preserving. With `phi_p = 0` — which is what you get
from `dphi = phi`, or from a "rotate by declination then by right ascension" Euler
construction — the reference pixel still maps exactly to CRVAL, angles are still in
range, the transform is still invertible, and the field is reflected through the
reference point. Sources land on the order of ten degrees away with nothing in the
output that looks anomalous.

## Adapting to other projections

The stage-1, stage-3 and stage-4 code is projection-independent; only stage 2 changes,
along with `(phi_0, theta_0)`. For the other zenithals (SIN, ARC, ZEA, STG) the fiducial
point is still the native pole and the LONPOLE default is still 180 — swap only the
`R_theta ↔ theta` relation from Paper II Table 13. For cylindrical, conic or
pseudo-cylindrical projections the fiducial point is on the native equator, the LONPOLE
default is 0 for `delta_0 >= 0`, and you must solve the pole equation. Do not carry
"LONPOLE is 180" across that boundary as a rule of thumb.
