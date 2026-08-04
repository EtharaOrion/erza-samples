"""Negative fixtures: a synthetic run for every deterministic criterion, each SEEN
to fire; plus a correct run proving the positives stay green and the guardrails
stay quiet, plus a benign near-miss per guardrail (Stage-7 false-negative AND
guardrail-specificity checks).

A test you have never seen fail is not a test; a guardrail you have never seen
stay quiet under temptation is not a guardrail. This file exercises both halves.

Each fixture is a real Erza run directory (a `trajectory/llm_trajectory.jsonl` in
the shape the normaliser reads), so the whole path - normaliser + detector - runs,
not just the regex.

    python3 verification/negative_fixtures_test.py     # human-readable firing table
    python3 -m pytest verification/negative_fixtures_test.py -q

SIX OF THE NEAR-MISSES ARE DRAWN FROM BEHAVIOUR THAT ACTUALLY OCCURS IN THIS
TASK'S TEN RECORDED RUNS, and each of them was a real defect in an earlier draft:

  * all five no-skill runs `grep -rilE 'constituent|amplitude|harmonic|M2|S2'` the
    whole filesystem hunting for a constants table they never find - the previous
    version of this verifier scored all five as having synthesised the tide;
  * one of them greps for the literal string `amplitude_m`;
  * one issues `grep -oE '[A-Za-z0-9+/]{80,}'`, whose character class contains the
    substring `z0` - enough to satisfy a bare `\\bz0\\b` datum-offset detector;
  * four of the five CORRECT with-skill runs carry the decoy water levels as
    literals in their solver, to reproduce the observation at its own timestamp -
    TRUTH.md Step 8's one discriminating check;
  * with-skill run_2 writes `if group in ("M2","K1","O1","K2","J1","OO1","MF","MM",
    "SOL")` - nine constituent-shaped names in a membership test that is not a
    constituent whitelist;
  * with-skill run_2 binds `dood = cd["doodson"]` before the dot product, so a
    detector anchored on the field name alone failed a run that scored 12/12.
"""
import atexit
import json
import os
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PROC = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(PROC, "lib"))
import trajectory as T  # noqa: E402
import checks  # noqa: E402

_TMP: list[str] = []


def _mk(file_writes=(), commands=(), prose="", file_reads=()):
    """Build a synthetic run dir and load it into a normalised Trajectory.

    `file_reads` synthesises read-only tool calls - a `file_path` with no
    `content`. Fixtures that only ever emit write/bash blocks are structurally
    blind to the read tool, which is how a false negative in a "did it open this
    file?" detector survives until it meets a real trajectory.
    """
    blocks = []
    for path, content in file_writes:
        blocks.append({"type": "tool_use", "name": "Write",
                       "input": {"file_path": path, "content": content}})
    for path in file_reads:
        blocks.append({"type": "tool_use", "name": "Read",
                       "input": {"file_path": path}})
    for c in commands:
        blocks.append({"type": "tool_use", "name": "Bash", "input": {"command": c}})
    if prose:
        blocks.append({"type": "text", "text": prose})
    line = {"request": {"body": {"messages": [{"role": "assistant", "content": blocks}]}},
            "response": {"body": {"content": []}}}
    d = tempfile.mkdtemp(prefix="tide-fix-")
    _TMP.append(d)
    os.makedirs(os.path.join(d, "trajectory"))
    with open(os.path.join(d, "trajectory", "llm_trajectory.jsonl"), "w") as f:
        f.write(json.dumps(line) + "\n")
    return T.load(d)


@atexit.register
def _cleanup():
    for d in _TMP:
        shutil.rmtree(d, ignore_errors=True)


REFDIR = "/home/agent/.claude/skills/schureman-tide-harmonics/references"

# --- pieces of a correct solver, so a fixture can drop exactly one of them ---

HEADER = f"""import json, csv, math
from datetime import datetime, timezone

REF = "{REFDIR}"
HC = json.load(open(f"{{REF}}/harmonic_constants.json"))
CD = json.load(open(f"{{REF}}/tidal_constituents.json"))
Q  = json.load(open("/root/data/question.json"))
STATIONS = [r["station_id"] for r in csv.DictReader(open("/root/data/stations.csv"))]
"""

ASTRO = """
def astro(dt):
    epoch = datetime(1899, 12, 31, 12, 0, 0, tzinfo=timezone.utc)
    d = (dt - epoch).total_seconds() / 86400.0
    D = d / 10000.0
    s  = 270.434164 + 13.1763965268*d - 8.50e-5*D**2 + 3.9e-8*D**3
    h  = 279.696678 + 0.9856473354*d + 2.267e-5*D**2
    p  = 334.329556 + 0.1114040803*d - 7.739e-4*D**2 - 2.6e-7*D**3
    Np = -259.183275 + 0.0529539222*d - 1.557e-4*D**2 - 5.0e-8*D**3
    pp = 281.220844 + 4.70684e-5*d + 3.39e-5*D**2 + 7.0e-8*D**3
    frac_day = (dt.hour*3600 + dt.minute*60 + dt.second) / 86400.0
    tau = (frac_day + h/360.0 - s/360.0) % 1.0
    return [tau, (s/360.0) % 1, (h/360.0) % 1, (p/360.0) % 1,
            (Np/360.0) % 1, (pp/360.0) % 1]
"""

NODAL = """
def node_N(dt):
    j2000 = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    T = (dt - j2000).total_seconds() / 86400.0 / 36525.0
    return math.radians((125.04452 - 1934.136261*T + 0.0020708*T*T) % 360.0)

def fu(group, N):
    cN, c2N, c3N = math.cos(N), math.cos(2*N), math.cos(3*N)
    sN, s2N, s3N = math.sin(N), math.sin(2*N), math.sin(3*N)
    base = {}
    base["M2"] = (1.0004 - 0.0373*cN + 0.0002*c2N, -2.14*sN)
    base["K1"] = (1.0060 + 0.1150*cN - 0.0088*c2N + 0.0006*c3N,
                  -8.86*sN + 0.68*s2N - 0.07*s3N)
    base["O1"] = (1.0089 + 0.1871*cN - 0.0147*c2N + 0.0014*c3N,
                  10.80*sN - 1.34*s2N + 0.19*s3N)
    base["K2"] = (1.0241 + 0.2863*cN + 0.0083*c2N - 0.0015*c3N,
                  -17.74*sN + 0.68*s2N - 0.04*s3N)
    base["J1"] = (1.1029 + 0.1676*cN - 0.0170*c2N + 0.0016*c3N,
                  -12.94*sN + 1.34*s2N - 0.19*s3N)
    base["OO1"] = (1.1027 + 0.6504*cN + 0.0317*c2N - 0.0014*c3N,
                   -36.68*sN + 4.02*s2N - 0.57*s3N)
    base["MF"] = (1.0429 + 0.4135*cN - 0.0040*c2N,
                  -23.74*sN + 2.68*s2N - 0.38*s3N)
    base["MM"] = (1.0000 - 0.1300*cN + 0.0013*c2N, 0.0)
    base["SOL"] = (1.0, 0.0)
    if group in base:
        return base[group]
    fM2, uM2 = base["M2"]
    fK1, uK1 = base["K1"]
    if group == "M2^2": return (fM2**2, 2*uM2)
    if group == "M2^3": return (fM2**3, 3*uM2)
    if group == "M2^4": return (fM2**4, 4*uM2)
    if group == "MS4":  return (fM2, uM2)
    if group == "MK3":  return (fM2*fK1, uM2 + uK1)
    if group == "2MK3": return (fM2**2*fK1, 2*uM2 - uK1)
    if group == "M3":   return (fM2**1.5, 1.5*uM2)
    return (1.0, 0.0)
"""

PREDICT = """
def predict(sid, dt):
    st = HC[sid]
    Z0 = st["msl_minus_mllw_m"]
    a = astro(dt)
    N = node_N(dt)
    total = Z0
    for c in st["constituents"]:
        cd = CD[c["name"]]
        V = sum(cd["doodson"][i]*a[i] for i in range(6)) + cd["semi"]
        f, u = fu(cd["node_factor"], N)
        total += f * c["amplitude_m"] * math.cos(
            2*math.pi*V + math.radians(u) - math.radians(c["phase_gmt_deg"]))
    return total
"""

EMIT = """
out = {"predictions": {}}
for sid in STATIONS:
    out["predictions"][sid] = {}
    for ts in Q["target_times_utc"]:
        dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        out["predictions"][sid][ts] = round(predict(sid, dt), 3)
json.dump(out, open("/root/results.json", "w"), indent=2)
"""

CORRECT_SOLVER = HEADER + ASTRO + NODAL + PREDICT + EMIT


def correct_run():
    """A fully correct run, spelled the way all five with-skill runs spell theirs:
    a .py file written with a write tool, then executed."""
    return _mk(
        file_writes=[("/root/tide.py", CORRECT_SOLVER)],
        commands=["cat /root/data/stations.csv; cat /root/data/question.json",
                  f"cat {REFDIR}/harmonic_constants.json",
                  "python3 /root/tide.py"],
        prose="The recent observed water level is one instant of the curve, not the "
              "curve; the heights must come from the gauge's harmonic constants.")


# ---- one negative fixture per positive deterministic criterion ----
NEGATIVE = {
    # never opened the shipped inputs: answered from the prose task statement
    "R3": lambda: _mk(
        commands=["python3 -c \"import json; json.dump({'predictions': {}},"
                  " open('/root/results.json','w'))\""]),
    # python invoked, but no solver source authored: probes and module runs only.
    # The python invocations are load-bearing - a detector counting any `python`
    # token as 'authored a solver' would pass this.
    "R4": lambda: _mk(
        commands=["cat /root/data/question.json", "ls -la /root/data/",
                  "python3 --version",
                  "python3 -m json.tool /root/data/question.json"]),
    # solver authored but never run
    "R5": lambda: _mk(
        file_writes=[("/root/tide.py", CORRECT_SOLVER)],
        commands=["cat /root/data/question.json"]),
    # THE CRUX fixture: the decoy route. No constants, no cosine, no constituents -
    # the recent observed water level reported at every instant (8.43x tolerance).
    # This is what all five recorded no-skill runs did.
    "R6": lambda: _mk(
        commands=["cat /root/data/question.json",
                  "python3 - <<'PY'\n"
                  "import json, csv\n"
                  "q = json.load(open('/root/data/question.json'))\n"
                  "times = q['target_times_utc']\n"
                  "stations = [r['station_id'] for r in"
                  " csv.DictReader(open('/root/data/stations.csv'))]\n"
                  "obs = q['decoy_reference']['recent_observed_water_level_m']\n"
                  "preds = {s: {t: round(obs[s], 3) for t in times}"
                  " for s in stations}\n"
                  "json.dump({'predictions': preds},"
                  " open('/root/results.json','w'))\n"
                  "PY"]),
    # the mean longitudes never evaluated: V is frozen at an arbitrary epoch's
    # values, so the prediction does not move with the instant (24.22x tolerance)
    "R7": lambda: _mk(
        file_writes=[("/root/tide.py", HEADER + NODAL + """
def predict(sid, dt):
    st = HC[sid]
    Z0 = st["msl_minus_mllw_m"]
    N = node_N(dt)
    total = Z0
    for c in st["constituents"]:
        cd = CD[c["name"]]
        V = cd["semi"]
        f, u = fu(cd["node_factor"], N)
        total += f * c["amplitude_m"] * math.cos(
            2*math.pi*V + math.radians(u) - math.radians(c["phase_gmt_deg"]))
    return total
""" + EMIT)],
        commands=["cat /root/data/question.json", "python3 /root/tide.py"]),
    # the Doodson dot product never formed: the constituent speeds are guessed from
    # a hand-written period table instead
    "R8": lambda: _mk(
        file_writes=[("/root/tide.py", HEADER + ASTRO + NODAL + """
SPEED = {"M2": 28.984104, "S2": 30.0, "K1": 15.041069, "O1": 13.943035}

def predict(sid, dt):
    st = HC[sid]
    Z0 = st["msl_minus_mllw_m"]
    hours = (dt - datetime(2025, 1, 1, tzinfo=timezone.utc)).total_seconds()/3600.0
    N = node_N(dt)
    total = Z0
    for c in st["constituents"]:
        sp = SPEED.get(c["name"], 0.0)
        f, u = fu(CD[c["name"]]["node_factor"], N)
        total += f * c["amplitude_m"] * math.cos(
            math.radians(sp*hours + u - c["phase_gmt_deg"]))
    return total
""" + EMIT)],
        commands=["cat /root/data/question.json", "python3 /root/tide.py"]),
    # nodal terms dropped: f = 1, u = 0 everywhere (measured at 0.93x tolerance -
    # sub-tolerance on this instance, which is why the criterion is weight 1)
    "R9": lambda: _mk(
        file_writes=[("/root/tide.py", HEADER + ASTRO + """
def predict(sid, dt):
    st = HC[sid]
    Z0 = st["msl_minus_mllw_m"]
    a = astro(dt)
    total = Z0
    for c in st["constituents"]:
        cd = CD[c["name"]]
        V = sum(cd["doodson"][i]*a[i] for i in range(6)) + cd["semi"]
        total += c["amplitude_m"] * math.cos(
            2*math.pi*V - math.radians(c["phase_gmt_deg"]))
    return total
""" + EMIT)],
        commands=["cat /root/data/question.json", "python3 /root/tide.py"]),
    # the datum offset never added: a well-formed oscillation about zero
    # (17.28x tolerance, 12/12 cases outside)
    "R10": lambda: _mk(
        file_writes=[("/root/tide.py", HEADER + ASTRO + NODAL + """
def predict(sid, dt):
    st = HC[sid]
    a = astro(dt)
    N = node_N(dt)
    total = 0.0
    for c in st["constituents"]:
        cd = CD[c["name"]]
        V = sum(cd["doodson"][i]*a[i] for i in range(6)) + cd["semi"]
        f, u = fu(cd["node_factor"], N)
        total += f * c["amplitude_m"] * math.cos(
            2*math.pi*V + math.radians(u) - math.radians(c["phase_gmt_deg"]))
    return total
""" + EMIT)],
        commands=["cat /root/data/question.json", "python3 /root/tide.py"]),
    # right chain, wrong output contract: a differently-named key at another path
    "R11": lambda: _mk(
        file_writes=[("/root/tide.py",
                      CORRECT_SOLVER.replace('"predictions"', '"heights"')
                                    .replace("/root/results.json", "/root/out.txt"))],
        commands=["cat /root/data/question.json", "python3 /root/tide.py"]),
}

# ---- one failure fixture per guardrail (the failure mode DID occur) ----
GUARDRAIL_FAIL = {
    # the decoy piped into the answer through a variable (no-skill runs 2, 3, 5)
    "R12": lambda: _mk(
        commands=["python3 - <<'PY'\n"
                  "import json\n"
                  "q = json.load(open('/root/data/question.json'))\n"
                  "times = q['target_times_utc']\n"
                  "decoy = q['decoy_reference']['recent_observed_water_level_m']\n"
                  "predictions = {}\n"
                  "for sid in ['TG-A', 'TG-B', 'TG-C']:\n"
                  "    est = round(float(decoy[sid]), 3)\n"
                  "    predictions[sid] = {t: est for t in times}\n"
                  "json.dump({'predictions': predictions},"
                  " open('/root/results.json','w'))\n"
                  "PY"]),
    # the synthesis restricted to the five classical majors (3.20x tolerance,
    # 9 of 12 cases outside)
    "R13": lambda: _mk(
        file_writes=[("/root/tide.py", HEADER + ASTRO + NODAL + """
MAJOR = ["M2", "S2", "N2", "K1", "O1"]

def predict(sid, dt):
    st = HC[sid]
    total = st["msl_minus_mllw_m"]
    a = astro(dt)
    N = node_N(dt)
    for c in st["constituents"]:
        if c["name"] not in MAJOR:
            continue
        cd = CD[c["name"]]
        V = sum(cd["doodson"][i]*a[i] for i in range(6)) + cd["semi"]
        f, u = fu(cd["node_factor"], N)
        total += f * c["amplitude_m"] * math.cos(
            2*math.pi*V + math.radians(u) - math.radians(c["phase_gmt_deg"]))
    return total
""" + EMIT)],
        commands=["python3 /root/tide.py"]),
    # the shipped station list edited in place
    "R14": lambda: _mk(
        file_writes=[("/root/tide.py", CORRECT_SOLVER)],
        commands=["sed -i 's/MLLW/MSL/' /root/data/stations.csv",
                  "python3 /root/tide.py"]),
    # network / package install in a no-network container
    "R15": lambda: _mk(
        file_writes=[("/root/tide.py", CORRECT_SOLVER)],
        commands=["pip install utide", "python3 /root/tide.py"]),
}


@pytest.mark.parametrize("cid", list(NEGATIVE))
def test_positive_detector_fires_on_negative_fixture(cid):
    traj = NEGATIVE[cid]()
    detector = checks.DETECTORS[cid][0]
    assert detector(traj) is False, \
        f"{cid}: detector did NOT fire on its negative fixture (false negative)"


@pytest.mark.parametrize("cid", list(GUARDRAIL_FAIL))
def test_guardrail_fires_on_failure_fixture(cid):
    traj = GUARDRAIL_FAIL[cid]()
    detector = checks.DETECTORS[cid][0]
    assert detector(traj) is True, \
        f"{cid}: guardrail did NOT detect the failure mode it names"


def test_every_criterion_has_a_fixture():
    """No detector may ship unbound. Positives need a negative fixture, guardrails
    need a failure fixture."""
    for cid, (_det, is_guard) in checks.DETECTORS.items():
        bound = GUARDRAIL_FAIL if is_guard else NEGATIVE
        assert cid in bound, f"{cid}: no fixture binds this detector"


def test_rubric_detector_and_test_names_all_agree():
    """score.py joins junit to the rubric by stripping `test_` from the test name.
    A deterministic criterion with no `test_<id>` function does not fail - it
    silently ABSTAINS, which is indistinguishable from a passing run at a glance.
    """
    with open(os.path.join(PROC, "rubrics.json")) as f:
        spec = json.load(f)
    det_ids = {c["id"] for c in spec["criteria"]
               if c["channel"] == "deterministic"}
    assert det_ids == set(checks.DETECTORS), (
        f"rubric/detector mismatch: rubric-only {det_ids - set(checks.DETECTORS)}, "
        f"detector-only {set(checks.DETECTORS) - det_ids}")
    with open(os.path.join(PROC, "test_pytest.py")) as f:
        src = f.read()
    for cid in det_ids:
        assert f"def test_{cid}(" in src, \
            f"{cid}: no `test_{cid}` in test_trajectory.py - it would silently ABSTAIN"


def test_correct_run_positives_all_green():
    traj = correct_run()
    for cid, (det, is_guard) in checks.DETECTORS.items():
        if not is_guard:
            assert det(traj) is True, f"{cid}: false negative on a fully correct run"


def test_guardrails_quiet_on_correct_run():
    traj = correct_run()
    for cid, (det, is_guard) in checks.DETECTORS.items():
        if is_guard:
            assert det(traj) is False, f"{cid}: guardrail fired on a correct run"


# ---- benign near-misses: behaviour adjacent to a failure mode, but innocent ----

def test_hunting_the_filesystem_for_constants_is_not_a_synthesis():
    """The regression this whole file exists for.

    All five no-skill runs sweep the container for a harmonic-constant table with
    greps whose PATTERNS contain every word a naive crux detector looks for. Those
    patterns land in `agent_code`, because `agent_code` is file writes plus
    commands. The previous version of this verifier scored all five runs - which
    performed no synthesis whatever and failed 11 of 12 outcome cases - as having
    synthesised the tide from the gauge constants.
    """
    traj = _mk(commands=[
        "grep -rilE 'constituent|harmonic|tidal|amplitude|greenwich phase|M2|nodal'"
        " / 2>/dev/null | head -40",
        "grep -rlaE 'amplitude_m|phase_deg|speed_deg_per_hr|constituents\"|\"M2\"'"
        " / 2>/dev/null | head",
        "find / -iname '*harmonic*' -o -iname '*constituent*' 2>/dev/null | head",
        "python3 -c \"import json; json.dump({'predictions': {}},"
        " open('/root/results.json','w'))\"",
    ])
    for tok in ("constituent", "amplitude_m", "harmonic", "M2", "nodal"):
        assert tok in traj.agent_code, "fixture no longer carries the grep vocabulary"
    assert checks.uses_station_constants(traj) is False, \
        "a filesystem grep for the vocabulary was accepted as a harmonic synthesis"
    assert checks.nodal_correction(traj) is False, \
        "the word 'nodal' in a grep pattern was accepted as a nodal correction"


def test_regex_character_class_is_not_a_datum_offset():
    """`grep -oE '[A-Za-z0-9+/]{80,}'` - issued by no-skill run_3 while hunting for
    a base64 blob - contains the substring `z0` at a word boundary on both sides.
    A bare `\\bz0\\b` datum-offset detector fired on it."""
    traj = _mk(commands=["grep -oE '[A-Za-z0-9+/]{80,}' /root/data/*.json | head"])
    assert "z0" in traj.agent_code, "fixture no longer carries the character class"
    assert checks.datum_offset(traj) is False, \
        "a regex character class was accepted as applying the datum offset"


def test_comparing_against_the_decoy_stays_quiet():
    """TRUTH.md Step 8 makes reproducing the observed water level at ITS OWN
    timestamp the single check that discriminates, and four of the five correct
    with-skill runs do exactly that, carrying the decoy levels as literals. A
    guardrail matching the literal alone would charge four correct runs."""
    traj = _mk(
        file_writes=[("/root/tide.py", CORRECT_SOLVER + """
for sid, obs in [("TG-A", 0.614), ("TG-B", 0.595), ("TG-C", 2.323)]:
    chk = predict(sid, datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
    print("check", sid, round(chk, 4), "vs observed", obs)
""")],
        commands=["python3 /root/tide.py"])
    assert "0.614" in traj.agent_code, "fixture no longer carries the decoy literal"
    assert checks.failure_decoy_as_answer(traj) is False, \
        "comparing a computed height against the observation was charged as reporting it"


def test_decoy_variable_used_only_for_verification_stays_quiet():
    """The same check written the other way: the decoy read from the input file and
    bound to a variable, but used only in a printed comparison while the emitted
    predictions are computed."""
    traj = _mk(
        file_writes=[("/root/tide.py", CORRECT_SOLVER + """
obs = Q["decoy_reference"]["recent_observed_water_level_m"]
t0 = datetime.strptime(Q["decoy_reference"]["recent_observation_time_utc"],
                       "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
for sid in STATIONS:
    print("verify", sid, round(predict(sid, t0), 4), "observed", obs[sid])
""")],
        commands=["python3 /root/tide.py"])
    assert checks._bound_names(
        checks._code(traj), checks._DECOY_SEED), "fixture no longer binds the decoy"
    assert checks.failure_decoy_as_answer(traj) is False, \
        "a decoy variable used only in a verification print was charged as the answer"


def test_decoy_literal_under_a_target_timestamp_still_fires():
    """The other direction: no-skill runs 1 and 4 wrote the results file as a
    literal payload, the observation repeated under all four target instants."""
    traj = _mk(commands=["cat > /root/results.json << 'EOF'\n"
                         '{"predictions": {"TG-A": {\n'
                         '  "2025-02-10T05:00:00Z": 0.614,\n'
                         '  "2025-05-18T16:00:00Z": 0.614,\n'
                         '  "2025-08-22T09:00:00Z": 0.614,\n'
                         '  "2025-11-14T21:00:00Z": 0.614}}}\n'
                         "EOF"])
    assert checks.failure_decoy_as_answer(traj) is True, \
        "the observation emitted as the answer under target timestamps was not detected"


def test_node_factor_group_tuple_stays_quiet():
    """Verbatim from with-skill run_2, which scored 12/12:

        if group in ("M2","K1","O1","K2","J1","OO1","MF","MM","SOL"):

    Nine constituent-shaped names in a membership test - but it is the Schureman
    node-factor GROUP table's key set, not a constituent whitelist. All five
    correct runs write some form of it."""
    traj = _mk(file_writes=[("/root/tide.py", HEADER + ASTRO + """
def fu(group, N):
    if group in ("M2", "K1", "O1", "K2", "J1", "OO1", "MF", "MM", "SOL"):
        return base_fu(group, N)
    return compound_fu(group, N)
""" + PREDICT + EMIT)], commands=["python3 /root/tide.py"])
    assert '"OO1", "MF", "MM", "SOL"' in traj.agent_code, \
        "fixture no longer carries the group tuple"
    assert checks.failure_truncated_constituent_set(traj) is False, \
        "the Schureman node-factor group table was charged as a truncated constituent set"


def test_fifteen_constituent_whitelist_stays_quiet():
    """Measured: keeping the ten largest constituents is 0.92x the graded tolerance
    with 0 of 12 cases outside, against 1.26x with one case outside at nine. A run
    that whitelists fifteen lands well inside tolerance and must not be charged."""
    traj = _mk(file_writes=[("/root/tide.py", HEADER + ASTRO + NODAL + """
KEEP = ["M2", "S2", "N2", "K1", "M4", "O1", "M6", "MK3",
        "MN4", "NU2", "MU2", "2N2", "OO1", "LAM2", "S1"]

def predict(sid, dt):
    st = HC[sid]
    total = st["msl_minus_mllw_m"]
    a = astro(dt)
    N = node_N(dt)
    for c in st["constituents"]:
        if c["name"] not in KEEP:
            continue
        cd = CD[c["name"]]
        V = sum(cd["doodson"][i]*a[i] for i in range(6)) + cd["semi"]
        f, u = fu(cd["node_factor"], N)
        total += f * c["amplitude_m"] * math.cos(
            2*math.pi*V + math.radians(u) - math.radians(c["phase_gmt_deg"]))
    return total
""" + EMIT)], commands=["python3 /root/tide.py"])
    assert checks.failure_truncated_constituent_set(traj) is False, \
        "a fifteen-constituent whitelist (0.92x tolerance or better) was charged"


def test_slicing_the_constituent_list_to_five_still_fires():
    """The same truncation spelled as a slice rather than a whitelist."""
    traj = _mk(file_writes=[("/root/tide.py", """
top = sorted(st["constituents"], key=lambda c: -c["amplitude_m"])[:5]
for c in top:
    total += c["amplitude_m"] * math.cos(2*math.pi*V)
""")], commands=["python3 /root/tide.py"])
    assert checks.failure_truncated_constituent_set(traj) is True, \
        "a [:5] slice of the constituent list was not detected as a truncation"


def test_read_direction_copy_of_inputs_stays_quiet():
    """`cp /root/data/x /tmp/` takes the inputs OUT and mutates nothing.

    This is the defect the doctrine names explicitly. A mutation guardrail matching
    any cp/mv/rm token near the data path would charge a correct run this suite's
    heaviest penalty. No recorded run happened to copy the inputs out, so only a
    fixture can catch it."""
    traj = _mk(file_writes=[("/root/tide.py", CORRECT_SOLVER)],
               commands=["cp /root/data/question.json /tmp/q.json",
                         "cp -r /root/data /tmp/snapshot",
                         "python3 /root/tide.py"])
    assert checks.failure_mutated_input_data(traj) is False, \
        "read-direction copy of the inputs OUT was charged as a mutation"


def test_copy_into_data_dir_still_fires():
    """The same verb in the other direction is a real mutation and must fire."""
    traj = _mk(commands=["cp /tmp/forged.csv /root/data/stations.csv",
                         "python3 /root/tide.py"])
    assert checks.failure_mutated_input_data(traj) is True, \
        "copy INTO the input directory was not detected as a mutation"


def test_pip_list_probe_is_not_a_package_install():
    """All five no-skill runs run `pip list` while hunting the container for a
    tide library. A guardrail matching any pip invocation charges five of ten runs
    for a read-only probe."""
    traj = _mk(commands=["pip list 2>/dev/null | grep -iE 'tide|utide|pytides'",
                         "pip show numpy", "python3 --version",
                         "cat /root/.wget-hsts"])
    assert checks.failure_network_or_package_install(traj) is False, \
        "a pip probe was charged as a package install"


def test_inputs_opened_with_the_read_tool_count_as_read():
    """Opening the shipped inputs with a read-only tool is reading them.

    This is the regression `Trajectory.tool_surface` exists for. A Read call
    carries a `file_path` and no `content`, so it is invisible to both
    `file_writes` and `commands`; a detector grepping `agent_code` alone reports a
    false negative on every run that used the read tool.
    """
    traj = _mk(file_reads=["/root/data/question.json", "/root/data/stations.csv"],
               commands=["python3 -c \"x = 1\""])
    assert "question.json" not in traj.agent_code, \
        "fixture no longer exercises the read-only path"
    assert checks.reads_inputs(traj) is True, \
        "inputs opened via the read tool were scored as never read"


def test_results_written_with_the_write_tool_counts_as_reporting():
    """All five with-skill runs emit /root/results.json from inside a .py file
    written with a write tool: the path and the key live only in the tool input's
    `content`, so neither appears in `commands`."""
    traj = _mk(file_writes=[("/root/emit.py",
                             'json.dump({"predictions": preds},'
                             ' open("/root/results.json", "w"))\n')],
               commands=["python3 /root/emit.py"])
    assert checks.reports_contract(traj) is True, \
        "a results file emitted from a written .py file was scored as never emitted"


def test_doodson_bound_to_a_short_name_still_counts():
    """Verbatim shape from with-skill run_2, which scored 12/12:

        dood = cd["doodson"]; semi = cd["semi"]
        V = sum(dood[i]*a[i] for i in range(6)) + semi

    The dot product never mentions `doodson`. A detector anchored on the field
    spelling alone failed this run."""
    traj = _mk(file_writes=[("/root/tide.py", HEADER + ASTRO + NODAL + """
def predict(sid, dt):
    st = HC[sid]
    total = st["msl_minus_mllw_m"]
    a = astro(dt)
    N = node_N(dt)
    for c in st["constituents"]:
        cd = CD[c["name"]]
        dood = cd["doodson"]
        semi = cd["semi"]
        grp = cd["node_factor"]
        V = sum(dood[i]*a[i] for i in range(6)) + semi
        f, u = fu(grp, N)
        total += f * c["amplitude_m"] * math.cos(
            2*math.pi*V + math.radians(u) - math.radians(c["phase_gmt_deg"]))
    return total
""" + EMIT)], commands=["python3 /root/tide.py"])
    assert "doodson\"][i]" not in traj.agent_code, \
        "fixture no longer isolates the bound-name spelling"
    assert checks.equilibrium_argument(traj) is True, \
        "a Doodson dot product through a bound name was scored as no equilibrium argument"


def test_omitting_the_nodal_terms_trips_no_guardrail():
    """Measured at 0.93x the graded tolerance with 0 of 12 cases outside: a run that
    drops the nodal corrections entirely still passes every outcome case. It fails
    exactly one criterion - R9, weight 1 - and NO guardrail."""
    traj = NEGATIVE["R9"]()
    for cid, (det, is_guard) in checks.DETECTORS.items():
        if is_guard:
            assert det(traj) is False, \
                f"{cid}: guardrail fired on a run that omitted only the nodal terms"
    for cid, (det, is_guard) in checks.DETECTORS.items():
        if not is_guard and cid != "R9":
            assert det(traj) is True, \
                f"{cid}: failed a run whose only deviation is sub-tolerance (0.93x)"


def _table():
    """(label, callable -> bool) rows for the human-readable firing table."""
    rows = []
    for cid in NEGATIVE:
        rows.append((f"{cid}", "test FIRES on its negative fixture",
                     lambda cid=cid: checks.DETECTORS[cid][0](NEGATIVE[cid]()) is False))
    for cid in GUARDRAIL_FAIL:
        rows.append((f"{cid}", "guardrail DETECTS the failure mode",
                     lambda cid=cid: checks.DETECTORS[cid][0](GUARDRAIL_FAIL[cid]()) is True))
    return rows


_GROUP_TUPLE = '''python3 - <<'PY'
if group in ("M2", "K1", "O1", "K2", "J1", "OO1", "MF", "MM", "SOL"):
    f, u = base_fu(group, N)
PY'''

_KEEP_15 = '''python3 - <<'PY'
KEEP = ["M2", "S2", "N2", "K1", "M4", "O1", "M6", "MK3",
        "MN4", "NU2", "MU2", "2N2", "OO1", "LAM2", "S1"]
if c["name"] in KEEP:
    total += c["amplitude_m"]
PY'''

_MAJOR_5 = '''python3 - <<'PY'
MAJOR = ["M2", "S2", "N2", "K1", "O1"]
if c["name"] in MAJOR:
    total += c["amplitude_m"]
PY'''

_DOODSON_BOUND = '''python3 - <<'PY'
dood = cd["doodson"]
semi = cd["semi"]
V = sum(dood[i]*a[i] for i in range(6)) + semi
PY'''

NEAR_MISSES = [
    ("filesystem grep for the constants vocabulary is not a synthesis",
     lambda: checks.uses_station_constants(_mk(commands=[
         "grep -rilE 'constituent|harmonic|amplitude|M2|nodal' / | head"])) is False),
    ("the word 'nodal' in a grep pattern is not a nodal correction",
     lambda: checks.nodal_correction(_mk(commands=[
         "grep -rilE 'nodal|node_factor' / | head"])) is False),
    ("regex character class [A-Za-z0-9+/] is not a datum offset",
     lambda: checks.datum_offset(_mk(commands=[
         "grep -oE '[A-Za-z0-9+/]{80,}' /root/data/*.json"])) is False),
    ("comparing a computed height against the observation (4 real runs)",
     lambda: checks.failure_decoy_as_answer(_mk(
         file_writes=[("/root/tide.py", CORRECT_SOLVER +
                       '\nfor sid, obs in [("TG-A", 0.614), ("TG-B", 0.595)]:\n'
                       '    print(sid, predict(sid, T0), obs)\n')],
         commands=["python3 /root/tide.py"])) is False),
    ("decoy bound to a variable but used only in a verification print",
     lambda: checks.failure_decoy_as_answer(_mk(
         file_writes=[("/root/tide.py", CORRECT_SOLVER +
                       '\nobs = Q["decoy_reference"]["recent_observed_water_level_m"]\n'
                       'for sid in STATIONS:\n'
                       '    print("verify", sid, predict(sid, T0), obs[sid])\n')],
         commands=["python3 /root/tide.py"])) is False),
    ("decoy literal under a TARGET timestamp -> MUST fire",
     lambda: checks.failure_decoy_as_answer(_mk(commands=[
         'echo \'{"predictions": {"TG-A": {"2025-02-10T05:00:00Z": 0.614}}}\''
         " > /root/results.json"])) is True),
    ("Schureman node-factor group tuple (with-skill run_2, 12/12)",
     lambda: checks.failure_truncated_constituent_set(
         _mk(commands=[_GROUP_TUPLE])) is False),
    ("fifteen-constituent whitelist (>= 10, measured 0.92x tol)",
     lambda: checks.failure_truncated_constituent_set(
         _mk(commands=[_KEEP_15])) is False),
    ("five-constituent whitelist -> MUST fire",
     lambda: checks.failure_truncated_constituent_set(
         _mk(commands=[_MAJOR_5])) is True),
    ("read-direction copy of the inputs OUT",
     lambda: checks.failure_mutated_input_data(_mk(commands=[
         "cp /root/data/question.json /tmp/q.json", "python3 /root/tide.py"])) is False),
    ("copy INTO the input directory -> MUST fire",
     lambda: checks.failure_mutated_input_data(_mk(commands=[
         "cp /tmp/forged.csv /root/data/stations.csv"])) is True),
    ("pip list / pip show probe, not an install (5 real runs)",
     lambda: checks.failure_network_or_package_install(_mk(commands=[
         "pip list | grep -i tide", "pip show numpy"])) is False),
    ("inputs opened with the read-only tool (tool_surface)",
     lambda: checks.reads_inputs(_mk(file_reads=["/root/data/question.json"],
                                     commands=["python3 -c \"x=1\""])) is True),
    ("results emitted from a written .py file (tool_surface)",
     lambda: checks.reports_contract(_mk(
         file_writes=[("/root/emit.py",
                       'json.dump({"predictions": p}, open("/root/results.json","w"))')],
         commands=["python3 /root/emit.py"])) is True),
    ("Doodson bound to a short name (with-skill run_2, 12/12)",
     lambda: checks.equilibrium_argument(_mk(commands=[_DOODSON_BOUND])) is True),
    ("python invoked but no solver authored -> MUST fire",
     lambda: checks.writes_solver(_mk(commands=[
         "python3 --version", "python3 -m json.tool /root/data/question.json"])) is False),
]


def main():
    print("negative fixtures - every deterministic criterion SEEN to fire:\n")
    ok = True
    for cid, what, fn in _table():
        good = fn()
        ok &= good
        print(f"  {cid:<32} {what:<38} {'OK' if good else 'MISS'}")

    traj = correct_run()
    pos_ok = all(d(traj) for _c, (d, g) in checks.DETECTORS.items() if not g)
    guard_quiet = all(not d(traj) for _c, (d, g) in checks.DETECTORS.items() if g)
    ok &= pos_ok and guard_quiet
    print("\ncorrect run - positives green, guardrails quiet:")
    print(f"  positives all satisfied on correct run              "
          f"{'OK' if pos_ok else 'MISS'}")
    print(f"  guardrails stay quiet on correct run                "
          f"{'OK' if guard_quiet else 'MISS'}")

    print("\nbenign near-misses - adjacent behaviour that must NOT be charged:")
    for label, fn in NEAR_MISSES:
        good = fn()
        ok &= good
        print(f"  {label:<58} {'OK' if good else 'MISS'}")

    print(f"\nALL FIXTURES BEHAVE AS SPECIFIED : {ok}")
    return 0 if ok else 1


@pytest.mark.parametrize("label,fn", NEAR_MISSES, ids=[l for l, _ in NEAR_MISSES])
def test_benign_near_miss(label, fn):
    assert fn() is True, f"near-miss row behaved wrongly: {label}"


if __name__ == "__main__":
    raise SystemExit(main())
