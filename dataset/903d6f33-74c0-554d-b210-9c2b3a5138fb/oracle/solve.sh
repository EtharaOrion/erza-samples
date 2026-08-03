#!/bin/bash
# Path-independent: resolves solve.py next to this script, so the oracle runs
# both under the Erza-native layout (/oracle) and the Harbor layout (/solution).
set -e
exec python3 "$(dirname "$0")/solve.py" "$@"
