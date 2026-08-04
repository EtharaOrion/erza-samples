#!/bin/bash
set -e
# Reference solver: rates every listed line of sight against that antenna's own
# calibration block and writes /root/results.json.
python3 /oracle/solve.py
