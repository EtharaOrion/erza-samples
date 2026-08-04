#!/bin/bash
# Reference solution: local magnitude ML via Wood-Anderson simulation.
set -e
python3 << 'PY'
import json, warnings, numpy as np
warnings.filterwarnings("ignore")
from obspy import read, read_inventory, Stream
from pathlib import Path

D = Path("/root/data")
q = json.loads((D / "question.json").read_text())
st = read(str(D / "waveform.mseed"))
inv = read_inventory(str(D / "station.xml"))

# horizontal components
horiz = [tr for tr in st if tr.stats.channel[-1] in ("N", "E", "1", "2")]

# IASPEI standard Wood-Anderson: static magnification 2080, T0=0.8 s.
# TWO zeros at the origin. The WA responds to ground DISPLACEMENT through
#     H(s) = G * s^2 / (s^2 + 2*h*w0*s + w0^2)
# and Step 3 above has already converted the trace to displacement, so both factors
# of s must be supplied here. The one-zero form is the response to VELOCITY; applying
# it to a displacement trace is one factor of s short and understates the amplitude by
# |2*pi*f| at the dominant frequency (~6.26x, or 0.80 ML, on this record).
# Check it: driving this paz with a 1 mm displacement sinusoid must deflect 2080 mm.
paz_wa = {"sensitivity": 2080.0, "zeros": [0j, 0j], "gain": 1.0,
          "poles": [-6.2832 - 4.7124j, -6.2832 + 4.7124j]}

S = Stream(horiz).copy()
S.detrend("linear"); S.taper(0.05)
S.remove_response(inventory=inv, output="DISP", pre_filt=(0.005, 0.01, 20, 25), water_level=60)
S.simulate(paz_simulate=paz_wa)                     # Wood-Anderson displacement (m)

amps_mm = [float(np.max(np.abs(tr.data))) * 1000.0 for tr in S]   # zero-to-peak, mm
A = max(amps_mm)                                    # SoCal ML: max horizontal

epi = float(q["epicentral_distance_km"]); depth = float(q.get("event_depth_km", 0.0))
r = np.sqrt(epi**2 + depth**2)                      # hypocentral distance km
# Hutton & Boore (1987) Southern California -logA0
logA0 = 1.110 * np.log10(r / 100.0) + 0.00189 * (r - 100.0) + 3.0
ML = float(np.log10(A) + logA0)

Path("/root/results.json").write_text(json.dumps({"local_magnitude_ml": round(ML, 3)}, indent=2))
print("ML =", round(ML, 3))
PY
