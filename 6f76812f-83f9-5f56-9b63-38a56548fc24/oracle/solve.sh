#!/bin/bash
set -e
# Reference solver: resolves each arc's differential signal bias against the
# published product tables, clears it from the geometry-free code observable,
# reduces to the vertical and averages each arc into /root/results.json.
python3 /oracle/solve.py
