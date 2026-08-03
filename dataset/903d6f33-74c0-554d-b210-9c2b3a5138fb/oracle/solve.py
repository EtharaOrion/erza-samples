"""Oracle: derives every source's ICRS position from the shipped FITS header and
source catalogue via the pinned standard FITS WCS (TAN) pipeline. Derivation
only - no hardcoded answers. The verifier recomputes with the same module at
grade time."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wcs_pipeline import solve_all  # noqa: E402

results = {"sources": solve_all("/root/data")}
with open("/root/results.json", "w") as f:
    json.dump(results, f, indent=1)
print(json.dumps(results, indent=1))
