"""Negative-fixture matrix: both halves of every deterministic criterion.

"A test you have never seen fail is not a test; a guardrail you have never seen
stay quiet under temptation is not a guardrail."

Every deterministic criterion in `../rubrics.json` gets BOTH halves here, and both
halves are COLLECTED pytest tests rather than lines inside a `main()`:

  * `test_good_fixture_is_accepted[<id>]`     - no check may fire on a correct run.
    A check that always fires would fail a correct run and is worse than no check.
  * `test_planted_defect_is_rejected[<id>]`   - the check must fire on a trajectory
    exhibiting exactly its failure mode. A check that never fires is inert.
  * one benign-near-miss test per guardrail, each naming that guardrail's test
    function, so the coverage can be attributed to it.

The GOOD fixture is adapted from this bundle's own oracle-armed golden trajectory
(`truth_armed/golden_run`): the same chain, condensed, with the 40 KB coefficient
table replaced by the file the run authored it into. `test_the_golden_run_itself_is
_all_green` grades the recorded golden directory directly, so the synthetic good
fixture is anchored to a real all-green run rather than to my own reading of it.

Each fixture is a real Erza run directory (a `trajectory/llm_trajectory.jsonl` in
the shape the normaliser reads), so the whole path - normaliser plus criterion -
runs, not just the regex.

WHY THE CRITERIA ARE IMPORTED, NEVER COPIED. The deterministic channel of this
bundle has no `checks.py` registry: each criterion IS the pytest function
`verifier/test_trajectory.py::test_<id>`. This module imports that module at RUN
time and calls those functions, resolving their pytest fixtures (`traj`, `code`)
through the module's own fixture definitions. Re-implementing a detector here
would mean the fixtures bind a copy and the graded criterion could drift away
from them unnoticed - which is the failure mode this file exists to prevent.

THE `o_*` CRITERIA ARE UNEVALUATED HERE, BY DESIGN. The outcome channel decides
its two criteria by reconstructing the run's solver and RE-EXECUTING it against
the shipped inputs. A synthetic fixture cannot exhibit "the probe re-derived an
answer outside tolerance" without shipping a whole working solver plus its
coefficient table, and what it would then be testing is the arithmetic, not the
criterion. They are listed in `UNEVALUATED` and excluded from the matrix, the way
the sibling suites' registries carry deterministic ids only.

NO `sys.argv` anywhere in this module. Under pytest, argv holds pytest's own
flags, and a module named `*_test.py` that reads them errors at COLLECTION and
takes every other test in this directory down with it.

    python3 -m pytest verification/negative_fixtures_test.py -q
    python3 verification/negative_fixtures_test.py        # firing table, no args
"""
import atexit
import importlib
import inspect
import json
import os
import re
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PROC = os.path.normpath(os.path.join(HERE, ".."))
BUNDLE = os.path.normpath(os.path.join(PROC, ".."))
GOLDEN_RUN = os.path.join(PROC, "truth_armed", "golden_run")
sys.path.insert(0, os.path.join(PROC, "lib"))
sys.path.insert(0, PROC)
import trajectory as T  # noqa: E402


# --------------------------------------------------------------------------- #
# calling the graded criteria                                                  #
# --------------------------------------------------------------------------- #

def _criteria_module():
    """The graded deterministic channel, imported at RUN time.

    Imported here rather than at module scope so that an edit landing in
    `verifier/test_trajectory.py` while this suite runs cannot half-import it:
    a failed import is retried once after `invalidate_caches()`, which is what a
    partially written file looks like from the outside.
    """
    for attempt in (1, 2):
        try:
            mod = sys.modules.get("test_pytest")
            return mod if mod is not None else importlib.import_module("test_pytest")
        except Exception:                       # noqa: BLE001 - retry once, then report
            if attempt == 2:
                raise
            sys.modules.pop("test_pytest", None)
            importlib.invalidate_caches()
    raise AssertionError("unreachable")


def _fixture_impl(obj):
    """The plain function behind a `@pytest.fixture`, across pytest versions.

    pytest 8 wraps the function in `__pytest_wrapped__`; pytest 9 replaces it
    with a `FixtureFunctionDefinition` exposing `_get_wrapped_function()`.
    Calling the decorated object directly is an error in both.
    """
    getter = getattr(obj, "_get_wrapped_function", None)
    if callable(getter):
        return getter()
    wrapped = getattr(obj, "__pytest_wrapped__", None)
    if wrapped is not None and hasattr(wrapped, "obj"):
        return wrapped.obj
    for attr in ("_fixture_function", "__wrapped__"):
        fn = getattr(obj, attr, None)
        if callable(fn):
            return fn
    return obj


def _resolve(fn, traj, mod, _depth=0):
    """Arguments for one criterion, resolving its pytest fixtures by name.

    The criteria take `traj` and the module's own derived views (`code`, which is
    `agent_code` with comments and docstrings stripped). Building those views
    from the module's fixture definitions - rather than restating them - is what
    keeps this suite honest: if the graded `code` view changes, these fixtures
    see the change.
    """
    assert _depth < 5, "fixture resolution recursed too deep"
    kwargs = {}
    for name in inspect.signature(fn).parameters:
        if name == "traj":
            kwargs[name] = traj
            continue
        provider = getattr(mod, name, None)
        assert provider is not None, (
            "criterion %s asks for fixture %r, which this suite cannot provide"
            % (getattr(fn, "__name__", fn), name))
        impl = _fixture_impl(provider)
        kwargs[name] = impl(**_resolve(impl, traj, mod, _depth + 1))
    return kwargs


def fires(cid, traj) -> bool:
    """True when the scored test for `cid` would FAIL on this trajectory.

    Uniform across polarities, because the channel's guardrail convention already
    is: a positive criterion fails when the behaviour is absent, and a guardrail
    fails when the failure mode occurred.
    """
    mod = _criteria_module()
    fn = getattr(mod, "test_" + cid, None)
    assert fn is not None, "no graded test in the deterministic channel for %s" % cid
    # Resolved OUTSIDE the try on purpose. `_resolve` asserts, and an assertion
    # raised by this HARNESS is not the criterion firing: swallowing it would
    # report every criterion as firing on every fixture, and the planted arm would
    # pass while measuring nothing - the exact vacuity this file exists to remove.
    kwargs = _resolve(fn, traj, mod)
    try:
        fn(**kwargs)
    except AssertionError:
        return True
    return False


# --------------------------------------------------------------------------- #
# synthetic run directories                                                    #
# --------------------------------------------------------------------------- #

_TMP: list = []


def _mk(file_writes=(), commands=(), prose=""):
    """Build a synthetic run dir and load it through the real normaliser."""
    blocks = []
    for path, content in file_writes:
        blocks.append({"type": "tool_use", "name": "Write",
                       "input": {"file_path": path, "content": content}})
    for c in commands:
        blocks.append({"type": "tool_use", "name": "Bash", "input": {"command": c}})
    if prose:
        blocks.append({"type": "text", "text": prose})
    line = {"request": {"body": {"messages": [
                {"role": "user", "content": [{"type": "text",
                                              "text": "Task: geomagnetic survey"}]},
                {"role": "assistant", "content": blocks}]}},
            "response": {"body": {"content": []}}}
    d = tempfile.mkdtemp(prefix="igrf-fix-")
    _TMP.append(d)
    os.makedirs(os.path.join(d, "trajectory"))
    with open(os.path.join(d, "trajectory", "llm_trajectory.jsonl"), "w") as fh:
        fh.write(json.dumps(line) + "\n")
    return T.load(d)


@atexit.register
def _cleanup():
    for d in _TMP:
        shutil.rmtree(d, ignore_errors=True)


# --------------------------------------------------------------------------- #
# The GOOD run, condensed from truth_armed/golden_run.
#
# The golden authored three files - the IAGA coefficient table, an `igrf_synth`
# module and a driver - and ran the driver. The table is 40 KB of numbers that no
# criterion reads, so it is left as the write it was; the module keeps the golden's
# own chain, function for function: parse coefficients, interpolate to the survey
# epoch, geodetic -> geocentric, Schmidt semi-normalised Legendre, spherical-
# harmonic synthesis, rotate into the geodetic north/up frame, declination,
# azimuth reduction.
#
# COMMENTS ARE NOT EVIDENCE. The graded `code` view blanks `#` comments and
# docstrings, so every token any criterion reads sits in real code here, and the
# planted defects below remove real code. `test_a_comment_is_not_evidence` pins it.
# --------------------------------------------------------------------------- #

_COEFF_HEAD = '''
import math

NMAX = 13
RE = 6371.2
WGS84_A = 6378.137
WGS84_E2 = 0.00669437999014
WGS84_B = WGS84_A * math.sqrt(1.0 - WGS84_E2)
EPOCHS = [1900.0 + 5.0 * i for i in range(25)]


def load_coeffs(path):
    g, h, sv_g, sv_h = {}, {}, {}, {}
    for line in open(path):
        if not (line.startswith("g ") or line.startswith("h ")):
            continue
        p = line.split()
        n, m = int(p[1]), int(p[2])
        (g if p[0] == "g" else h)[(n, m)] = [float(x) for x in p[3:28]]
        (sv_g if p[0] == "g" else sv_h)[(n, m)] = float(p[28])
    return g, h, sv_g, sv_h


def coeffs_at(date, path):
    g, h, sv_g, sv_h = load_coeffs(path)
    G, H = {}, {}
    if date < EPOCHS[-1]:
        i = max(k for k in range(len(EPOCHS) - 1) if EPOCHS[k] <= date)
        frac = (date - EPOCHS[i]) / (EPOCHS[i + 1] - EPOCHS[i])
        for k in g:
            G[k] = g[k][i] + frac * (g[k][i + 1] - g[k][i])
        for k in h:
            H[k] = h[k][i] + frac * (h[k][i + 1] - h[k][i])
    else:
        dt = date - EPOCHS[-1]
        for k in g:
            G[k] = g[k][-1] + dt * sv_g[k]
        for k in h:
            H[k] = h[k][-1] + dt * sv_h[k]
    return G, H
'''

# Gauss-normalised recurrence followed by the explicit Schmidt factor S, exactly
# as the golden's igrf_synth.py writes it.
_SCHMIDT_LEGENDRE = '''

def schmidt_legendre(theta_deg, nmax=NMAX):
    th = math.radians(theta_deg)
    st, ct = math.sin(th), math.cos(th)
    P = {(n, m): 0.0 for n in range(nmax + 1) for m in range(nmax + 1)}
    dP = dict(P)
    S = {(0, 0): 1.0}
    P[(0, 0)] = 1.0
    for n in range(1, nmax + 1):
        for m in range(0, n + 1):
            if n == m:
                P[(n, m)] = st * P[(n - 1, m - 1)]
                dP[(n, m)] = st * dP[(n - 1, m - 1)] + ct * P[(n - 1, n - 1)]
            elif n == 1:
                P[(n, m)] = ct * P[(n - 1, m)]
                dP[(n, m)] = ct * dP[(n - 1, m)] - st * P[(n - 1, m)]
            else:
                Knm = ((n - 1) ** 2 - m ** 2) / float((2 * n - 1) * (2 * n - 3))
                P[(n, m)] = ct * P[(n - 1, m)] - Knm * P[(n - 2, m)]
                dP[(n, m)] = (ct * dP[(n - 1, m)] - st * P[(n - 1, m)]
                              - Knm * dP[(n - 2, m)])
            if m == 0:
                S[(n, 0)] = S[(n - 1, 0)] * (2.0 * n - 1) / n
            else:
                S[(n, m)] = S[(n, m - 1)] * math.sqrt(
                    (n - m + 1) * ((1 if m == 1 else 0) + 1.0) / (n + m))
    for n in range(1, nmax + 1):
        for m in range(0, n + 1):
            P[(n, m)] *= S[(n, m)]
            dP[(n, m)] *= S[(n, m)]
    return P, dP
'''

# THE PLANTED DEFECT for R8: the textbook UNnormalised
# recurrence. Same Legendre machinery, same synthesis; no normalisation is formed
# anywhere - not named, not as a ratio, not from factorials, and not folded into
# the recursion coefficient. This is the error that puts the declination out by
# degrees while every other step looks right.
_PLAIN_LEGENDRE = '''

def legendre_plain(theta_deg, nmax=NMAX):
    th = math.radians(theta_deg)
    st, ct = math.sin(th), math.cos(th)
    P = {(n, m): 0.0 for n in range(nmax + 1) for m in range(nmax + 1)}
    dP = dict(P)
    P[(0, 0)] = 1.0
    for n in range(1, nmax + 1):
        for m in range(0, n + 1):
            if n == m:
                P[(n, m)] = (2 * n - 1) * st * P[(n - 1, m - 1)]
                dP[(n, m)] = (2 * n - 1) * (st * dP[(n - 1, m - 1)]
                                            + ct * P[(n - 1, m - 1)])
            elif m == n - 1:
                P[(n, m)] = (2 * n - 1) * ct * P[(n - 1, m)]
                dP[(n, m)] = (2 * n - 1) * (ct * dP[(n - 1, m)]
                                            - st * P[(n - 1, m)])
            else:
                P[(n, m)] = ((2 * n - 1) * ct * P[(n - 1, m)]
                             - (n + m - 1) * P[(n - 2, m)]) / (n - m)
                dP[(n, m)] = ((2 * n - 1) * (ct * dP[(n - 1, m)]
                                             - st * P[(n - 1, m)])
                              - (n + m - 1) * dP[(n - 2, m)]) / (n - m)
    return P, dP
'''

# position conversion, then the elements. LEGENDRE_FN is bound to whichever
# Legendre block the variant carries; ROTATION to whichever frame step it takes.
# The geodetic latitude is spelled `lat_deg` rather than `gdlat_deg` on purpose:
# `gdlat` alone satisfies R12's angle pattern (`d_?lat`
# matches inside it), so a variant that removes the rotation would still look
# rotated, and the fixture would prove nothing.
_SYNTH_TAIL = '''

def geodetic_to_geocentric(lat_deg, height_km):
    a, b = WGS84_A, WGS84_B
    lat = math.radians(lat_deg)
    s2, c2 = math.sin(lat) ** 2, math.cos(lat) ** 2
    tmp = height_km * math.sqrt(a ** 2 * c2 + b ** 2 * s2)
    beta = math.atan((tmp + b ** 2) / (tmp + a ** 2) * math.tan(lat))
    theta = math.pi / 2.0 - beta
    r = math.sqrt(height_km ** 2 + 2 * tmp
                  + a ** 2 * (1 - (1 - (b / a) ** 4) * s2)
                  / (1 - (1 - (b / a) ** 2) * s2))
    return math.degrees(theta), r

ROTATION_FN

def field_elements(date, lat_deg, lon_deg, height_km, path):
    G, H = coeffs_at(date, path)
    theta_deg, r = geodetic_to_geocentric(lat_deg, height_km)
    P, dP = LEGENDRE_FN(theta_deg)
    lam = math.radians(lon_deg)
    st = math.sin(math.radians(theta_deg))
    ratio = RE / r
    Br = Bth = Bph = 0.0
    for n in range(1, NMAX + 1):
        rn = ratio ** (n + 2)
        for m in range(0, n + 1):
            gnm, hnm = G.get((n, m), 0.0), H.get((n, m), 0.0)
            cm, sm = math.cos(m * lam), math.sin(m * lam)
            gc = gnm * cm + hnm * sm
            gs = m * (-gnm * sm + hnm * cm)
            Br += rn * (n + 1) * gc * P[(n, m)]
            Bth += -rn * gc * dP[(n, m)]
            Bph += -rn * gs * P[(n, m)] / st
    ROTATION
    return Bn, Bph, -Bu


def declination(date, lat_deg, lon_deg, height_km, path):
    X, Y, Z = field_elements(date, lat_deg, lon_deg, height_km, path)
    return math.degrees(math.atan2(Y, X))


def true_azimuth(date, lat_deg, lon_deg, height_km, mag_az_deg, path):
    D = declination(date, lat_deg, lon_deg, height_km, path)
    return (mag_az_deg + D) % 360.0
'''

_ROTATION_FN = '''
def rotate_to_geodetic_frame(theta_deg, lat_deg, B_th, B_r):
    psi = math.radians(lat_deg) - (math.pi / 2.0 - math.radians(theta_deg))
    Bn = -math.cos(psi) * B_th - math.sin(psi) * B_r
    Bu = -math.sin(psi) * B_th + math.cos(psi) * B_r
    return Bn, Bu

'''
_ROTATION_CALL = "Bn, Bu = rotate_to_geodetic_frame(theta_deg, lat_deg, Bth, Br)"

# THE PLANTED DEFECT for R12: the geocentric components
# are handed to the declination as if they were already the geodetic north/up
# pair. The rotation is gone, function and call, so no angle between the two
# latitudes is formed anywhere.
_NO_ROTATION_FN = ""
_NO_ROTATION_CALL = "Bn, Bu = -Bth, Br"


def _synth_module(legendre_block, legendre_fn, rotation_fn=_ROTATION_FN,
                  rotation_call=_ROTATION_CALL, head=_COEFF_HEAD):
    src = head + legendre_block + _SYNTH_TAIL
    return (src.replace("LEGENDRE_FN", legendre_fn)
               .replace("ROTATION_FN", rotation_fn)
               .replace("ROTATION", rotation_call))


CORRECT_SYNTH = _synth_module(_SCHMIDT_LEGENDRE, "schmidt_legendre")

CORRECT_DRIVER = '''
import csv
import json
import os

import igrf_synth

DATA = "/root/data"
COEFF = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "igrf13coeffs.txt")


def main():
    question = json.load(open(os.path.join(DATA, "question.json")))
    epoch = float(question["survey_epoch_decimal_year"])
    stations = {}
    for row in csv.DictReader(open(os.path.join(DATA, "stations.csv"))):
        stations[row["station_id"]] = {"true_azimuth_deg": igrf_synth.true_azimuth(
            epoch,
            float(row["latitude_deg"]),
            float(row["longitude_deg"]),
            float(row["elevation_m"]) / 1000.0,
            float(row["magnetic_azimuth_deg"]),
            COEFF)}
    json.dump({"stations": stations}, open("/root/results.json", "w"), indent=2)


main()
'''

# the coefficient table the golden authored, stubbed to two cards: no criterion
# reads it, and 40 KB of numbers in a fixture is 40 KB nobody will check.
COEFF_TABLE = (
    "g 1 0  -31543 ... -29404.8   5.7\n"
    "h 1 1    5922 ...   4652.5 -25.9\n"
)

CORRECT_COMMANDS = ["ls -la /root/data",
                    "cat /root/data/stations.csv",
                    "python3 /root/solve.py",
                    "cat /root/results.json"]
CORRECT_PROSE = ("Declination at survey precision is a model evaluation, not a "
                 "chart lookup: synthesise the field from the coefficients the "
                 "skill supplies, convert the station's geodetic position to "
                 "geocentric first, then reduce each magnetic azimuth.")


def good_run():
    """The correct run. Every positive criterion must accept it and every
    guardrail must stay quiet on it."""
    return _mk(file_writes=[("/root/igrf13coeffs.txt", COEFF_TABLE),
                            ("/root/igrf_synth.py", CORRECT_SYNTH),
                            ("/root/solve.py", CORRECT_DRIVER)],
               commands=CORRECT_COMMANDS,
               prose=CORRECT_PROSE)


# --------------------------------------------------------------------------- #
# One planted defect per criterion. Everything except the planted defect is kept
# plausible, so the fixture isolates the behaviour its criterion is about.
# --------------------------------------------------------------------------- #

# R11: the chart route the task's decoy invites - one rounded
# regional declination applied to every station.
_CHART_ROUTE = '''
import csv
import json

q = json.load(open("/root/data/question.json"))
d = q["decoy_reference"]["old_chart_declination_deg"]

out = {}
for row in csv.DictReader(open("/root/data/stations.csv")):
    az = float(row["magnetic_azimuth_deg"])
    out[row["station_id"]] = {"true_azimuth_deg": (az + d) % 360.0}

json.dump({"stations": out}, open("/root/results.json", "w"))
'''

# R6: no chart, but no model either - twelve declinations typed
# in from a table, so nothing is ever evaluated at the station's position.
_TYPED_TABLE = '''
import csv
import json

TABLE = {"GDS01": 13.6, "GDS02": 15.9, "GDS03": 15.1, "GDS04": 20.4,
         "GDS05": 18.4, "GDS06": 16.5, "GDS07": 19.4, "GDS08": 15.6,
         "GDS09": 18.6, "GDS10": 20.8, "GDS11": 19.1, "GDS12": 18.5}

out = {}
for row in csv.DictReader(open("/root/data/stations.csv")):
    sid = row["station_id"]
    az = float(row["magnetic_azimuth_deg"])
    out[sid] = {"true_azimuth_deg": (az + TABLE[sid]) % 360.0}

json.dump({"stations": out}, open("/root/results.json", "w"))
'''

# R7: the field IS synthesised, but the station's geodetic
# latitude is used as the polar angle and the elevation is dropped - the run never
# leaves the sphere, so no ellipsoid appears anywhere in it.
_SPHERE_HEAD = '''
import math

NMAX = 13
RE = 6371.2
EPOCHS = [1900.0 + 5.0 * i for i in range(25)]


def load_coeffs(path):
    g, h, sv_g, sv_h = {}, {}, {}, {}
    for line in open(path):
        if not (line.startswith("g ") or line.startswith("h ")):
            continue
        p = line.split()
        n, m = int(p[1]), int(p[2])
        (g if p[0] == "g" else h)[(n, m)] = [float(x) for x in p[3:28]]
        (sv_g if p[0] == "g" else sv_h)[(n, m)] = float(p[28])
    return g, h, sv_g, sv_h


def coeffs_at(date, path):
    g, h, sv_g, sv_h = load_coeffs(path)
    G, H = {}, {}
    dt = date - EPOCHS[-1]
    for k in g:
        G[k] = g[k][-1] + dt * sv_g[k]
    for k in h:
        H[k] = h[k][-1] + dt * sv_h[k]
    return G, H
'''

_SPHERE_TAIL = '''

def rotate_to_local_frame(B_th, B_r):
    tilt = 0.0
    Bn = -math.cos(tilt) * B_th - math.sin(tilt) * B_r
    Bu = -math.sin(tilt) * B_th + math.cos(tilt) * B_r
    return Bn, Bu


def field_elements(date, lat_deg, lon_deg, height_km, path):
    G, H = coeffs_at(date, path)
    theta_deg = 90.0 - lat_deg
    r = RADIUS
    P, dP = schmidt_legendre(theta_deg)
    lam = math.radians(lon_deg)
    st = math.sin(math.radians(theta_deg))
    ratio = RE / r
    Br = Bth = Bph = 0.0
    for n in range(1, NMAX + 1):
        rn = ratio ** (n + 2)
        for m in range(0, n + 1):
            gnm, hnm = G.get((n, m), 0.0), H.get((n, m), 0.0)
            cm, sm = math.cos(m * lam), math.sin(m * lam)
            gc = gnm * cm + hnm * sm
            gs = m * (-gnm * sm + hnm * cm)
            Br += rn * (n + 1) * gc * P[(n, m)]
            Bth += -rn * gc * dP[(n, m)]
            Bph += -rn * gs * P[(n, m)] / st
    Bn, Bu = rotate_to_local_frame(Bth, Br)
    return Bn, Bph, -Bu


def declination(date, lat_deg, lon_deg, height_km, path):
    X, Y, Z = field_elements(date, lat_deg, lon_deg, height_km, path)
    return math.degrees(math.atan2(Y, X))


def true_azimuth(date, lat_deg, lon_deg, height_km, mag_az_deg, path):
    D = declination(date, lat_deg, lon_deg, height_km, path)
    return (mag_az_deg + D) % 360.0
'''


def _sphere_module(radius_expr):
    src = _SPHERE_HEAD + _SCHMIDT_LEGENDRE + _SPHERE_TAIL
    return src.replace("RADIUS", radius_expr)


_SPHERE_NO_HEIGHT = _sphere_module("RE")
# R13: the station's elevation IS carried onto a spherical radius,
# so the run is visibly thinking about position - and still hands the geodetic
# latitude straight to the synthesis as if it were geocentric.
_SPHERE_WITH_HEIGHT = _sphere_module("RE + height_km")

# R3: the station table is transcribed into the solver and
# the shipped file is never opened.
_TRANSCRIBED_STATIONS = '''
import json

import igrf_synth

EPOCH = 2020.0
COEFF = "/root/igrf13coeffs.txt"
SURVEY = [("GDS01", 64.2, -152.3, 0.210, 37.4),
          ("GDS02", 66.85, -160.1, 0.095, 118.9),
          ("GDS03", 61.4, -149.9, 0.120, 205.2),
          ("GDS04", 68.1, -133.7, 0.060, 291.6),
          ("GDS05", 58.3, -134.4, 0.015, 73.0),
          ("GDS06", 70.2, -148.5, 0.008, 342.8),
          ("GDS07", 60.1, -141.0, 0.900, 159.5),
          ("GDS08", 67.5, -115.3, 0.180, 12.1),
          ("GDS09", 65.0, -126.8, 0.140, 248.7),
          ("GDS10", 72.1, -125.9, 0.030, 95.3),
          ("GDS11", 62.8, -137.6, 0.700, 300.0),
          ("GDS12", 55.2, -131.6, 0.010, 224.6)]

out = {}
for sid, lat, lon, elev_km, mag_az in SURVEY:
    out[sid] = {"true_azimuth_deg": igrf_synth.true_azimuth(
        EPOCH, lat, lon, elev_km, mag_az, COEFF)}

json.dump({"stations": out}, open("/root/results.json", "w"))
'''

# R9: the declination is added and the sum is emitted as it stands,
# so a station near due north comes out at 371 degrees.
_NO_WRAP_SYNTH = CORRECT_SYNTH.replace("return (mag_az_deg + D) % 360.0",
                                       "return mag_az_deg + D")

# R12: same chain, no frame rotation at all.
_NO_ROTATION_SYNTH = _synth_module(_SCHMIDT_LEGENDRE, "schmidt_legendre",
                                   rotation_fn=_NO_ROTATION_FN,
                                   rotation_call=_NO_ROTATION_CALL)

# R10: right arithmetic, invented output key.
_OFF_CONTRACT_DRIVER = CORRECT_DRIVER.replace('"true_azimuth_deg"',
                                              '"azimuth_true"')

PLANTED = {
    "R3": lambda: _mk(
        file_writes=[("/root/igrf_synth.py", CORRECT_SYNTH),
                     ("/root/solve.py", _TRANSCRIBED_STATIONS)],
        commands=["python3 /root/solve.py"],
        prose="Typed the survey table into the solver from the task statement."),

    "R4": lambda: _mk(
        commands=["cat /root/data/stations.csv",
                  "python3 -c 'print((37.4 + 6.5) % 360.0)'",
                  "echo '{\"stations\": {}}' > /root/results.json"],
        prose="Reduced the azimuths at the prompt; no solver authored."),

    "R5": lambda: _mk(
        file_writes=[("/root/igrf_synth.py", CORRECT_SYNTH),
                     ("/root/solve.py", CORRECT_DRIVER)],
        commands=["ls -la /root/data", "cat /root/data/stations.csv"],
        prose="Drafted the solver but never ran it."),

    "R6": lambda: _mk(
        file_writes=[("/root/solve.py", _TYPED_TABLE)],
        commands=["cat /root/data/stations.csv", "python3 /root/solve.py"],
        prose="Twelve declinations read off a table and added."),

    "R7": lambda: _mk(
        file_writes=[("/root/igrf_synth.py", _SPHERE_NO_HEIGHT),
                     ("/root/solve.py", CORRECT_DRIVER)],
        commands=["cat /root/data/stations.csv", "python3 /root/solve.py"],
        prose="Treated the station latitude as the polar angle on a sphere."),

    "R8": lambda: _mk(
        file_writes=[("/root/igrf_synth.py",
                      _synth_module(_PLAIN_LEGENDRE, "legendre_plain")),
                     ("/root/solve.py", CORRECT_DRIVER)],
        commands=["cat /root/data/stations.csv", "python3 /root/solve.py"],
        prose="Plugged the plain associated Legendre values into the sum."),

    "R9": lambda: _mk(
        file_writes=[("/root/igrf_synth.py", _NO_WRAP_SYNTH),
                     ("/root/solve.py", CORRECT_DRIVER)],
        commands=["cat /root/data/stations.csv", "python3 /root/solve.py"],
        prose="Added the declination and emitted the sum as it stands."),

    "R10": lambda: _mk(
        file_writes=[("/root/igrf_synth.py", CORRECT_SYNTH),
                     ("/root/solve.py", _OFF_CONTRACT_DRIVER)],
        commands=["cat /root/data/stations.csv", "python3 /root/solve.py"],
        prose="Right arithmetic under a key of my own choosing."),

    "R11": lambda: _mk(
        file_writes=[("/root/solve.py", _CHART_ROUTE)],
        commands=["cat /root/data/question.json", "python3 /root/solve.py"],
        prose="Used the single regional chart value shown in the task."),

    "R12": lambda: _mk(
        file_writes=[("/root/igrf_synth.py", _NO_ROTATION_SYNTH),
                     ("/root/solve.py", CORRECT_DRIVER)],
        commands=["cat /root/data/stations.csv", "python3 /root/solve.py"],
        prose="Took the geocentric components as the local north and up pair."),

    "R13": lambda: _mk(
        file_writes=[("/root/igrf_synth.py", _SPHERE_WITH_HEIGHT),
                     ("/root/solve.py", CORRECT_DRIVER)],
        commands=["cat /root/data/stations.csv", "python3 /root/solve.py"],
        prose="Carried the elevation onto a spherical radius and used the "
              "station latitude for the polar angle."),
}


# --------------------------------------------------------------------------- #
# Benign near-misses. Both guardrails here fire on the ABSENCE of work, so the
# temptation is the opposite of the usual one: a run that DID the work in a
# spelling the pattern does not enumerate. A false fire subtracts from a run that
# did nothing wrong, and nothing else in the suite would notice.
# --------------------------------------------------------------------------- #

# Synthesis through a library, with none of the vocabulary: no IGRF, no Schmidt,
# no Legendre - a published coefficient set and scipy's associated Legendre.
_LIBRARY_SYNTHESIS = '''
import csv
import json
import math

import numpy as np
from scipy.special import lpmv

NMAX = 13
A = 6371.2
ELL_A = 6378.137
ELL_E2 = 0.00669437999014
GNM = {(1, 0): -29404.8, (1, 1): -1450.9, (2, 0): -2500.0}
HNM = {(1, 1): 4652.5, (2, 1): 2982.0}


def to_geocentric(gdlat_deg, h_km):
    b2 = ELL_A ** 2 * (1.0 - ELL_E2)
    gd = math.radians(gdlat_deg)
    tmp = h_km * math.sqrt(ELL_A ** 2 * math.cos(gd) ** 2 + b2 * math.sin(gd) ** 2)
    beta = math.atan((tmp + b2) / (tmp + ELL_A ** 2) * math.tan(gd))
    return math.degrees(math.pi / 2.0 - beta), ELL_A + h_km


def elements(lat_deg, lon_deg, h_km):
    th_deg, r = to_geocentric(lat_deg, h_km)
    th, lam = math.radians(th_deg), math.radians(lon_deg)
    x = math.cos(th)
    br = bt = bp = 0.0
    for n in range(1, 3):
        for m in range(0, n + 1):
            s = math.sqrt(2.0 * math.factorial(n - m) / math.factorial(n + m)) \\
                if m else 1.0
            pnm = s * lpmv(m, n, x)
            dpnm = s * (n * x * lpmv(m, n, x) - (n + m) * lpmv(m, n - 1, x)) \\
                / max(1e-12, math.sin(th))
            gc = GNM.get((n, m), 0.0) * math.cos(m * lam) \\
                + HNM.get((n, m), 0.0) * math.sin(m * lam)
            gs = m * (-GNM.get((n, m), 0.0) * math.sin(m * lam)
                      + HNM.get((n, m), 0.0) * math.cos(m * lam))
            rn = (A / r) ** (n + 2)
            br += rn * (n + 1) * gc * pnm
            bt += -rn * gc * dpnm
            bp += -rn * gs * pnm / max(1e-12, math.sin(th))
    psi = math.radians(lat_deg) - (math.pi / 2.0 - th)
    north = -math.cos(psi) * bt - math.sin(psi) * br
    up = -math.sin(psi) * bt + math.cos(psi) * br
    return north, bp, -up


out = {}
for row in csv.DictReader(open("/root/data/stations.csv")):
    north, east, down = elements(float(row["latitude_deg"]),
                                 float(row["longitude_deg"]),
                                 float(row["elevation_m"]) / 1000.0)
    d = math.degrees(np.arctan2(east, north))
    out[row["station_id"]] = {
        "true_azimuth_deg": (float(row["magnetic_azimuth_deg"]) + d) % 360.0}

json.dump({"stations": out}, open("/root/results.json", "w"))
'''

# The recorded no-skill/run_3 shape: metres rather than kilometres, the
# eccentricity derived from the flattening, and the geocentric latitude named
# `phip`. The conversion is exact; none of the words appear.
_METRES_AND_TERSE = '''
import csv
import json
import math

a_wgs = 6378137.0
f = 1 / 298.257223563
e2 = f * (2 - f)
RE = 6371200.0
NMAX = 13
COEF = {(1, 0): -29404.8, (1, 1): -1450.9}


def position(lat_deg, lon_deg, h_m):
    lat = math.radians(lat_deg)
    nu = a_wgs / math.sqrt(1 - e2 * math.sin(lat) ** 2)
    p = (nu + h_m) * math.cos(lat)
    z = (nu * (1 - e2) + h_m) * math.sin(lat)
    phip = math.atan2(z, p)
    return math.degrees(math.pi / 2 - phip), math.hypot(p, z)


def legendre(th_deg, nmax=NMAX):
    th = math.radians(th_deg)
    st, ct = math.sin(th), math.cos(th)
    P = {(0, 0): 1.0}
    dP = {(0, 0): 0.0}
    S = {(0, 0): 1.0}
    for n in range(1, nmax + 1):
        for m in range(0, n + 1):
            P[(n, m)] = ct * P.get((n - 1, m), 0.0) if n != m \\
                else st * P.get((n - 1, m - 1), 0.0)
            dP[(n, m)] = -st * P.get((n - 1, m), 0.0)
            S[(n, m)] = S.get((n, m - 1), 1.0) * math.sqrt(
                (n - m + 1) * ((1 if m == 1 else 0) + 1.0) / (n + m)) if m \\
                else S.get((n - 1, 0), 1.0) * (2.0 * n - 1) / n
            P[(n, m)] *= S[(n, m)]
            dP[(n, m)] *= S[(n, m)]
    return P, dP


def declination(lat_deg, lon_deg, h_m):
    th_deg, r = position(lat_deg, lon_deg, h_m)
    P, dP = legendre(th_deg)
    lam = math.radians(lon_deg)
    br = bt = bp = 0.0
    for (n, m), g in COEF.items():
        rn = (RE / r) ** (n + 2)
        br += rn * (n + 1) * g * math.cos(m * lam) * P[(n, m)]
        bt += -rn * g * math.cos(m * lam) * dP[(n, m)]
        bp += -rn * m * (-g * math.sin(m * lam)) * P[(n, m)]
    psi = math.radians(lat_deg) - (math.pi / 2 - math.radians(th_deg))
    X = -math.cos(psi) * bt - math.sin(psi) * br
    up = -math.sin(psi) * bt + math.cos(psi) * br
    Z = -up
    return math.degrees(math.atan2(bp, X))


out = {}
for row in csv.DictReader(open("/root/data/stations.csv")):
    d = declination(float(row["latitude_deg"]), float(row["longitude_deg"]),
                    float(row["elevation_m"]))
    out[row["station_id"]] = {
        "true_azimuth_deg": (float(row["magnetic_azimuth_deg"]) + d) % 360.0}

json.dump({"stations": out}, open("/root/results.json", "w"))
'''

NEAR_MISS = {
    "R11": lambda: _mk(
        file_writes=[("/root/solve.py", _LIBRARY_SYNTHESIS)],
        commands=["cat /root/data/stations.csv", "python3 /root/solve.py"],
        prose="Summed a published main-field set with scipy's Legendre."),

    "R13": lambda: _mk(
        file_writes=[("/root/solve.py", _METRES_AND_TERSE)],
        commands=["cat /root/data/stations.csv", "python3 /root/solve.py"],
        prose="Worked in metres throughout; the eccentricity comes from the "
              "flattening."),
}


# --------------------------------------------------------------------------- #
# the criterion inventory, read off the rubric                                 #
# --------------------------------------------------------------------------- #

def _rubric():
    with open(os.path.join(PROC, "rubrics.json")) as fh:
        return json.load(fh)


_SPEC = _rubric()
DET_IDS = [c["id"] for c in _SPEC["criteria"] if c["channel"] == "deterministic"]
GUARDRAIL_IDS = [c["id"] for c in _SPEC["criteria"]
                 if c["channel"] == "deterministic" and not c["is_positive"]]

# Decided by probe re-execution, not by a pattern over the trajectory: see the
# module docstring. Listed so the exclusion is a recorded decision rather than an
# omission, and asserted below to be exactly the outcome channel.
UNEVALUATED = {
    "R1":
        "outcome channel - decided by reconstructing and re-executing the run's "
        "own solver against the shipped inputs; no trajectory pattern to plant",
    "R2":
        "outcome channel, GATE - decided by probe re-execution against the "
        "frozen truth; a fixture would grade arithmetic, not the criterion",
}

# Two criteria per predicate, by construction: `R6` /
# `R11` are the positive and guardrail readings of
# `_has_synthesis`, and `R7` / `R13` of
# `_has_geodetic_conversion` (the guardrail additionally requires synthesis, so
# it is moot on the chart route). No fixture can trip one member of a pair
# without the other; the fixtures below are distinct routes into each failure,
# and the collateral is expected rather than a fixture defect.
SHARED_PREDICATE_PAIRS = [("R6", "R11"),
                          ("R7", "R13")]


# --------------------------------------------------------------------------- #
# the collected matrix                                                         #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("cid", DET_IDS)
def test_good_fixture_is_accepted(cid):
    """No criterion may fire on a correct run."""
    assert not fires(cid, good_run()), (
        "%s fired on the GOOD fixture - it would fail a correct run" % cid)


@pytest.mark.parametrize("cid", DET_IDS)
def test_planted_defect_is_rejected(cid):
    """Every criterion must fire on a trajectory exhibiting its failure mode."""
    assert cid in PLANTED, "no planted-defect fixture for %s" % cid
    assert fires(cid, PLANTED[cid]()), (
        "%s stayed SILENT on a trajectory exhibiting exactly its failure mode"
        % cid)


def test_every_criterion_has_a_planted_defect_fixture():
    """A criterion with no negative fixture has never been seen to fail."""
    missing = sorted(set(DET_IDS) - set(PLANTED))
    assert not missing, "no planted-defect fixture for: %s" % ", ".join(missing)


def test_criterion_ids_match_the_deterministic_rubric():
    """score.py joins junit test names to criteria by stripping `test_`; a
    mismatch makes a criterion abstain silently rather than error."""
    mod = _criteria_module()
    _out = {c["id"] for c in _SPEC["criteria"] if c["channel"] == "outcome"}
    named = {n[len("test_"):] for n in dir(mod)
             if n.startswith("test_") and not n.startswith("test_zz")
             and not n.startswith("test_reward") and not n.startswith("test_selfcheck")
             and callable(getattr(mod, n))} - _out
    assert named == set(DET_IDS), (
        "only-in-module=%s only-in-rubrics=%s"
        % (sorted(named - set(DET_IDS)), sorted(set(DET_IDS) - named)))


def test_unevaluated_set_is_exactly_the_outcome_channel():
    """The suite abstains on the outcome criteria and on nothing else."""
    outcome = {c["id"] for c in _SPEC["criteria"] if c["channel"] == "outcome"}
    assert set(UNEVALUATED) == outcome, (
        "UNEVALUATED must list every outcome criterion and no other: "
        "only-in-UNEVALUATED=%s only-in-rubric=%s"
        % (sorted(set(UNEVALUATED) - outcome), sorted(outcome - set(UNEVALUATED))))
    assert not (set(UNEVALUATED) & set(DET_IDS)), (
        "a deterministic criterion is being excused as unevaluated")


def test_the_golden_run_itself_is_all_green():
    """The recorded oracle-armed golden trajectory, graded directly.

    The GOOD fixture above is a condensation of this run, and a condensation can
    drift from what it condenses. Grading the real directory pins the claim to
    bytes in the bundle instead of to the fixture author's reading of them.
    """
    assert os.path.isdir(GOLDEN_RUN), "golden run missing at %s" % GOLDEN_RUN
    traj = T.load(GOLDEN_RUN)
    fired = [cid for cid in DET_IDS if fires(cid, traj)]
    assert not fired, (
        "the oracle-armed golden run fails %d deterministic criteria: %s"
        % (len(fired), ", ".join(fired)))


def test_good_fixture_and_golden_run_agree():
    """Both all-green is necessary; agreeing criterion by criterion is the claim.

    A synthetic good fixture that passed for different reasons than the golden
    would still show green here, so the comparison is made explicit.
    """
    golden = T.load(GOLDEN_RUN)
    synthetic = good_run()
    disagree = [cid for cid in DET_IDS
                if fires(cid, golden) != fires(cid, synthetic)]
    assert not disagree, (
        "the condensed GOOD fixture and the golden run disagree on: %s"
        % ", ".join(disagree))


# --------------------------------------------------------------------------- #
# Benign near-misses, one test per guardrail, each naming its graded test.
#
# Written out rather than parametrized on purpose. A parametrized sweep calling
# `fires(cid, ...)` runs the same assertion, but nothing in the test body names
# the criterion, so neither a reader nor a coverage tool can tell WHICH guardrail
# was seen to stay quiet.
# --------------------------------------------------------------------------- #

def test_synthesis_guardrail_quiet_on_a_library_route_with_none_of_the_words():
    """A published coefficient set summed with `scipy.special.lpmv` IS field
    synthesis. The guardrail must key on the work, not on the words IGRF,
    Schmidt or Legendre appearing."""
    mod = _criteria_module()
    traj = NEAR_MISS["R11"]()
    code = _resolve(mod.test_R11, traj, mod)["code"]
    assert not re.search(r"igrf|schmidt|legendre", code, re.I), (
        "the fixture no longer exercises the no-vocabulary route")
    mod.test_R11(code)


def test_geodetic_guardrail_quiet_on_metres_and_an_undeclared_geocentric_latitude():
    """The recorded reward-1.0 shape: metres rather than kilometres, the
    eccentricity derived from the flattening, and the geocentric latitude named
    `phip`. The conversion is exact and none of the words appear; charging it
    would subtract from a correct run for a unit choice."""
    mod = _criteria_module()
    traj = NEAR_MISS["R13"]()
    code = _resolve(mod.test_R13, traj, mod)["code"]
    assert not re.search(r"geodetic|geocentric|colatitude", code, re.I), (
        "the fixture no longer exercises the undeclared-conversion route")
    mod.test_R13(code)


_DIRECT_QUIET_CALL = re.compile(r"mod\.(test_\w+)\(")


def test_every_guardrail_has_a_direct_near_miss_assertion():
    """Completeness, in both halves: every guardrail needs a benign fixture AND a
    test that calls its graded function while asserting it stays quiet. Adding a
    third guardrail without both fails here rather than silently going
    unexercised."""
    with open(os.path.abspath(__file__)) as fh:
        called = set(_DIRECT_QUIET_CALL.findall(fh.read()))
    for cid in GUARDRAIL_IDS:
        assert cid in NEAR_MISS, "no benign near-miss fixture for %s" % cid
        assert "test_" + cid in called, (
            "%s has a near-miss fixture but no test calling its graded function "
            "directly; the coverage cannot be attributed to this guardrail" % cid)


def test_a_comment_is_not_evidence():
    """The graded `code` view blanks comments and docstrings.

    A run that DESCRIBES the method it did not use must not be credited for it -
    and, the other way round, a planted defect hidden in a comment would not be
    a planted defect at all. This is why every fixture above puts its evidence,
    and its absence, in real code.
    """
    narrated = ("# Schmidt semi-normalised Legendre synthesis of the IGRF-13\n"
                "# Gauss coefficients, converted to geocentric first.\n"
                + _CHART_ROUTE)
    traj = _mk(file_writes=[("/root/solve.py", narrated)],
               commands=["python3 /root/solve.py"])
    mod = _criteria_module()
    code = _resolve(mod.test_R6, traj, mod)["code"]
    assert "Schmidt" not in code and "IGRF" not in code, (
        "the graded code view no longer strips comments; every fixture in this "
        "file assumes it does")
    assert fires("R6", traj), (
        "a chart-route run was credited with field synthesis it only described")


# --------------------------------------------------------------------------- #
# human-readable firing table                                                  #
# --------------------------------------------------------------------------- #

def main():
    """Firing table. Takes no arguments, by design."""
    ok = True
    good = good_run()

    print("GOOD fixture (condensed from truth_armed/golden_run) - nothing may fire:")
    for cid in DET_IDS:
        f = fires(cid, good)
        print("  %-32s %s" % (cid, "FIRED (unexpected)" if f else "quiet"))
        ok = ok and not f

    print("\nPLANTED defects - each criterion must fire on its own fixture:")
    for cid in DET_IDS:
        if cid not in PLANTED:
            print("  %-32s NO FIXTURE" % cid)
            ok = False
            continue
        traj = PLANTED[cid]()
        f = fires(cid, traj)
        collateral = [o for o in DET_IDS if o != cid and fires(o, traj)]
        print("  %-32s %-20s collateral: %s"
              % (cid, "fired" if f else "SILENT (unexpected)",
                 ", ".join(collateral) or "-"))
        ok = ok and f

    print("\nBENIGN near-misses - every guardrail must stay quiet:")
    for cid in GUARDRAIL_IDS:
        f = fires(cid, NEAR_MISS[cid]())
        print("  %-32s %s" % (cid, "FIRED (false positive)" if f else "quiet"))
        ok = ok and not f

    print("\nrecorded golden run (truth_armed/golden_run):")
    golden_fired = [cid for cid in DET_IDS if fires(cid, T.load(GOLDEN_RUN))]
    print("  %-32s %s" % ("all deterministic criteria",
                          "FIRED: " + ", ".join(golden_fired) if golden_fired
                          else "all green"))
    ok = ok and not golden_fired

    print("\nUNEVALUATED (outside this suite by design):")
    for cid, why in UNEVALUATED.items():
        print("  %-32s %s" % (cid, why))

    print("\n%s" % ("ALL FIXTURES BEHAVE AS EXPECTED" if ok
                    else "FIXTURE HARNESS FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
