---
name: schureman-tide-harmonics
description: Predict the tide height at a coastal station and instant by harmonic synthesis, by hand. Read the station's published harmonic constants (per-constituent amplitude and Greenwich phase lag) from references/harmonic_constants.json and the constituent definitions (Doodson numbers, phase, node-factor group) from references/tidal_constituents.json; evaluate each constituent's equilibrium argument and 18.6-year (Schureman 1958) nodal correction at the requested UTC time; and sum height = Z0 + sum f*H*cos(2*pi*V + u - g). Use when a task gives a tide or water-level station (by id or name) and one or more times and needs the predicted height above a datum, especially with no tide library and no network. Not for storm surge or meteorological residuals, not for tidal currents, and not when a task supplies its own tide model to use instead.
license: MIT
---

# Harmonic tide prediction, by hand

The tide height at a place is the sum of a fixed set of sinusoids - the tidal
**constituents** (M2, S2, K1, O1, ...). Each constituent has a fixed **speed**
(angular frequency) that comes from astronomy, and a **local amplitude H** and
**Greenwich phase lag g** that are *specific to the station* and must be measured
there. Given those constants, the predicted height above the station datum at UTC
instant *t* is

```
height(t) = Z0 + sum_i  f_i * H_i * cos( 2*pi*V_i(t) + u_i(t) - g_i )
```

- `H_i`, `g_i` - the station's amplitude (m) and Greenwich phase lag (deg) for
  constituent *i* (from `references/harmonic_constants.json`).
- `V_i(t)` - the constituent's **equilibrium argument** at *t* (cycles), built from
  the astronomical mean longitudes and the constituent's Doodson numbers.
- `f_i`, `u_i` - the **nodal factor** and **nodal angle**: a slow (18.6-year (Schureman 1958))
  modulation of amplitude and phase from the regression of the Moon's node.
- `Z0` - the datum offset (mean sea level above the chart datum), `msl_minus_mllw_m`.

The whole difficulty is that `H_i` and `g_i` are **not obtainable to the needed precision without local measurement** to
the precision a prediction needs, and they are **not** the single recent water level
a task may quote for orientation: they are empirical, per-station, and published as a
harmonic-constant table. This skill ships that table and the method; together they
give the height at any instant.

Budget your effort accordingly: reading the constants and summing the cosines is
bookkeeping. The two places hand-rolled predictions go wrong are the **equilibrium
argument / time origin** (stage 2) and the **nodal corrections** (stage 3). Get
either wrong and every instant drifts while the numbers still look plausible.

## The chain, in order

```
(station, t_UTC)
   -> Z0, {H_i, g_i}         from harmonic_constants.json  (stage 0)
   -> [tau,s,h,p,N',pp](t)   astronomical mean longitudes    (stage 1)
   -> V_i = doodson_i . astro + semi_i                        (stage 2)
   -> f_i, u_i from the node longitude N                      (stage 3)
   -> height = Z0 + sum f_i H_i cos(2*pi*V_i + u_i - g_i)     (stage 4)
```

Everything is closed-form; there is no fitting and no iteration. If your design has
a solver loop, you have mis-modelled the problem.

### Stage 0 - the station constants

`references/harmonic_constants.json` is keyed by `station_id`. Each station carries
`msl_minus_mllw_m` (that is `Z0`, the mean-sea-level height above the chart datum)
and a `constituents` list of `{name, amplitude_m, phase_gmt_deg}`. `phase_gmt_deg`
is the **Greenwich** phase lag (referenced to Greenwich, not local time). Match each
constituent by `name` to its definition in
`references/tidal_constituents.json`, which gives `doodson` (6 integers), `semi`
(a phase constant, in cycles), `speed_deg_per_hr`, and `node_factor` (the group
label used in stage 3).

### Stage 1 - astronomical mean longitudes

Compute, at the target UTC instant, the mean longitudes (all reduced to cycles,
i.e. divided by 360 and taken mod 1). With `d` = days since 1899-12-31 12:00 UT and
`D = d/10000` (Schureman 1958, SP-98; polynomials also in Meeus 1998):

Mean-longitude polynomials, Schureman (1958) C&GS Special Pub. 98; Meeus (1998):
```
s   = 270.434164 + 13.1763965268*d - 8.50e-5*D^2 + 3.9e-8*D^3      # Moon mean longitude
h   = 279.696678 +  0.9856473354*d + 2.267e-5*D^2                  # Sun mean longitude
p   = 334.329556 +  0.1114040803*d - 7.739e-4*D^2 - 2.6e-7*D^3     # lunar perigee
N'  = -259.183275 + 0.0529539222*d - 1.557e-4*D^2 - 5.0e-8*D^3     # (negative) lunar node term
pp  = 281.220844 +  4.70684e-5*d   + 3.39e-5*D^2 + 7.0e-8*D^3      # solar perigee
# Mean-longitude polynomials: Schureman (1958), C&GS Special Pub. 98; Meeus (1998).
```

Then the mean **lunar time** in cycles is `tau = frac(UT_day) + h/360 - s/360`,
where `frac(UT_day)` is the fraction of the UT day (hours/24). Assemble the vector
`astro = [tau, s/360, h/360, p/360, N'/360, pp/360]` (each mod 1).

### Stage 2 - equilibrium argument

For each constituent, `V = doodson . astro + semi` (cycles), i.e.
`V = d1*tau + d2*(s/360) + d3*(h/360) + d4*(p/360) + d5*(N'/360) + d6*(pp/360) + semi`.
`2*pi*V` is the argument in radians. (Doodson 1921; Schureman 1958.)

### Stage 3 - nodal factor f and angle u

`f` and `u` (deg) depend only on the ascending-node longitude `N`, computed
independently as `N = 125.04452 - 1934.136261*T + 0.0020708*T^2` (deg, mod 360),  (Meeus (1998))
with `T` the Julian centuries from J2000.0 (Meeus 1998). Dispatch on the
constituent's `node_factor` group. The base groups (Schureman 1958, Table 14;
Foreman 1977):

| group | f | u (deg) |
|---|---|---|
| `M2` | 1.0004 - 0.0373 cosN + 0.0002 cos2N | -2.14 sinN |
| `K1` | 1.0060 + 0.1150 cosN - 0.0088 cos2N + 0.0006 cos3N | -8.86 sinN + 0.68 sin2N - 0.07 sin3N |
| `O1` | 1.0089 + 0.1871 cosN - 0.0147 cos2N + 0.0014 cos3N | 10.80 sinN - 1.34 sin2N + 0.19 sin3N |
| `K2` | 1.0241 + 0.2863 cosN + 0.0083 cos2N - 0.0015 cos3N | -17.74 sinN + 0.68 sin2N - 0.04 sin3N |
| `J1` | 1.1029 + 0.1676 cosN - 0.0170 cos2N + 0.0016 cos3N | -12.94 sinN + 1.34 sin2N - 0.19 sin3N |
| `OO1` | 1.1027 + 0.6504 cosN + 0.0317 cos2N - 0.0014 cos3N | -36.68 sinN + 4.02 sin2N - 0.57 sin3N |
| `MF` | 1.0429 + 0.4135 cosN - 0.0040 cos2N | -23.74 sinN + 2.68 sin2N - 0.38 sin3N |
| `MM` | 1.0000 - 0.1300 cosN + 0.0013 cos2N | 0 |
| `SOL` | 1 | 0 |

The compound (shallow-water) groups combine the base ones: `M2^2` = (f_M2^2,
2 u_M2); `M2^3` = (f_M2^3, 3 u_M2); `M2^4` = (f_M2^4, 4 u_M2); `MS4` = (f_M2,
u_M2); `MK3` = (f_M2 f_K1, u_M2 + u_K1); `2MK3` = (f_M2^2 f_K1, 2 u_M2 - u_K1);
`M3` = (f_M2^1.5, 1.5 u_M2) (Schureman (1958), Foreman (1977)). Any group not listed takes `f = 1, u = 0`.

### Stage 4 - sum and emit

`height = Z0 + sum_i f_i * H_i * cos(2*pi*V_i + radians(u_i) - radians(g_i))`, in
metres above the station datum. Keep full double precision through to output; do not
round `H`, `g`, or the height prematurely, and spell every station id and every
timestamp exactly as the task gives them.

### Working conditions

With no tide library and no network, write the synthesis by hand - it is a few dozen
lines needing only a standard math library and the shipped tables. Do not spend the
budget on `pip`. Leave the delivered inputs unmodified.

## The traps, ranked by how often they bite

| Trap | What it looks like | Cost |
|---|---|---|
| **Reporting the orientation value** | echo the single recent observation, or the mean level, at every time | wrong at every instant by much of the tidal range |
| **Wrong time origin / equilibrium arg** | mismatched epoch, local vs Greenwich phase, degrees vs cycles | a large, roughly uniform phase error |
| **Dropping minor constituents** | keep only M2,S2,K1,O1 | tens of centimetres at some instants |
| **Omitting nodal corrections** | `f=1, u=0` for the lunar constituents | up to ~0.09 m, largest near a nodal extreme |
| **Rounding H or g** | truncating the constants before summing | small but avoidable drift |

## Verify with something that can actually disagree

- **Reproduce the orientation reading.** Each station's `decoy_reference` recent
  observation is a real predicted height at `recent_observation_time_utc`. Run your
  method at that timestamp and confirm you reproduce that value to a centimetre - a
  quick, independent check that your constants, argument and nodal terms line up.
- **Worked check value.** At gauge `TG-A`, `2025-01-01T00:00:00Z`, the
  method gives about **0.61 m** above MLLW; at gauge `TG-C` the same
  instant gives about **2.32 m**. (These are example instants (oracle synthesis, Schureman (1958)), not the task's
  requested times.)
- **Sanity.** Predicted heights must sit within roughly the station's tidal range
  about `Z0`; a value far outside the range is a phase or unit error, not the tide.

## References

- Schureman, P. (1958). *Manual of Harmonic Analysis and Prediction of Tides.*
  U.S. Coast and Geodetic Survey, Special Publication No. 98. (Method, mean-longitude
  polynomials, and the node-factor table.)
- Doodson, A. T. (1921). "The harmonic development of the tide-generating
  potential." *Proc. R. Soc. Lond. A* 100:305-329. (Doodson numbers.)
- Foreman, M. G. G. (1977). *Manual for Tidal Heights Analysis and Prediction.*
  Pacific Marine Science Report 77-10. (Node-factor formulae.)
- NOAA CO-OPS, *Tidal Analysis and Prediction* and the published station harmonic
  constants (https://tidesandcurrents.noaa.gov/harcon.html). Source of the shipped
  `harmonic_constants.json`.
- `references/constituents-and-prediction.md` - the file formats, the full method,
  and additional worked check values.
