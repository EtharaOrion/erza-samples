#!/bin/bash
set -e
# Reference solver: derives every station/time tide height and writes /root/results.json.
python3 /oracle/solve.py
