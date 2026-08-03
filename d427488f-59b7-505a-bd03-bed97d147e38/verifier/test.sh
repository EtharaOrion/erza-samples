#!/bin/bash
mkdir -p /logs/verifier
python3 - <<'PY' || true
import json, os
if os.path.exists('/root/results.json') and os.path.exists('/verifier/expected_values.json'):
    g=json.load(open('/verifier/expected_values.json')); r=json.load(open('/root/results.json'))
    try:
        gs=float(r.get('robust_scale')); gz=float(r.get('zeta_prime'))
        rs=float(g['ref_robust_scale']); rz=float(g['ref_zeta_prime'])
        ts=float(g['tolerance_robust_scale_abs']); tz=float(g['tolerance_zeta_prime_abs'])
        print(f"SCALE_RAW: got={gs:.6f} ref={rs:.6f} err={abs(gs-rs):.6f} tol={ts} -> {'OK' if abs(gs-rs)<=ts else 'FAIL'}")
        print(f"ZETA_RAW:  got={gz:.6f} ref={rz:.6f} err={abs(gz-rz):.6f} tol={tz} -> {'OK' if abs(gz-rz)<=tz else 'FAIL'}")
    except Exception as e:
        print("RAW: unreadable", e)
PY
pytest --ctrf /logs/verifier/ctrf.json /verifier/test_outputs.py -rA -v
rc=$?
if [ $rc -eq 0 ]; then echo 1 > /logs/verifier/reward.txt; else echo 0 > /logs/verifier/reward.txt; fi
exit 0
