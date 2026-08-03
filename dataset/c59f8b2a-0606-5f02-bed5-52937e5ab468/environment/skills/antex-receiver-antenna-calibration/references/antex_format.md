# Antenna phase-centre calibration: what it measures and how it is published

Background for the procedure in `SKILL.md`. Nothing here is specific to any one
task instance.

## Why a calibration exists

A carrier-phase observation is a range to the point at which the phase is
effectively measured. For a geodetic antenna that point is not the physical centre
of the element, not the antenna reference point stamped on the housing, and not
fixed: the element, the ground plane, the choke rings and the radome together shape
a radiation pattern whose phase front is not a perfect sphere. The apparent range
therefore depends on where in the sky the satellite is, and the dependence is
systematic rather than random.

Because the dependence is systematic, it does not average away over a session. Left
uncorrected it maps almost entirely into the estimated station height and into the
tropospheric zenith delay, which correlate strongly with each other, and the height
error runs to centimetres. This is why a phase-centre model is a required input to
any geodetic-quality processing rather than a refinement.

The correction is published as two parts. The mean offset, one vector per carrier
frequency, carries the bulk of the displacement between the reference point and the
phase centre. The variations carry what is left after that mean is removed,
tabulated against the direction of arrival. Splitting it this way keeps the table
small and lets software that models only the mean still capture most of the effect.

## How a calibration is determined

Two independent measurement techniques are in use, and their agreement is what
makes the published values trustworthy.

A **robot calibration** mounts the antenna on an articulated arm in the open field
and rotates and tilts it through thousands of orientations while tracking real
satellites. Differencing observations taken in different orientations against a
nearby reference antenna cancels the atmosphere, the satellite orbit and the clock
error, and leaves the antenna pattern. Because the antenna itself is moved rather
than the satellites waited for, the whole hemisphere is covered in hours and the
elevation-dependent part is separated from the tropospheric delay, which a static
calibration cannot do.

An **anechoic-chamber calibration** transmits a signal at the antenna from a
positioner inside a chamber lined with absorber, measuring the phase response
directly across azimuth and elevation. It reaches directions a field calibration
cannot and is free of multipath, at the cost of representing the antenna in
isolation rather than on a real mount.

Both are **absolute** techniques: they yield the pattern of the antenna itself
rather than its difference from an assumed-ideal reference antenna. The earlier
generation of published values was **relative**, tied by construction to one
reference model whose own pattern was assumed to be zero, which propagated that
model's error into every other antenna and into the terrestrial scale. The switch
to absolute values was made together with the reference frame it accompanies, and
the two are used as a matched pair - values from one generation are not mixed with
another (Schmid and others, 2016, *Absolute IGS antenna phase center model igs08.atx*,
Journal of Geodesy 90, doi:10.1007/s00190-015-0876-3).

## Why the values do not transfer

The pattern belongs to the antenna model as built. A radome changes it: fitting a
dome over an element shifts the vertical offset and reshapes the variation, so the
model-plus-radome combination is calibrated and published as a distinct entry, and
a bare-element calibration is not valid for the same element under a dome.

The offset is also frequency-dependent, and not by a smooth law. A published table
carries a separate block per carrier, and the vertical offsets of two carriers on
one antenna commonly differ by several centimetres. Ionosphere-free combinations of
carriers therefore need the offsets of both, combined with the same coefficients as
the observations.

Across models the spread is larger still. Vertical offsets for common geodetic
antennas at the primary carrier span roughly a decimetre, and the shape of the
variation pattern differs as well as its scale, so substituting a similar antenna's
calibration leaves a systematic error of the same order as the effect being
corrected.

## The exchange format

Published calibrations are distributed in ANTEX, a fixed-column text format defined
by the International GNSS Service
(`https://files.igs.org/pub/data/format/antex14.txt`). One file carries many
antennas; each antenna runs from a `START OF ANTENNA` record to an `END OF ANTENNA`
record, with the record label in columns 61-80 of every line.

The antenna header names the type and, where present, the radome; states the
calibration method, the agency and the date; and declares the grid geometry. `DAZI`
is the azimuth step in degrees, and a value of zero means the antenna is published
without azimuth resolution. `ZEN1 / ZEN2 / DZEN` are the first zenith angle, the
last zenith angle and the step, again in degrees, so the columns of the variation
table run from the zenith outward toward the horizon.

Each frequency block opens with the three-character carrier code, gives the mean
offset as North, East and Up in millimetres on the `NORTH / EAST / UP` record, then
tabulates the variations. The `NOAZI` row holds the azimuth-averaged variation
across the zenith nodes. Where an azimuth grid is published, one row follows per
azimuth node, the azimuth in the first field and the variation at each zenith node
after it. Values are millimetres throughout.

Satellite transmitter antennas appear in the same file and in the same records, but
they are not interchangeable with receiver entries: their pattern is expressed in
the spacecraft body frame against the nadir angle, and the sign convention that
applies to them is the one for a transmitting rather than a receiving element.

## Applying the model

For a receiver antenna the correction along a line of sight is the mean offset
projected onto that line of sight, plus the variation interpolated at the azimuth
and zenith angle of the satellite. The projection uses the local North/East/Up unit
vector towards the satellite; the interpolation is taken bilinearly between the
bracketing azimuth rows and zenith columns, which is what the established
processing packages do with a gridded table.

Two conventions are worth stating explicitly, because getting either wrong produces
a plausible-looking number. The grid is indexed by zenith angle, not elevation, so
the elevation reported by a processing engine is converted before the lookup. And
the variation is added to the projected offset with the sign the table carries; it
is not a magnitude.

## Sources

- Rothacher, M., and Schmid, R., 2010, *ANTEX: The Antenna Exchange Format,
  Version 1.4*, 15 September 2010:
  `https://files.igs.org/pub/data/format/antex14.txt`
- International GNSS Service, IGS20 absolute antenna correction file:
  `https://files.igs.org/pub/station/general/igs20.atx`
- Schmid, R., Steigenberger, P., Gendt, G., Ge, M., and Rothacher, M., 2007,
  *Generation of a consistent absolute phase-center correction model for GPS
  receiver and satellite antennas*: Journal of Geodesy, v. 81, no. 12, p. 781-798,
  doi:10.1007/s00190-007-0148-y
- Schmid, R., Dach, R., Collilieux, X., Jäggi, A., Schmitz, M., and Dilssner, F.,
  2016, *Absolute IGS antenna phase center model igs08.atx: status and potential
  improvements*: Journal of Geodesy, v. 90, no. 4, p. 343-364,
  doi:10.1007/s00190-015-0876-3
- Görres, B., Campbell, J., Becker, M., and Siemes, M., 2006, *Absolute
  calibration of GPS antennas: laboratory results and comparison with field and
  robot techniques*: GPS Solutions, v. 10, no. 2, p. 136-145,
  doi:10.1007/s10291-005-0015-3

IGS products are made available to the public without charge or restriction under
the IGS data and product policy (`https://igs.org/data-products-overview/`), which
asks that the service be acknowledged.
