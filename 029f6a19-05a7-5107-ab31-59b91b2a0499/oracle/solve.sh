#!/bin/bash
# Reference solution. Evaluates the published assignment models for every record
# in /root/data/response_records.csv and writes /root/results.json.
set -euo pipefail
# Path-independent: resolves solve.py next to this script, so the oracle runs
# both under the Erza-native layout (/oracle) and the Harbor layout (/solution).
python3 "$(dirname "$0")/solve.py" "$@"
test -s /root/results.json
