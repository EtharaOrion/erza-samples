"""Synthetic run dirs: one that SHOULD trip each deterministic test, plus the
correct run on which none of them may.

Two consumers, one source of fixtures:

    python3 verification/make_fixtures.py > /tmp/fixmap.json   # writes /tmp/fixtures/*
    python3 verification/run_fixtures.py                       # subprocess table

    python3 -m pytest verification/negative_fixtures_test.py   # collected matrix

The module is IMPORTABLE: `GOOD`, `CORRECT`, `CASES` and `record()` are the
machinery, and nothing happens on import. It used to build /tmp/fixtures at import
time and print to stdout, so the only way to reuse a fixture was to shell out to
pytest once per fixture - which is why the fixture matrix lived in a script that
the test runner never ran, and why a regression in any detector could go unnoticed
until someone remembered to run it by hand.

`GOOD` is the SKELETON the negative cases mutate: it carries the shape of a
correct chain and deliberately does NOT name the pole-longitude convention, which
is what makes `no_lonpole_name` a fixture rather than a copy of `GOOD`. It is not
a correct run and must never be used as one. `CORRECT` is the correct run,
condensed from `truth_armed/golden_run`.
"""
import json
import os
import shutil

BASE = "/tmp/fixtures"

GOOD = """import math, csv, json
hdr = {}
for line in open('/root/data/image.hdr'):
    pass
phi_p = 180.0
for row in csv.DictReader(open('/root/data/sources.csv')):
    px = float(row['x']); py = float(row['y'])
    dx = px - CRPIX1; dy = py - CRPIX2
    x = CD11*dx + CD12*dy; y = CD21*dx + CD22*dy
    R = math.hypot(x, y)
    phi = math.degrees(math.atan2(x, -y))
    theta = math.degrees(math.atan2(180.0/math.pi, R))
    dphi = phi - phi_p
    ra = (a0 + math.atan2(-1, 1)) % 360.0
    dec = math.asin(0.5)
    out[row['source_id']] = {"ra_deg": ra, "dec_deg": dec}
json.dump({"sources": out}, open('/root/results.json','w'))
"""

# --------------------------------------------------------------------------- #
# The correct run, condensed from truth_armed/golden_run.
#
# The golden authored a `wcs_pipeline` module and a driver that imports it, and
# ran the driver. Kept here function for function - header parse, CD matrix,
# inverse TAN, native->celestial rotation with phi_p taken from LONPOLE with the
# standard's default, RA wrapped - minus the generator-only inverses and the
# build-time bug knob, which no criterion reads.
#
# Two properties of this source are load-bearing and easy to lose in an edit:
#   * it NAMES the convention (`LONPOLE`), which is what `R7` asks
#     and what `GOOD` above deliberately omits;
#   * its only `- 1` sits nowhere near a CRPIX subtraction, so the rebase
#     guardrail stays quiet.
# The graded `code` view blanks comments and docstrings, so every token a
# criterion reads is real code here, and every planted defect removes real code.
# --------------------------------------------------------------------------- #
CORRECT_PIPELINE = """import csv
import math
import os

DEG = math.pi / 180.0


def read_header(path):
    hdr = {}
    for line in open(path):
        s = line.strip()
        if not s or s == 'END' or '=' not in s:
            continue
        key, rest = s.split('=', 1)
        key = key.strip()
        rest = rest.strip()
        if rest.startswith("'"):
            hdr[key] = rest[1:rest.index("'", 1)].strip()
            continue
        rest = rest.split('/')[0].strip()
        try:
            hdr[key] = float(rest)
        except ValueError:
            hdr[key] = rest
    return hdr


def read_sources(path):
    src = {}
    for row in csv.DictReader(open(path)):
        src[row['source_id'].strip()] = (float(row['x']), float(row['y']))
    return src


def pixel_to_intermediate(px, py, hdr):
    dx = px - hdr['CRPIX1']
    dy = py - hdr['CRPIX2']
    x = hdr['CD1_1'] * dx + hdr['CD1_2'] * dy
    y = hdr['CD2_1'] * dx + hdr['CD2_2'] * dy
    return x, y


def intermediate_to_native(x, y):
    r = math.hypot(x, y)
    phi = math.degrees(math.atan2(x, -y))
    theta = math.degrees(math.atan2(180.0 / math.pi, r))
    return phi, theta


def native_to_celestial(phi, theta, hdr):
    phi_p = float(hdr.get('LONPOLE', 180.0))
    ap, dp = hdr['CRVAL1'] * DEG, hdr['CRVAL2'] * DEG
    dphi = (phi - phi_p) * DEG
    th = theta * DEG
    sin_th, cos_th = math.sin(th), math.cos(th)
    sin_dp, cos_dp = math.sin(dp), math.cos(dp)
    cos_dphi = math.cos(dphi)
    sin_dec = min(1.0, max(-1.0, sin_th * sin_dp + cos_th * cos_dp * cos_dphi))
    dec = math.degrees(math.asin(sin_dec))
    num = -cos_th * math.sin(dphi)
    den = sin_th * cos_dp - cos_th * sin_dp * cos_dphi
    ra = math.degrees(ap + math.atan2(num, den)) % 360.0
    return ra, dec


def solve_all(data_dir):
    hdr = read_header(os.path.join(data_dir, 'image.hdr'))
    src = read_sources(os.path.join(data_dir, 'sources.csv'))
    out = {}
    for sid in sorted(src):
        px, py = src[sid]
        x, y = pixel_to_intermediate(px, py, hdr)
        phi, theta = intermediate_to_native(x, y)
        ra, dec = native_to_celestial(phi, theta, hdr)
        out[sid] = {'ra_deg': ra, 'dec_deg': dec}
    return out
"""

CORRECT_DRIVER = """import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wcs_pipeline import solve_all

results = {'sources': solve_all('/root/data')}
json.dump(results, open('/root/results.json', 'w'), indent=1)
print(json.dumps(results, indent=1))
"""

# (path, content) in the order the golden wrote them
CORRECT = (("/root/wcs_pipeline.py", CORRECT_PIPELINE),
           ("/root/solve.py", CORRECT_DRIVER))
CORRECT_COMMANDS = ["ls -la /root/data",
                    "cat /root/data/image.hdr",
                    "cat /root/data/sources.csv",
                    "python3 /root/solve.py",
                    "cat /root/results.json"]
CORRECT_PROSE = ("LONPOLE is absent from the header, so for this zenithal "
                 "projection the FITS standard's default applies and phi_p is "
                 "180 degrees; the rotation carries phi - phi_p.")

CASES = {
    # name: (code, commands, expected-failing-test)
    "no_write":        ("",   ["python3 -c 'print(1)'"],        "R4"),
    "no_exec":         (GOOD, ["ls /root/data"],                 "R5"),
    "rounded_output":  (GOOD.replace('"ra_deg": ra', '"ra_deg": round(ra, 3)'),
                        ["python3 solve.py"],                    "R11"),
    "no_ids":          (GOOD.replace("csv.DictReader(open('/root/data/sources.csv'))", "[]")
                            .replace("row['source_id']", "'X'"),
                        ["python3 solve.py"],                    "R12"),
    "zero_based":      (GOOD.replace("dx = px - CRPIX1", "dx = (px - 1) - CRPIX1"),
                        ["python3 solve.py"],                    "R13"),
    "pip_install":     (GOOD, ["pip install astropy", "python3 solve.py"],
                                                                 "R14"),
    "mutate_input":    (GOOD, ["rm /root/data/image.hdr", "python3 solve.py"],
                                                                 "R15"),
    "solver_loop":     (GOOD.replace("R = math.hypot(x, y)",
                                     "from scipy.optimize import fsolve\n    R = fsolve(f, 1.0)"),
                        ["python3 solve.py"],                    "R16"),
    "bad_phi":         (GOOD.replace("math.atan2(x, -y)", "math.atan2(y, x)"),
                        ["python3 solve.py"],                    "R8"),
    "bad_theta":       (GOOD.replace("math.atan2(180.0/math.pi, R)", "math.atan(180.0/(math.pi*R))"),
                        ["python3 solve.py"],                    "R9"),
    "no_mod360":       (GOOD.replace(") % 360.0", ")"),
                        ["python3 solve.py"],                    "R10"),
    "no_lonpole":      (GOOD.replace("phi_p = 180.0", "").replace("dphi = phi - phi_p", "dphi = phi"),
                        ["python3 solve.py"],                    "R6"),
    # dedicated fixtures for the two criteria previously only seen failing
    # collaterally
    "no_header_read":  (GOOD.replace("for line in open('/root/data/image.hdr'):\n    pass\n", ""),
                        ["python3 solve.py"],                    "R3"),
    "no_lonpole_name": (GOOD, ["python3 solve.py"],              "R7"),
    # tightened-test fixtures: failure modes the earlier, looser tests missed
    "handwrote_answer": ("", [],                                 "R4",
                         {"file": ("/root/results.json", '{"sources": {"S01": {"ra_deg": 1.0}}}')}),
    "version_only":    (GOOD, ["python3 --version"],             "R5"),
    "curl_with_flags": (GOOD, ["curl -sO http://pypi.org/x", "python3 solve.py"],
                                                                 "R14"),
    "transcribed_rebase": (GOOD.replace("dx = px - CRPIX1", "dx = (px - 1) - 512.5"),
                        ["python3 solve.py"],                    "R13"),
    # BENIGN NEAR-MISS CONTROLS - prefixed '!': the named guardrail must NOT
    # fire. A guardrail never seen staying quiet under temptation is not a
    # guardrail: the cp control below caught a real false positive (the old
    # pattern fired on a read-direction copy).
    "benign_cp_out":   (GOOD, ["cp /root/data/sources.csv /tmp/work.csv", "python3 solve.py"],
                                                                 "!R15"),
    "benign_readonly": (GOOD, ["cat /root/data/image.hdr", "head -5 /root/data/sources.csv",
                               "python3 solve.py"],              "!R15"),
    "benign_local_curl": (GOOD, ["python3 solve.py", "echo 'see https://fits.gsfc.nasa.gov'"],
                                                                 "!R14"),
    # The two guardrails that had a firing fixture but no quiet one. Both carry
    # negative weight, so a false fire subtracts from a run that did nothing
    # wrong and nothing else in the suite would notice.
    #
    # A `- 1` next to a pixel coordinate is also how a 1-based FITS coordinate
    # indexes a 0-based array, which correct code does routinely - and it will
    # sit a line or two from the CRPIX arithmetic. This fixture does both, the
    # right way round: CRPIX is subtracted from the untouched coordinate, and the
    # `- 1` appears only where an array is actually indexed.
    "benign_array_index": (
        GOOD.replace("dec = math.asin(0.5)",
                     "dec = math.asin(0.5)\n"
                     "    val = image[int(round(py)) - 1][int(round(px)) - 1]"),
        ["python3 solve.py"],                                    "!R13"),
    # Confirming the answer by a second, independent construction is rewarded by
    # `R22` (weight 3). The natural second
    # construction is a forward round-trip driven to convergence, so a guardrail
    # that fired on any `scipy.optimize` would make the two contradict each other.
    "benign_check_loop": (
        GOOD + "\n"
        "from scipy.optimize import brentq\n"
        "def verify_roundtrip(sid, ra, dec):\n"
        "    residual = brentq(lambda t: t - 0.5, 0.0, 1.0)\n"
        "    assert abs(residual) < 1e-9\n",
        ["python3 solve.py"],                                    "!R16"),
    # Rounding inside a DIAGNOSTIC is not an output-precision defect - the
    # guardrail's own docstring names this exact case ("Rounding inside a
    # diagnostic print of a residual"), and an earlier version of the graded
    # test wrongly failed a passing run for it. The emitted coordinates stay
    # full precision; only a residual is formatted short, under a name that is
    # not a coordinate.
    "benign_diag_round": (
        GOOD + "\n"
        "residual_px = 0.0001234567\n"
        "print(f\"max residual {residual_px:.3f} px\")\n",
        ["python3 solve.py"],                                    "!R11"),
}


def record(code="", commands=(), extra=None, prose="", files=()):
    """One `llm_trajectory.jsonl` line in the shape the normaliser reads.

    `files` is [(path, content)] for runs that author more than one file - the
    correct run authors a module and a driver, as the golden did. `code` is the
    single-file shorthand the negative cases use.
    """
    extra = extra or {}
    content = []
    if code:
        content.append({"type": "tool_use", "name": "write",
                        "input": {"file_path": "/root/solve.py", "content": code}})
    for path, body in files:
        content.append({"type": "tool_use", "name": "write",
                        "input": {"file_path": path, "content": body}})
    if extra.get("file"):
        path, body = extra["file"]
        content.append({"type": "tool_use", "name": "write",
                        "input": {"file_path": path, "content": body}})
    for c in commands:
        content.append({"type": "tool_use", "name": "bash", "input": {"command": c}})
    if prose:
        content.append({"type": "text", "text": prose})
    msgs = [{"role": "user", "content": [{"type": "text", "text": "Task: astrometry"}]},
            {"role": "assistant", "content": content}]
    return {"request": {"body": {"messages": msgs}},
            "response": {"body": {"content": [{"type": "text", "text": "done"}]}}}


def write_run(run_dir, rec):
    """Materialise one synthetic run directory."""
    os.makedirs(os.path.join(run_dir, "trajectory"), exist_ok=True)
    os.makedirs(os.path.join(run_dir, "verifier"), exist_ok=True)
    with open(os.path.join(run_dir, "trajectory", "llm_trajectory.jsonl"), "w") as fh:
        fh.write(json.dumps(rec) + "\n")
    with open(os.path.join(run_dir, "verifier", "pass_at_1.txt"), "w") as fh:
        fh.write("0")
    with open(os.path.join(run_dir, "verifier", "reward.txt"), "w") as fh:
        fh.write("0.0")
    return run_dir


def correct_record():
    """The correct run: every positive criterion green, every guardrail quiet."""
    return record(files=CORRECT, commands=CORRECT_COMMANDS, prose=CORRECT_PROSE)


def case_record(name):
    spec = CASES[name]
    code, cmds, _target = spec[:3]
    extra = spec[3] if len(spec) > 3 else {}
    return record(code=code, commands=cmds, extra=extra)


def build(base=BASE):
    """Write every fixture under `base`. Returns {name: expected-failing-test}."""
    shutil.rmtree(base, ignore_errors=True)
    for name in CASES:
        write_run(os.path.join(base, name), case_record(name))
    write_run(os.path.join(base, "correct_run"), correct_record())
    return {k: v[2] for k, v in CASES.items()}


def main():
    print(json.dumps(build(), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
