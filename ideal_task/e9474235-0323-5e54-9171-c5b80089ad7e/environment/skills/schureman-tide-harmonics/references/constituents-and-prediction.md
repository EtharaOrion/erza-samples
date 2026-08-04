# Harmonic tide prediction - file formats, method, check values

Companion to `SKILL.md`. Everything here is class-level: it applies to any tide
station and any UTC instant. No value here is the answer to any particular task.

## Data files

`harmonic_constants.json` - keyed by `station_id`:

```
"TG-A": {
  "label": "TG-A",
  "msl_minus_mllw_m": Z0,          # Z0: mean sea level above the chart datum (m)
  "datum": "MLLW",
  "constituents": [ {"name":"M2","amplitude_m":1.572,"phase_gmt_deg":91.9}, ... ]
}
```

`amplitude_m` is `H` (metres); `phase_gmt_deg` is `g`, the **Greenwich** phase lag
(degrees). These are the station's published harmonic constants (NOAA CO-OPS
harmonic-constant tables; Schureman 1958). They are empirical and specific to the
station.

`tidal_constituents.json` - keyed by constituent name:

```
"M2": {"doodson":[2,0,0,0,0,0], "semi":0.0, "speed_deg_per_hr":28.984104, "node_factor":"M2"}
```

`doodson` are the six integer multipliers of `[tau, s, h, p, N', pp]`; `semi` is a
constant phase term in cycles; `node_factor` selects the stage-3 group. (Doodson
1921; Schureman 1958; Foreman 1977.)

## Astronomical arguments (Schureman 1958; Meeus 1998)

With `d` = days since 1899-12-31 12:00:00 UT and `D = d/10000`, the mean longitudes
(degrees, then reduce mod 360 and divide by 360 to get cycles):

| symbol | polynomial in d (deg) |
|---|---|
| s (Moon) | 270.434164 + 13.1763965268 d - 8.50e-5 D^2 + 3.9e-8 D^3 |
| h (Sun) | 279.696678 + 0.9856473354 d + 2.267e-5 D^2 |
| p (lunar perigee) | 334.329556 + 0.1114040803 d - 7.739e-4 D^2 - 2.6e-7 D^3 |
| N' (node term) | -259.183275 + 0.0529539222 d - 1.557e-4 D^2 - 5.0e-8 D^3 |
| pp (solar perigee) | 281.220844 + 4.70684e-5 d + 3.39e-5 D^2 + 7.0e-8 D^3 |

Mean lunar time (cycles): `tau = frac(UT_day) + h/360 - s/360`, with `frac(UT_day)`
the UT hours/24. Equilibrium argument (cycles): `V = doodson . [tau,s/360,h/360,
p/360,N'/360,pp/360] + semi`.

## Node factor f and angle u

Ascending-node longitude (deg), Meeus (1998): `N = 125.04452 - 1934.136261 T + 0.0020708 T^2`,
`T` = Julian centuries from J2000.0 (Meeus 1998). The group formulae are in
`SKILL.md` (Schureman 1958, Table 14; Foreman 1977). Node factors vary slowly over
the 18.6-year nodal cycle; in years when `N` is near 0 the diurnal factors are near
their maxima.

## Prediction

```
height = Z0 + sum_i  f_i * H_i * cos( 2*pi*V_i + radians(u_i) - radians(g_i) )
```

## Worked check values (example instants, not any task's requested times)

At `2025-01-01T00:00:00Z`:

| station | height above MLLW (m) |
|---|---|
| TG-A gauge TG-A | 0.61 |
| TG-B gauge TG-B | 0.60 |
| TG-C gauge TG-C | 2.32 |

Reproducing these to a centimetre confirms the mean-longitude epoch, the Greenwich
phase convention, and the nodal terms are all correct before predicting the task's
own times.
