---
name: geomagnetic-declination-igrf
description: Compute magnetic declination (and the other geomagnetic field elements) at a geodetic point and epoch by evaluating the IGRF-13 field by hand - parse the Schmidt semi-normalised Gauss coefficients, convert geodetic coordinates to geocentric on the WGS84 ellipsoid, synthesise the spherical-harmonic field to degree 13, rotate it back to the geodetic frame, and read off declination D = atan2(East, North). Use when a task gives a geographic position (and possibly an epoch) and needs the magnetic declination, or needs to reduce a magnetic-referenced bearing/azimuth to true north, especially with no geomagnetic library and no network. Not for computing crustal or external (magnetospheric) fields, not for dates outside 1900-2025, and not when a task supplies its own field model to use instead.
license: MIT
---

# Magnetic declination from IGRF-13, by hand

A magnetic compass measures azimuth relative to *magnetic* north. To reduce a
magnetic azimuth to a **true (geographic) azimuth** you add the local **magnetic
declination** D (the angle from true north to magnetic north, positive east):

```
true_azimuth = (magnetic_azimuth + D) mod 360
```

The whole difficulty is D. Declination is **not** recallable or estimable to
survey precision, and it is **not** a single regional number: it varies by tens
of degrees across a survey area and drifts by tenths of a degree per year. It has
to be *computed* from the geomagnetic field model. The model is the International
Geomagnetic Reference Field, 13th generation (IGRF-13): a spherical-harmonic
description of the main field whose coefficients are region-independent and
published, but far too many to recall. This skill ships the coefficients and the
synthesis, which together give D at any point and epoch to model precision.

Budget your effort accordingly: parsing and the harmonic sum are bookkeeping. The
two places hand-rolled implementations go wrong are the **geodetic-to-geocentric
conversion** (stage 2) and the **Schmidt normalisation of the Legendre functions**
(stage 3). Get either wrong and every station moves off by more than a survey
tolerance while the numbers still look reasonable.

## The chain, in order

```
(lat_gd, lon, h)  --geod->geoc-->  (theta, r, lon)  --SH synth-->  (Br, Btheta, Bphi)
 geodetic deg, km                   geocentric                      geocentric field, nT
                                                     --rotate-->  (X north, Y east, Z down)
                                                     D = atan2(Y, X)   I = atan2(Z, hypot(X,Y))
```

The chain is closed-form throughout - no fitting, no iteration. If your design has
a solver loop in it, you have mis-modelled the problem.

### Stage 0 - the coefficients

The Gauss coefficients live in `references/igrf13coeffs.txt` (the IAGA V-MOD
distribution of IGRF-13; Alken et al. 2021, doi:10.1186/s40623-020-01288-x). Each
line after the two-line header is

```
c/s  n  m  <value at 1900.0>  <1905.0>  ...  <2020.0>  <SV 2020-2025>
```

where `c/s` is `g` (cosine term) or `h` (sine term), `n` is the degree
(1..13), `m` is the order (0..n), the 25 numeric columns are the coefficient in
nanotesla at the 5-year epochs 1900.0 through 2020.0, and the final column is the
secular-variation rate in nT/yr for 2020-2025. Parse `g[(n,m)]`, `h[(n,m)]`.

### Stage 1 - coefficients at the epoch

The 5-year epoch nodes and the secular-variation column are defined by IGRF-13
(Alken et al. 2021). For an epoch on one of the nodes, read that column directly.
Between two nodes, **linearly interpolate** the two bracketing columns. Beyond the
last node (2020.0), **linearly extrapolate** with the secular-variation column:
`g(t) = g(2020.0) + (t - 2020.0) * SV`. This linear scheme is the model's own
definition of time dependence; do not substitute a smoother interpolant.

### Stage 2 - geodetic to geocentric (do not skip this)

The station coordinates are **geodetic** (latitude on the WGS84 ellipsoid, height
above it). The harmonic synthesis is defined in **geocentric spherical**
coordinates. You must convert, using the WGS84 defining parameters (NGA
TR8350.2, 2014). The semi-major axis is `a = 6378.137` km and
`e^2 = 0.00669437999014`:

```
b   = a*sqrt(1 - e^2)
s2  = sin(lat_gd)^2 ;  c2 = cos(lat_gd)^2
tmp = h*sqrt(a^2*c2 + b^2*s2)
beta  = atan( (tmp + b^2)/(tmp + a^2) * tan(lat_gd) )    # geocentric latitude
theta = pi/2 - beta                                       # geocentric colatitude
r   = sqrt( h^2 + 2*tmp + a^2*(1 - (1-(b/a)^4)*s2)/(1 - (1-(b/a)^2)*s2) )
```

**Treating the geodetic latitude as if it were geocentric** (using
`theta = 90 - lat_gd`, `r = 6371.2 + h`) is the single most common error here. The
geodetic and geocentric latitudes differ by up to a fifth of a degree at
mid-latitudes; that difference feeds straight into D and moves the answer past any
survey tolerance. The IGRF geomagnetic reference radius `RE = 6371.2` km (Alken et
al. 2021) appears **only** as the ratio base in the synthesis (stage 4), never as
the station radius.

### Stage 3 - Schmidt semi-normalised Legendre functions

You need `P_n^m(cos theta)` and `dP_n^m/dtheta`, Schmidt semi-normalised, for all
`n = 1..13`, `m = 0..n`. The robust route is the Gauss-normalised recurrence
followed by an explicit Schmidt factor `S` - **not** a single recurrence with the
normalisation folded in, which is where sign/scale slips hide.

```
# Gauss-normalised functions (unnormalised recurrence):
P[0,0] = 1
P[n,n]   = sin(theta) * P[n-1,n-1]
dP[n,n]  = sin(theta) * dP[n-1,n-1] + cos(theta) * P[n-1,n-1]
# for m < n:
K = 0                      if n == 1
K = ((n-1)^2 - m^2)/((2n-1)(2n-3))   if n > 1
P[n,m]   = cos(theta)*P[n-1,m]  - K*P[n-2,m]
dP[n,m]  = cos(theta)*dP[n-1,m] - sin(theta)*P[n-1,m] - K*dP[n-2,m]

# Schmidt factor, then multiply P and dP by it:
S[0,0] = 1
S[n,0] = S[n-1,0] * (2n-1)/n
S[n,m] = S[n,m-1] * sqrt( (n-m+1) * (1 + [m==1]) / (n+m) )     # m >= 1
P[n,m]  *= S[n,m] ;  dP[n,m] *= S[n,m]
```

A wrong normalisation typically leaves the low-degree terms about right and
corrupts the rest, so D can come out several to ~10 deg off - large, uniform, and
not obviously a bug. `references/coefficients-and-synthesis.md` states the
recurrence and the check values in full.

### Stage 4 - synthesise the field, rotate to geodetic

With `ratio = RE/r`, sum over all `n, m`:

```
Br     =  sum (ratio)^(n+2) * (n+1) * [g cos(m*lon) + h sin(m*lon)] * P[n,m]
Btheta = -sum (ratio)^(n+2)         * [g cos(m*lon) + h sin(m*lon)] * dP[n,m]
Bphi   = -sum (ratio)^(n+2) * m      * [-g sin(m*lon) + h cos(m*lon)] * P[n,m] / sin(theta)
```

These are **geocentric** components (Bphi is already geographic east). Rotate the
`(Btheta, Br)` pair back into the geodetic north/up frame - the rotation angle is
the same geodetic-minus-geocentric latitude difference from stage 2. The series
form is in `references/coefficients-and-synthesis.md`. Then

```
X = B_north (geodetic) ;  Y = Bphi (east) ;  Z = B_down
D = atan2(Y, X)     # declination, radians -> degrees, east positive
```

Declination depends on X and Y, and the geodetic rotation changes X, so the
stage-2 conversion is not optional even though you "only need D".

### Stage 5 - reduce the azimuth and emit

```
true_azimuth = (magnetic_azimuth + D) mod 360
```

Keep D and the azimuth at **full double precision** through to output - do not
round D to whole or tenths of a degree, and do not round the emitted azimuth to a
few decimals; declination reductions are quoted to a fraction of a degree and
premature rounding can move a correct value across the line. Match the requested
output shape and spell every station id exactly as the input spells it.

### Working conditions

With no geomagnetic library and no network, write the synthesis by hand - it is a
few dozen lines needing only a standard math library and the shipped coefficient
file. Do not spend the budget on `pip` or on hunting for a package. Leave the
delivered inputs unmodified.

## The traps, ranked by how often they bite

| Trap | What it looks like | Cost |
|---|---|---|
| **Geodetic used as geocentric** | `theta = 90 - lat`, `r = 6371.2 + h`; stage 2 skipped | a couple tenths of a degree at every station |
| **Schmidt normalisation wrong** | one folded recurrence; missing `S` factor | several to ~10 deg, uniform |
| **Chart / estimated declination** | the single old-chart figure applied everywhere, or a recalled ballpark | many degrees; wrong at every station |
| **Declination sign / azimuth sense** | `magnetic - D`, or D measured west-positive | ~2*D at every station |
| **Rounded D** | D truncated to whole/tenths of a degree before adding | up to ~0.5 deg |

All of these are **uniform across the network** - they do not move some stations
and spare others. Either the method is right everywhere or the whole network has
shifted.

## Verify with something that can actually disagree

- **Independent field route.** Recompute one station's field by numerically
  differentiating the scalar potential `V = a * sum (a/r)^(n+1) (g cos m*lon +
  h sin m*lon) P_n^m` (finite differences in r, theta, lon) instead of the
  analytic `Br/Btheta/Bphi`, and require the two D values to agree to ~1e-4 deg.
  A shared normalisation error will *not* cancel between the two routes.
- **Sign and magnitude sanity.** In the northern mid-latitudes the horizontal
  field points roughly north; a declination of many tens of degrees, or the wrong
  sign, is a convention error, not the true value.
- **Do not** treat "the reference point reproduces the chart value" or "D is in a
  plausible range" as verification - a wrong normalisation or a skipped geodetic
  conversion passes both.

## References

- `references/igrf13coeffs.txt` - the IGRF-13 Schmidt semi-normalised Gauss
  coefficients (IAGA V-MOD; Alken et al. 2021, *Earth, Planets and Space* 73:49,
  doi:10.1186/s40623-020-01288-x).
- `references/coefficients-and-synthesis.md` - the file format, the full Legendre
  recurrence and Schmidt factor, the geodetic<->geocentric transforms and the
  field-vector rotation, and worked check values.
