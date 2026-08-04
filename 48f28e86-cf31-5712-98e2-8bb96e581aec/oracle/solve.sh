#!/bin/bash
set -e
# Reference solver: derives each true azimuth and writes /root/results.json.
python3 /oracle/solve.py
