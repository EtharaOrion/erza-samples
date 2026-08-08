#!/bin/bash
set -e
# Reference solver: resolves each arc's differential signal bias against the
# published product tables, clears it from the geometry-free code observable,
# reduces to the vertical and averages each arc into /root/results.json.
# Path-independent: resolves solve.py next to this script, so the oracle runs
# both under the Erza-native layout (/oracle) and the Harbor layout (/solution).
exec python3 "$(dirname "$0")/solve.py" "$@"
