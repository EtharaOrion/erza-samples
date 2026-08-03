---
name: local-magnitude-seismology
description: Compute the local (Richter) magnitude ML of an earthquake from a broadband seismogram using obspy — reading miniSEED + StationXML, removing the instrument response, simulating a Wood-Anderson seismograph, measuring the peak horizontal amplitude in millimetres, and applying the region's distance correction (-logA0). Use when a task gives raw seismic counts + station response and asks for local magnitude / ML / Richter magnitude. Not for moment magnitude Mw (that needs a spectral/moment-tensor method), body/surface-wave magnitudes, or phase picking.
license: MIT
---

# Local magnitude (ML) from a broadband seismogram

ML is defined as the amplitude a **Wood-Anderson (WA) torsion seismograph** would
record, in millimetres, corrected for distance. You must reproduce that instrument
synthetically — you cannot read a magnitude off the raw counts, and the catalogue
magnitude is often **Mw (moment magnitude)**, a *different* quantity you must not
report.

## Pipeline (every step matters)

### 1. Load and select horizontals
```python
from obspy import read, read_inventory, Stream
st = read("waveform.mseed"); inv = read_inventory("station.xml")
horiz = [tr for tr in st if tr.stats.channel[-1] in ("N", "E", "1", "2")]
```
ML uses **horizontal** components (the classic WA is horizontal).

### 2. Remove the instrument response — correctly
```python
S = Stream(horiz).copy(); S.detrend("linear"); S.taper(0.05)   # 5% cosine taper
S.remove_response(inventory=inv, output="DISP",
                  pre_filt=(0.005, 0.01, 20, 25), water_level=60)
```
- **`pre_filt`** (a cosine taper in the frequency domain) and **`water_level`** are
  mandatory — without them the deconvolution blows up at low frequency and the
  amplitude is meaningless. This is the single most common failure.
- `output="DISP"` → ground **displacement in metres** (WA responds to displacement).
- The taper fraction (`0.05`) and the `pre_filt` corners (`0.005`/`0.01` Hz at the low
  end, `20`/`25` Hz at the high end) are *stabilisation* choices, not standardised
  constants: they bracket the station's passband well outside the signal band. Sweeping
  the water level over 30–90 dB and widening the pre-filter moves ML by <0.05 here, so
  they are not a lever — but they must be present.

### 3. Simulate the Wood-Anderson seismograph (IASPEI standard)
```python
paz_wa = {"sensitivity": 2080.0, "zeros": [0j, 0j], "gain": 1.0,
          "poles": [-6.2832 - 4.7124j, -6.2832 + 4.7124j]}   # T0=0.8 s
S.simulate(paz_simulate=paz_wa)          # now S is WA displacement (m)
```
- Use the **IASPEI (2011) static magnification 2080**, *not* the historical 2800.
- The WA free period is **0.8 s**. The poles above encode **h = 0.8**
  (h = −Re(pole)/ω₀ = 6.2832/7.8540); the value 0.7 is also widely quoted. The two
  readings differ by 0.023 ML, far inside tolerance — this is *not* the thing to get
  right.

> **The thing to get right: TWO zeros at the origin.**
> A Wood-Anderson responds to ground **displacement** through
> `H(s) = G·s²/(s² + 2hω₀s + ω₀²)` — numerator `s²`, so **two** zeros.
> Step 2 already converted the trace to displacement, so both factors of `s` must be
> supplied here. The **one-zero** form `zeros=[0j]` is the response to **velocity**
> (velocity has already absorbed one factor of `s`), and it is what most copied obspy
> snippets contain. Applying it to a displacement trace is one factor of `s` short: the
> amplitude comes out low by `|2πf|` at the dominant frequency — a factor of ~6.3, or
> **0.80 ML**, near 1 Hz. That is more than twice the graded tolerance.
>
> **Verify it yourself, in three lines.** A WA is *defined* by its static
> magnification: 1 mm of ground displacement must deflect the trace 2080 mm.
> ```python
> t = np.arange(0, 60, 0.01)
> tr = Trace(data=0.001*np.sin(2*np.pi*5.0*t)); tr.stats.sampling_rate = 100.0
> tr.simulate(paz_simulate=paz_wa)
> print(np.max(np.abs(tr.data[1000:-1000]))*1000)   # must be ~2080
> ```
> `zeros=[0j, 0j]` → **2034** ✅  ·  `zeros=[0j]` → **65** ❌
> Run this check whenever you write a WA paz. It costs nothing and it catches the one
> error that dominates every other on this pipeline.

### 4. Peak amplitude in millimetres
```python
import numpy as np
amps_mm = [float(np.max(np.abs(tr.data))) * 1000.0 for tr in S]   # zero-to-peak, mm
A = max(amps_mm)                                                  # max horizontal
```
Convert metres → **millimetres** (×1000). Use the **maximum** of the two horizontals
(SoCal convention), zero-to-peak.

### 5. Distance correction and ML
```python
r = np.sqrt(epi_km**2 + depth_km**2)     # HYPOcentral distance
# Hutton & Boore (1987), Southern California:
logA0 = 1.110*np.log10(r/100.0) + 0.00189*(r - 100.0) + 3.0
ML = np.log10(A) + logA0
```
- Use **hypocentral** distance (include depth), not just epicentral.
- The `-logA0` term is **region-specific**; for Southern California use Hutton &
  Boore (1987) with coefficients `1.110`, `0.00189`, `+3.0`. A generic textbook
  `ML = log10(A) + 3` (the 100-km reference only) is wrong at other distances.

## Sanity checks
- **Calibrate the WA paz before you trust it** (§3): 1 mm displacement in → ~2080 mm
  out. This is the single highest-yield check on the whole pipeline.
- ML for a felt regional earthquake is typically **3–6**. Agreement with a catalogue
  Mw is *not* a check — ML and Mw are different quantities that happen to track each
  other over parts of the range and diverge elsewhere.
- If |ML| is implausible (negative, or >8), suspect a missing response removal,
  the `×1000` mm conversion, or the WA simulation.

## When NOT to use this skill
- **Moment magnitude Mw** — needs a spectral fit or moment-tensor inversion; none of
  this applies.
- **mb / Ms / Mc** (body-wave, surface-wave, coda-duration) — different amplitude
  measures and different distance corrections.
- **Outside Southern California** — the `-logA0` coefficients in §5 are regional.
  Using Hutton & Boore where a local calibration exists is a method error.
- **Teleseismic distances** (beyond a few hundred km) — ML is a *local* scale and
  saturates; the WA simulation is not the right instrument.

## Sources
- Hutton, L. K. & Boore, D. M. (1987), *The ML scale in Southern California*,
  BSSA 77(6), 2074–2094 — the `1.110` / `0.00189` / `+3.0` coefficients.
- IASPEI (2011/2013), *Standard procedure for magnitude determination*, WG on
  Magnitude Measurements — static magnification **2080**, T₀ = 0.8 s, and the
  displacement response `G·s²/(s² + 2hω₀s + ω₀²)`.
- Uhrhammer, R. A. & Collins, E. R. (1990), BSSA 80(3), 702–716 — the re-determination
  that replaced the historical 2800 magnification with 2080.
