# Differential signal biases: where the numbers come from, and what they are not

## The measurement

A daily differential signal bias solution is a network product. An analysis centre
takes a few hundred stations' dual-frequency observations, models the ionospheric
electron content over the network, and solves simultaneously for the electron
content and for one constant hardware delay per satellite and per station per
signal pair. The delays and the ionosphere are estimated in the same adjustment
because they are entangled: at a single station over a single arc they are not
separable at all, which is why the values have to come from a product and cannot
be recovered from the record they are applied to.

The values used here are the CAS/IGG multi-GNSS product, generated daily from the
MGEX and iGMAS networks with the local-ionospheric-modelling technique described in

> Wang N., Yuan Y., Li Z., Montenbruck O., Tan B. (2016). Determination of
> differential code biases with multi-GNSS observations. *Journal of Geodesy*
> 90(3), 209-228. DOI 10.1007/s00190-015-0867-4

and distributed in Bias-SINEX form. The format itself is specified by

> Schaer S. SINEX_BIAS - Solution (Software/technique) INdependent EXchange
> Format for GNSS Biases, Version 1.00. IGS Bias and Calibration Working Group.
> `https://files.igs.org/pub/data/format/sinex_bias_100.pdf`

## The datum: a zero-mean constellation condition

Only the *sum* of a satellite bias and a station bias is observable on any one
link. The split between the two sides is therefore not determined by the data; it
is imposed. The convention every ionosphere-oriented product uses is a **zero-mean
constellation condition**: the satellite values of a constellation are constrained
to sum to zero over the day, and the station values absorb the remainder. The CAS
files state it in their own header comment - "A zero-mean constellation condition
is applied to separate satellite and receiver biases on a daily basis" - and the
CODE global ionosphere maps state the same thing as "The code bias datum is
defined by zero-mean conditions imposed on the satellite bias estimates."

Two consequences that matter in practice:

- **You must use both sides from the same product and the same day.** Mixing a
  satellite value from one agency with a station value from another, or from a
  different day, breaks the datum and leaves a residual of whatever the two
  agencies' zero-mean solutions differ by.
- **A station value is not a property of the receiver alone.** It carries the
  constellation's zero-mean offset too. This is why station values run large -
  tens of nanoseconds is ordinary - while satellite values stay within about ten.

## Why the rows are not algebraically consistent

A product may publish `C1C`-`C1W`, `C1W`-`C2W` and `C1C`-`C2W` for the same
satellite. Algebraically the first two should sum to the third. They do not, quite:
each is an independent estimate formed from a different subset of the observations,
with its own geometry, its own elevation distribution and its own noise. Residual
discrepancies of one to a few tenths of a nanosecond between a chained and a
directly published value are routine and are visible in any real file.

A tenth of a nanosecond is a few centimetres of range and a few tenths of a TECU
of slant electron content (the conversion follows from the carrier frequencies
in RINEX 3.05 section 5.1, `https://files.igs.org/pub/data/format/rinex305.pdf`), so
this is not a rounding curiosity - it is larger than the tolerance of most
calibrated-TEC work. Hence the ordering rule: when the product
publishes the exact ordered pair you need, that row is the answer, and a chain
built through other rows is only the fallback for a pair the product does not
carry. Chaining when you did not have to is a real, measurable error, not a
stylistic choice.

## The standard deviations

Every row carries a published standard deviation. It describes the formal
precision of that estimate within the daily adjustment - typically a few
thousandths to a few hundredths of a nanosecond for satellites, and a little
looser for stations. It is **not** a licence to round the value, and it is not the
accuracy of the bias in any absolute sense: absolute signal biases are
inaccessible, and only differences are ever determined. Use the published value at
the precision printed; use the standard deviation only for weighting or for
flagging a row that came out of a thin day of data.

## Signals and their codes

Observables are named with the RINEX 3 three-character convention: type, band,
tracking channel. The ones that recur in GPS bias products are

| code | band | signal |
|---|---|---|
| `C1C` | L1 | C/A code |
| `C1W` | L1 | P(Y) code, Z-tracking |
| `C2W` | L2 | P(Y) code, Z-tracking |
| `C2L` | L2 | L2C, L channel |
| `C2S` | L2 | L2C, M channel |
| `C2X` | L2 | L2C, M+L combined |
| `C5Q` | L5 | L5, Q channel |
| `C5X` | L5 | L5, I+Q combined |

The full table, and the carrier frequency of each band, is section 5.1 of the
RINEX 3.05 specification (`https://files.igs.org/pub/data/format/rinex305.pdf`).

Which of these a station reports is a property of its receiver and firmware, and
it is why two stations in the same network need different rows out of the same
product. A station tracking L2C rather than the legacy P(Y) code needs its L2
observable moved onto the reference observable before any inter-frequency row
applies; the intra-frequency row exists for exactly that step, and skipping it
leaves the whole L2C-to-P(Y) offset in the result.

## The single-layer reduction, for context

Slant content is reduced to vertical with a thin-shell approximation: all the
electrons are treated as lying on a spherical shell at a fixed height, the ray
pierces it at one point, and the obliquity factor is the cosine of the zenith
angle at that pierce point. The shell radius and height a product is published
on are carried in the header of every CODE IONEX file, in its `BASE RADIUS` and
`HGT1 / HGT2 / DHGT` records; a task that needs them will state which it wants.
Nothing in the bias handling depends on which shell is chosen, but a calibrated
result quoted without one is incomplete.
