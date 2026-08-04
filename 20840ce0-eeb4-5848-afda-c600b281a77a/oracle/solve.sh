#!/bin/bash
# Reference solution. Builds every payee detail record from the baked semantic
# data and the published field table, then writes /root/results.json.
set -euo pipefail
python3 /solution/solve.py
test -s /root/results.json
