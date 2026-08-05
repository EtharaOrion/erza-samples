#!/bin/bash
# Reference solution. Converts each ledger line with its reporting period's own
# factor edition, then writes /root/results.json.
set -euo pipefail
python3 "$(dirname "$0")/solve.py"
test -s /root/results.json
