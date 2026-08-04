#!/bin/bash
# Reference solution. Evaluates the published assignment models for every record
# in /root/data/response_records.csv and writes /root/results.json.
set -euo pipefail
python3 /solution/solve.py
test -s /root/results.json
