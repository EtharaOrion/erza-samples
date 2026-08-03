---
name: antex-receiver-antenna-calibration
description: >-
  Apply a receiver antenna's published phase-centre calibration - the mean offset
  vector per carrier frequency plus the gridded phase-centre variations - to a
  satellite line of sight, giving the carrier-phase correction in millimetres. Use
  when a task supplies satellite azimuths and elevations for a named receiver
  antenna and asks for the phase-centre correction, or for the offset between the
  antenna reference point and the electrical phase centre along a line of sight. Do
  not use for satellite transmitter antennas, which are calculated in the
  spacecraft body frame against the nadir angle instead; do not use when the
  correction is already applied in the supplied observations; and do not use for
  the site eccentricity, the surveyed vector from the ground marker to the antenna
  reference point, which is a separate quantity carried in the station log.
---

# Phase-centre correction for a receiver antenna

A geodetic receiver antenna does not observe from a single point. The point at
which the carrier phase is effectively measured - the electrical phase centre -
moves with the direction the signal arrives from and with the carrier frequency.
The displacement between it and the **antenna reference point** (ARP, the physical
datum a station log measures to) reaches a few centimetres, which is one to two
orders of magnitude larger than the noise of a carrier-phase observation.

The displacement is split in two:

- the **phase-centre offset** (PCO), a single mean vector per carrier frequency in
  the local North/East/Up frame, from the ARP to the mean phase centre; and
- the **phase-centre variation** (PCV), the residual that remains after the mean
  vector is removed, tabulated against the direction of arrival.

Both are properties of the antenna model, not of the site or of the constellation.
They are determined by measurement - a robot in the field or an anechoic chamber -
and they change with the radome fitted. Two geodetic antennas at one station can
differ by most of a decimetre in the vertical component. Nothing in the geometry of
a line of sight predicts them; the antenna's own calibration table is required.

## What is in a calibration block

The blocks in `references/` are in the ANTEX antenna exchange format, one file per
antenna, each holding a single antenna. The format is defined by the International
GNSS Service (`https://files.igs.org/pub/data/format/antex14.txt`).

Header records, each carrying its label in columns 61-80:

| record | content |
|---|---|
| `TYPE / SERIAL NO` | the antenna label, columns 1-20 |
| `DAZI` | azimuth step of the variation grid, in degrees; zero means the grid is azimuth-independent |
| `ZEN1 / ZEN2 / DZEN` | first zenith angle, last zenith angle and step, in degrees |
| `# OF FREQUENCIES` | number of frequency blocks that follow |

Then one block per carrier, opened by `START OF FREQUENCY` and closed by
`END OF FREQUENCY`, both carrying the three-character frequency code in columns
4-6. Inside a block:

| record | content |
|---|---|
| `NORTH / EAST / UP` | the PCO vector in millimetres, three fields of ten columns |
| `NOAZI` row | the azimuth-averaged variation across the zenith nodes, in millimetres |
| numeric rows | one row per azimuth node: the azimuth in columns 1-8, then the variation at each zenith node |

The frequency code is the satellite system letter followed by the two-digit carrier
number, and the format specification fixes the mapping
(`https://files.igs.org/pub/data/format/antex14.txt`, section 4): `G01`, `G02` and
`G05` are the GPS L1, L2 and L5 carriers; `E01`, `E05`, `E06`, `E07` and `E08` the
Galileo E1, E5a, E6, E5b and E5 carriers; `R01` and `R02` the GLONASS G1 and G2
carriers; and the `C`, `J` and `S` prefixes carry the BeiDou, QZSS and SBAS
entries. Every value in the block is in millimetres, and the zenith grid runs from
the zenith outward, so the last column is the horizon and the first is directly
overhead.

The same specification fixes the sign convention for a receiver antenna: the mean
phase-centre position is the antenna reference point plus the offset vector, given
in a topocentric north/east/up system, and the observed distance is the geometric
distance to the mean phase centre plus the phase-centre variation. Azimuth counts
clockwise from north toward east.

## Procedure

1. **Load that antenna's own block.** Match on the antenna label. A calibration
   never transfers between antenna models, and a model with a radome fitted is a
   different calibration from the same model without one.

2. **Select the frequency block by its code.** Several codes often share one
   calibration inside a file - a block for `G01` and a block for `E01` may carry
   identical values, because the carriers sit at the same frequency - but this is
   a property of the published table, not a rule, so read the block asked for
   rather than substituting a neighbour.

3. **Project the offset onto the line of sight.** With azimuth `az` clockwise from
   geodetic north and elevation `el` above the horizon, the unit vector towards the
   satellite in the local North/East/Up frame is

       e = (cos(el) * cos(az), cos(el) * sin(az), sin(el))

   and the projected offset is the dot product `N * e_N + E * e_E + U * e_U`.
   At low elevation the vertical component is heavily foreshortened, so the
   horizontal components matter most where the variation is largest.

4. **Interpolate the variation.** The grid is indexed by azimuth and by **zenith
   angle**, not by elevation, so convert first: `zenith = 90 - el`. Locate the
   bracketing azimuth rows and the bracketing zenith columns, and take the value
   bilinearly in the two arguments:

       PCV = (1-fa)(1-fz) v00 + (1-fa) fz v01 + fa (1-fz) v10 + fa fz v11

   where `fa` and `fz` are the fractional positions between the bracketing nodes.
   Bilinear interpolation on this grid is what the standard processing packages
   apply. The azimuth axis is periodic and published tables usually repeat the
   first row at the end of the range, so an azimuth beyond the last tabulated row
   wraps to the first.

5. **Add the two terms.** The correction is the projected offset plus the
   interpolated variation, in millimetres. Both terms carry sign; the variation is
   added, not subtracted.

## Traps

- **Substituting a similar antenna.** A nominal offset for another geodetic
  antenna, or a class-typical value, is not this antenna's calibration. Vertical
  offsets across common geodetic models span roughly a decimetre, and the variation
  pattern differs in shape as well as in scale, so the substitution biases the whole
  station.
- **Elevation where the table wants a zenith angle.** The grid columns run from the
  zenith outward. Indexing them with the elevation angle silently mirrors the
  pattern about 45 degrees.
- **Dropping the variation.** The offset is the mean over the hemisphere; the
  variation is what is left after that mean is removed and it does not vanish. On a
  geodetic antenna it runs to several millimetres across the usable sky, and it is
  systematic with elevation rather than random.
- **Reading the azimuth-averaged row instead of the grid.** The `NOAZI` row is a
  convenience for azimuth-independent processing. Where a `DAZI` grid is published
  it is the fuller model, and the two disagree by up to a few millimetres.
- **Mixing units.** ANTEX carries millimetres throughout. Processing software often
  works in metres; converting one term and not the other is a common defect.

## Check values

Read directly off the blocks in `references/`, which are extracts of the published
IGS20 antenna model (`https://files.igs.org/pub/station/general/igs20.atx`), for
orientation while wiring up the parser and the interpolation. Frequency code `E08`,
azimuth 62.5 degrees, elevation 37.5 degrees - a direction that falls between grid
nodes on both axes, so it exercises the bilinear step:

| antenna | PCO N, E, U (mm) | PCV (mm) | projected offset (mm) | correction (mm) |
|---|---|---|---|---|
| ANT-A | 0.10, 0.56, 59.72 | -3.5975 | 36.7859 | 33.1884 |
| ANT-B | 0.14, 0.21, 158.36 | -4.4800 | 96.6025 | 92.1225 |
| ANT-C | -0.22, 0.08, 122.78 | -4.8900 | 74.7194 | 69.8294 |

This frequency and this direction are outside the set a task instance asks about;
they exercise the parser and the interpolation, not the answer.

## Provenance of the blocks

The three blocks are real receiver-antenna calibrations from the IGS20 antenna
model, the absolute antenna correction set adopted by the International GNSS
Service with the IGS20 reference frame, retrieved 2026-07-27 from
`https://files.igs.org/pub/station/general/igs20.atx`. IGS products are made
available to the public without charge or restriction under the IGS data and
product policy (`https://igs.org/data-products-overview/`), which asks that the
service be acknowledged.

The antennas are relabelled ANT-A, ANT-B and ANT-C here, and the manufacturer type
string, the radome code, the calibrating agency and the calibration date are
withheld, so the blocks travel with the task rather than being looked up from the
antenna index. See `references/antex_format.md` for the measurement basis and the
record layout in detail.
