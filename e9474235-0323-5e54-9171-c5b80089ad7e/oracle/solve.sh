#!/bin/bash
set -e
# Reference solver: derives every station/time tide height and writes /root/results.json.
# Path-independent: resolves solve.py next to this script, so the oracle runs
# both under the Erza-native layout (/oracle) and the Harbor layout (/solution).
exec python3 "$(dirname "$0")/solve.py" "$@"
