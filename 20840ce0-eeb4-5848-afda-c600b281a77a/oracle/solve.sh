#!/bin/bash
# Reference solution. Builds every payee detail record from the baked semantic
# data and the published field table, then writes /root/results.json.
set -euo pipefail
# Path-independent: resolves solve.py next to this script, so the oracle runs
# both under the Erza-native layout (/oracle) and the Harbor layout (/solution).
python3 "$(dirname "$0")/solve.py" "$@"
test -s /root/results.json
