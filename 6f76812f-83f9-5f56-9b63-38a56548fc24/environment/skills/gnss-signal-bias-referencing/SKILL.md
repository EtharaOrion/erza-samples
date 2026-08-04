---
name: gnss-signal-bias-referencing
description: >-
  Resolve a published differential signal bias product onto whatever observable
  pair a receiver actually tracked, and combine the space-vehicle and receiver
  sides into the single quantity a geometry-free code observable must be cleared
  of. Use when a task supplies raw code pseudoranges on two frequencies and asks
  for an electron content, a hardware delay, or any quantity that depends on the
  geometry-free code combination being free of equipment delay. Do not use when
  the observables supplied are already bias-corrected, when only carrier phase is
  involved, when the wanted quantity is an ionosphere-free combination for orbit
  or clock work, or when the product in hand is an observable-specific
  (pseudo-absolute) bias set rather than a differential one.
---

# Referencing a differential signal bias onto the observables you actually have

A code pseudorange carries a hardware delay contributed by the transmitting
satellite and another by the receiving station. Both depend on the *signal*, not
just the frequency: a receiver tracking the C/A code on the first frequency sees a
different delay from one tracking the encrypted P(Y) code on that same frequency.
Analysis centres publish these as **differential signal biases** (DSBs), one value
per ordered pair of observables, per satellite and per station, per day.

The trap is not arithmetic. It is that the pair you need is very often not the
pair the product publishes, and the rules that get you from one to the other are
spread across a format description whose own "How to Use a SINEX BIAS File?"
section was never written - it ships as a placeholder paragraph. What follows is
that missing section.

## What a published row means

A row carrying observables `OBS1` and `OBS2` is the *difference* of the two
underlying signal biases, in the order printed:

> `BD(OBS1, OBS2) = B(OBS1) - B(OBS2)`

That is equation (7) of the Bias-SINEX 1.00 format description (S. Schaer, IGS
Bias and Calibration Working Group; `https://files.igs.org/pub/data/format/sinex_bias_100.pdf`,
section 6.3.1). Reversing the two observables reverses the sign of the value; the
ordered pair is part of the datum, not decoration.

Two further rules from the same document, both of which decide answers:

- **The sign.** Section 6.1 defines a bias as `observation - true observation`,
  hence `true observation = observation - bias`, equations (3a)-(3c), restated as
  equation (4) in section 6.2.1. A bias is an *error carried by the observation*,
  not a correction to be applied to it. It is therefore **subtracted** from the
  observable. The document settles this with a worked numerical example - ground
  truth 11, observed 7, bias -4 - and the sign is the single most common thing to
  get backwards, because "bias correction" reads like something you add.
- **The two sides.** Section 6.2.2, equation (5): `Btotal = Bsatellite + Breceiver`.
  The satellite entry and the station entry are separate rows in the product and
  they simply sum. Neither side alone is the total, and which side is larger
  varies: station values commonly run to tens of nanoseconds while satellite
  values sit within about ten.

## Reference observables

Each constellation has a pair of observables the product's datum is anchored on.
For GPS these are `C1W` and `C2W`, the legacy P(Y)-code observables, as the format
description states when it works its observable-specific example ("assuming GPS
C1W/C2W reference observables", Bias-SINEX 1.00 section 6.3.3,
`https://files.igs.org/pub/data/format/sinex_bias_100.pdf`). The reference pair matters because
it is the hub every other observable is published relative to: intra-frequency
rows such as `C1C`-`C1W` or `C2W`-`C2L` exist precisely to move a tracked signal
onto its frequency's reference observable.

## Resolving the pair you need

Given a product's rows for one satellite or one station, and the ordered pair
`(A, B)` the receiver actually reported, take the first of these that applies -
in this order, because the later rules are fallbacks, not alternatives:

1. **A row for exactly `(A, B)`.** Use its value as published. This takes
   precedence over anything you could assemble, and the precedence is not
   cosmetic: the rows in a real product are *independent estimates* from the same
   adjustment, not algebraically consistent identities. Chaining `C1C`->`C1W`->`C2W`
   and reading the published `C1C`-`C2W` row give answers that differ by a
   few tenths of a nanosecond, which is several TECU of electron content. The
   directly published row is the product's own answer for that pair; prefer it.
2. **A row for the reversed pair `(B, A)`.** Use its value negated.
3. **Neither is present.** The pair is genuinely absent from that day's solution -
   this is normal, since a station only gets rows for the signals it was seen to
   track - and the value falls back to a chain: the signed sum along the shortest
   path of published rows linking `A` to `B`, each step contributing `+value` when
   it is traversed in the printed order and `-value` when traversed against it.
   Where two chains are equally short, take the one whose intermediate observables
   are the constellation's reference observables.

Rule 3 is where sign errors breed. Summing the magnitudes of the rows on the path,
or assuming every row runs in the direction you happen to need, is wrong for any
chain that traverses a row backwards. Write the chain out as observables and carry
each step's sign explicitly.

Note that rules 1 and 3 are resolved **per side, independently**. It is entirely
normal for the satellite side of an arc to have a direct row while the station
side of the same arc has to be chained, because satellites are tracked by the
whole network and a single station is not.

## Putting it together

For one epoch of a geometry-free code observable formed as `range(A) - range(B)`:

```
b_total = resolve(satellite_rows, A, B) + resolve(station_rows, A, B)     [ns]
geometry_free_corrected = (range_A - range_B) - c * b_total * 1e-9        [m]
```

with `c` the speed of light. Only then convert to an electron content. The bias is
constant across a day's solution, so it is a single number per arc, not a
per-epoch quantity - which also means a wrong bias shows up as a clean offset in
the result, never as scatter.

## Reference tables

`references/dsb_sat_<label>.tsv` and `references/dsb_rec_<label>.tsv` carry the
published rows for each satellite and receiver label, in nanoseconds, copied
verbatim from the CAS/IGG multi-GNSS DCB product for the day in question
(Bias-SINEX 1.00; method described in Wang N., Yuan Y., Li Z., Montenbruck O.,
Tan B. (2016), *Journal of Geodesy* 90(3):209-228, DOI 10.1007/s00190-015-0867-4;
archived at `ftp://igs.gnsswhu.cn/pub/gps/products/mgex/dcb/`). Each file has one
row per ordered observable pair with its value and its published standard
deviation. The satellite and receiver files are separate because they are separate
sides of equation (5).

`references/method.md` carries the longer note: why the product's rows are not
algebraically consistent, how the zero-mean constellation condition fixes the
split between the two sides, and what the standard deviations do and do not tell
you.

## Checking an implementation

Three resolutions that exercise all three rules. None of them is an observable
pair a receiver in a typical single-frequency-pair task reports, so they check the
resolver rather than the answer:

| resolution wanted | rule | expected value, ns |
|---|---|---|
| `BD(C1C, C5Q)` for a station whose product row `C1C C5Q` reads `11.3850` | 1, direct | `11.3850` |
| `BD(C5X, C1C)` for a station whose product row `C1C C5X` reads `-9.7540` | 2, reversed | `9.7540` |
| `BD(C1C, C2X)` for a satellite with rows `C1C C2W` = `1.0550` and `C2W C2X` = `0.2340` and no `C1C`-`C2X` row | 3, chained via the reference observable | `1.2890` |

Two diagnostic mis-resolutions of that third row, for comparison:

| symptom | what it means |
|---|---|
| the chain resolves to `0.8210` ns | the rows are being summed by magnitude, without each row's own ordered-pair sign |
| the chain resolves to `1.0550` ns | the intra-frequency row is being skipped and the second observable treated as the reference one |

## Scope

This procedure is about *referencing*, not about estimating. It presumes a
published product for the day. Estimating biases from a single station's own
observations is a different job entirely, needs a spatial ionosphere model and a
datum constraint, and is not what this note covers.
