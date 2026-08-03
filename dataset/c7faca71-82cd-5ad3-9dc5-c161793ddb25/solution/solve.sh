#!/bin/bash
# Reference solution. Derives every graded figure from the shipped roster and the
# published limits, then writes /root/results.json.
set -euo pipefail
python3 /solution/solve.py
test -s /root/results.json
