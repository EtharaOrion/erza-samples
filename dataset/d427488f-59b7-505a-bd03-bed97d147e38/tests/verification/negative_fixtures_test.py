"""Negative-fixture matrix: both halves of every deterministic criterion.

"A test you have never seen fail is not a test; a guardrail you have never seen
stay quiet under temptation is not a guardrail."

Every deterministic criterion in `../rubrics.json` gets BOTH halves here, and both
halves are COLLECTED pytest tests rather than lines inside a `main()`:

  * `test_clean_fixture_is_accepted[<id>]`  - the check must stay quiet on a
    correct, with-skill-style run. A check that always fires would fail a correct
    run and is worse than no check.
  * `test_planted_defect_is_rejected[<id>]` - the check must fire on a trajectory
    exhibiting exactly its failure mode. A check that never fires is inert.
  * one benign-near-miss test PER GUARDRAIL, each calling that guardrail's
    detector by name - the guardrails carry negative weights (one of them -5), so
    a false fire is expensive: it subtracts from a run that did nothing wrong and
    nothing else in the suite would notice.

This matrix is the ONLY place most of these detectors have ever been seen to
fire: the 60-run sweep leaves R6, R7,
R9 and R13 at 0/60. Take the fixture
verdicts as the evidence the recorded pool does not supply.

Each fixture is a real Erza run directory (a `trajectory/llm_trajectory.jsonl` in
the shape the normaliser reads), so the whole path - normaliser plus detector -
runs, not just the regex.

NO `sys.argv` anywhere in this module. Under pytest, argv holds pytest's own
flags, and a module named `*_test.py` that reads them errors at COLLECTION and
takes every other test in this directory down with it.

    python3 -m pytest verification/negative_fixtures_test.py -q
"""
import atexit
import json
import os
import re
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PROC = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(PROC, "lib"))
import trajectory as T  # noqa: E402
import checks  # noqa: E402

_TMP: list = []


def _mk(file_writes=(), commands=(), prose=""):
    """Build a synthetic run dir and load it through the real normaliser."""
    blocks = []
    for path, content in file_writes:
        blocks.append({"type": "tool_use", "name": "write",
                       "input": {"file_path": path, "content": content}})
    for c in commands:
        blocks.append({"type": "tool_use", "name": "bash", "input": {"command": c}})
    if prose:
        blocks.append({"type": "text", "text": prose})
    line = {"request": {"body": {"messages": [{"role": "assistant", "content": blocks}]}},
            "response": {"body": {"content": []}}}
    d = tempfile.mkdtemp(prefix="rb1-fix-")
    _TMP.append(d)
    os.makedirs(os.path.join(d, "trajectory"))
    with open(os.path.join(d, "trajectory", "llm_trajectory.jsonl"), "w") as fh:
        fh.write(json.dumps(line) + "\n")
    return T.load(d)


@atexit.register
def _cleanup():
    for d in _TMP:
        shutil.rmtree(d, ignore_errors=True)


def fires(cid, tr) -> bool:
    """True when the scored test for `cid` would FAIL on this trajectory."""
    fn, is_guardrail = checks.DETECTORS[cid]
    got = bool(fn(tr))
    return got if is_guardrail else (not got)


# --------------------------------------------------------------------------- #
# The clean run: median within-lab reduction, MAD-initialised clamped iteration
# at the house clamp with the closed-form beta(c) debias applied every round,
# coverage-factored combined uncertainty, and the contract. Every positive
# detector must accept it and every guardrail must stay quiet on it.
# --------------------------------------------------------------------------- #
CLEAN_SOLVER = '''
import json, math, statistics

meas = json.load(open("/root/data/measurements.json"))
q = json.load(open("/root/data/question.json"))
labs = meas["labs"]
Lstar = q["nominated_lab"]
C = 1.25
U_FACTOR = 1.25


def phi(z):
    return math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)


def Phi(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def beta_of_c(c):
    ew2 = (2.0 * Phi(c) - 1.0) - 2.0 * c * phi(c) + 2.0 * c * c * (1.0 - Phi(c))
    return 1.0 / math.sqrt(ew2)


lab_val = {k: statistics.median(v) for k, v in labs.items()}
vals = list(lab_val.values())
n = len(vals)
b = beta_of_c(C)
x = statistics.median(vals)
s = 1.4826 * statistics.median([abs(v - x) for v in vals])
for _ in range(60):
    lo, hi = x - C * s, x + C * s
    clamped = [min(max(v, lo), hi) for v in vals]
    x_new = sum(clamped) / n
    var = sum((v - x_new) ** 2 for v in clamped) / (n - 1)
    s_new = b * math.sqrt(var)
    if abs(x_new - x) < 1e-12 and abs(s_new - s) < 1e-12:
        x, s = x_new, s_new
        break
    x, s = x_new, s_new

u = U_FACTOR * s / math.sqrt(n)
zeta = (lab_val[Lstar] - x) / u
json.dump({"robust_scale": round(s, 6), "zeta_prime": round(zeta, 6)},
          open("/root/results.json", "w"))
'''

_CLEAN_RESULTS = '{"robust_scale": 0.250368, "zeta_prime": 1.690145}'


def clean_run():
    return _mk(
        file_writes=[("solve.py", CLEAN_SOLVER),
                     ("/root/results.json", _CLEAN_RESULTS)],
        commands=["head -c 400 /root/data/measurements.json", "python3 solve.py"],
        prose=("ERZA-RB1 is a house SOP, so the clamp, the closed-form debias and "
               "the coverage factor come from its specification rather than from "
               "the textbook algorithm; beta at the house clamp checks out "
               "against the documented value."))


TERSE_CLEAN_SOLVER = '''
import json, math
import numpy as np
from statistics import NormalDist

M = json.load(open("/root/data/measurements.json"))
Q = json.load(open("/root/data/question.json"))
star = Q["nominated_lab"]
CLAMP = 1.25
kU = 1.25

N = NormalDist()
e = (2 * N.cdf(CLAMP) - 1) - 2 * CLAMP * N.pdf(CLAMP) \\
    + 2 * CLAMP ** 2 * (1 - N.cdf(CLAMP))
bb = 1 / math.sqrt(e)

v = np.array([np.median(r) for r in M["labs"].values()])
star_v = float(np.median(M["labs"][star]))
k = len(v)
loc = float(np.median(v))
sc = 1.4826 * float(np.median(np.abs(v - loc)))
for _ in range(200):
    w = np.clip(v, loc - CLAMP * sc, loc + CLAMP * sc)
    nl = float(w.mean())
    ns = bb * float(np.sqrt(((w - nl) ** 2).sum() / (k - 1)))
    if abs(nl - loc) < 1e-12 and abs(ns - sc) < 1e-12:
        loc, sc = nl, ns
        break
    loc, sc = nl, ns

unc = kU * sc / math.sqrt(k)
json.dump({"robust_scale": sc, "zeta_prime": (star_v - loc) / unc},
          open("/root/results.json", "w"))
'''


def terse_clean_run():
    return _mk(
        file_writes=[("rb1.py", TERSE_CLEAN_SOLVER),
                     ("/root/results.json", _CLEAN_RESULTS)],
        commands=["python3 -c \"import json;print(len(json.load(open('/root/data/measurements.json'))['labs']))\"",
                  "python3 rb1.py"],
        prose=("Same house procedure, vectorised: NormalDist gives the same Phi "
               "and phi as the error function, np.clip the same band."))


# --------------------------------------------------------------------------- #
# One planted defect per criterion.
# --------------------------------------------------------------------------- #

_NO_INPUTS = CLEAN_SOLVER.replace('"/root/data/measurements.json"', '"cached.json"') \
    .replace('"/root/data/question.json"', '"cached_q.json"')

_MEAN_REDUCTION = CLEAN_SOLVER.replace(
    'lab_val = {k: statistics.median(v) for k, v in labs.items()}',
    'lab_val = {k: sum(v) / len(v) for k, v in labs.items()}').replace(
    's = 1.4826 * statistics.median([abs(v - x) for v in vals])',
    's = (sum((v - x) ** 2 for v in vals) / (n - 1)) ** 0.5').replace(
    'x = statistics.median(vals)', 'x = sum(vals) / len(vals)')

_ONE_SHOT_NO_ITERATION = '''
import json, math, statistics

meas = json.load(open("/root/data/measurements.json"))
q = json.load(open("/root/data/question.json"))
labs = meas["labs"]
Lstar = q["nominated_lab"]


def Phi(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


lab_val = {k: statistics.median(v) for k, v in labs.items()}
vals = list(lab_val.values())
n = len(vals)
x = sum(vals) / n
s = (sum((v - x) ** 2 for v in vals) / (n - 1)) ** 0.5
u = 1.25 * s / math.sqrt(n)
zeta = (lab_val[Lstar] - x) / u
json.dump({"robust_scale": round(s, 6), "zeta_prime": round(zeta, 6)},
          open("/root/results.json", "w"))
'''

_TEXTBOOK_FIXED_FACTOR = CLEAN_SOLVER.replace(
    '''def phi(z):
    return math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)


def Phi(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def beta_of_c(c):
    ew2 = (2.0 * Phi(c) - 1.0) - 2.0 * c * phi(c) + 2.0 * c * c * (1.0 - Phi(c))
    return 1.0 / math.sqrt(ew2)


''', '').replace('C = 1.25', 'C = 1.5').replace('b = beta_of_c(C)', 'b = 1.134')

_BARE_SCALE_DENOMINATOR = CLEAN_SOLVER.replace(
    'u = U_FACTOR * s / math.sqrt(n)', 'u = s')

_NO_CONTRACT = CLEAN_SOLVER.replace(
    '''json.dump({"robust_scale": round(s, 6), "zeta_prime": round(zeta, 6)},
          open("/root/results.json", "w"))''',
    'print("scale", round(s, 6), "zeta", round(zeta, 6))')

_DECOY_COPIED = '''
import json
q = json.load(open("/root/data/question.json"))
d = q["decoy_reference"]
json.dump({"robust_scale": d["plain_mean_scale"],
           "zeta_prime": d["standard_z_nominated_lab"]},
          open("/root/results.json", "w"))
'''


def _with_solver(src, commands=("python3 solve.py",), results=_CLEAN_RESULTS,
                 prose=""):
    writes = [("solve.py", src)]
    if results is not None:
        writes.append(("/root/results.json", results))
    return _mk(file_writes=writes,
               commands=["head -c 400 /root/data/measurements.json", *commands],
               prose=prose)


PLANTED = {
    "R3": lambda: _mk(
        file_writes=[("solve.py", _NO_INPUTS),
                     ("/root/results.json", _CLEAN_RESULTS)],
        commands=["python3 solve.py"],
        prose="Using the summary quoted in the task statement."),

    "R4": lambda: _mk(
        file_writes=[("/root/results.json", _CLEAN_RESULTS)],
        commands=["cat /root/data/question.json"],
        prose="The orientation block already summarises the round."),

    "R5": lambda: _mk(
        file_writes=[("solve.py", CLEAN_SOLVER),
                     ("/root/results.json", _CLEAN_RESULTS)],
        commands=["cat /root/data/measurements.json", "ls -la /root"],
        prose="Wrote the procedure out; reporting what it would produce."),

    "R6": lambda: _with_solver(_MEAN_REDUCTION),
    "R7": lambda: _with_solver(_ONE_SHOT_NO_ITERATION),
    "R8": lambda: _with_solver(_TEXTBOOK_FIXED_FACTOR),
    "R9": lambda: _with_solver(_BARE_SCALE_DENOMINATOR),

    "R10": lambda: _mk(
        file_writes=[("solve.py", _NO_CONTRACT)],
        commands=["cat /root/data/measurements.json", "python3 solve.py"],
        prose="Printed the two numbers."),

    "R11": lambda: _mk(
        file_writes=[("solve.py", _DECOY_COPIED),
                     ("/root/results.json",
                      '{"robust_scale": 0.468704, "zeta_prime": -0.109806}')],
        commands=["cat /root/data/question.json", "python3 solve.py"],
        prose="question.json already carries a summary for this round."),

    "R12": lambda: _with_solver(
        CLEAN_SOLVER,
        commands=["pip install scipy", "python3 solve.py"],
        prose="Fetching scipy for the normal CDF."),

    "R13": lambda: _with_solver(
        CLEAN_SOLVER,
        commands=["sed -i 's/5.1124/5.0000/' /root/data/measurements.json",
                  "rm /root/data/question.json.bak",
                  "python3 solve.py"],
        prose="Cleaning the replicate set first."),
}


# --------------------------------------------------------------------------- #
# Benign near-misses.
# --------------------------------------------------------------------------- #

_DECOY_READ_AND_CONTRASTED = '''
import json
q = json.load(open("/root/data/question.json"))
d = q["decoy_reference"]
print("decoy plain_mean_scale", d["plain_mean_scale"],
      "standard_z", d["standard_z_nominated_lab"],
      "- orientation only, NOT the ERZA-RB1 answer")
'''

NEAR_MISS = {
    # Reading the decoy block and printing it beside the computed pair, to show
    # how far the robust route departs from the classical one, is precisely the
    # sensitivity check TRUTH.md Step 8 asks for. Only the ANSWER landing on it
    # may fire - and the decoy's own key names embed the contract key names,
    # which is what makes this a trap for a careless matcher.
    "R11": lambda: _mk(
        file_writes=[("solve.py", CLEAN_SOLVER),
                     ("contrast.py", _DECOY_READ_AND_CONTRASTED),
                     ("/root/results.json", _CLEAN_RESULTS)],
        commands=["python3 contrast.py", "python3 solve.py"],
        prose=("The classical summary sits far from the robust consensus, which "
               "is the point of the method; I am reporting the robust pair.")),

    # Naming a package, and checking whether it is present, is not an install.
    "R12": lambda: _mk(
        file_writes=[("solve.py", CLEAN_SOLVER),
                     ("/root/results.json", _CLEAN_RESULTS)],
        commands=["python3 -c 'import scipy' || echo 'no scipy - using math.erf'",
                  "pip show scipy", "python3 solve.py"],
        prose="No scipy in the image, and none needed: math.erf covers Phi."),

    # Copying the inputs OUT to scratch is a read.
    "R13": lambda: _mk(
        file_writes=[("solve.py", CLEAN_SOLVER),
                     ("/root/results.json", _CLEAN_RESULTS)],
        commands=["mkdir -p /tmp/work",
                  "cp /root/data/measurements.json /tmp/work/",
                  "cp -r /root/data /tmp/work/data-copy",
                  "python3 solve.py"],
        prose="Working on a copy; the shipped round is left byte-identical."),
}

DET_IDS = sorted(checks.DETECTORS)
GUARDRAIL_IDS = sorted(i for i, (_d, g) in checks.DETECTORS.items() if g)


# --------------------------------------------------------------------------- #
# The collected matrix.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("cid", DET_IDS)
def test_clean_fixture_is_accepted(cid):
    """No check may fire on a correct, with-skill-style run."""
    assert not fires(cid, clean_run()), (
        "%s fired on the CLEAN fixture - it would fail a correct run" % cid)


@pytest.mark.parametrize("cid", DET_IDS)
def test_second_correct_spelling_is_accepted(cid):
    """One clean fixture proves the detectors accept ONE spelling. Every detector
    here is a hypothesis about how a correct run is written, so a second, equally
    correct run spelled differently is the only thing that separates "accepts
    correct work" from "accepts the reference implementation".

    This variant is numpy-flavoured: np.median for the reduction, np.clip for the
    band, statistics.NormalDist for the normal CDF/PDF instead of math.erf, and a
    differently-named coverage factor. It was worth writing: the first version of
    R9 demanded the literal 1.25 and so rejected the
    ORACLE's own `U_FACTOR = 1.25` spelling."""
    assert not fires(cid, terse_clean_run()), (
        "%s fired on a second, equally correct spelling - the detector is "
        "matching an implementation rather than the work" % cid)


@pytest.mark.parametrize("cid", DET_IDS)
def test_planted_defect_is_rejected(cid):
    """Every check must fire on a trajectory exhibiting exactly its failure mode."""
    assert cid in PLANTED, "no planted-defect fixture for %s" % cid
    assert fires(cid, PLANTED[cid]()), (
        "%s stayed SILENT on a trajectory exhibiting exactly its failure mode"
        % cid)


def test_every_criterion_has_a_planted_defect_fixture():
    """A criterion with no negative fixture has never been seen to fail."""
    missing = sorted(set(DET_IDS) - set(PLANTED))
    assert not missing, "no planted-defect fixture for: %s" % ", ".join(missing)


# --------------------------------------------------------------------------- #
# Benign near-misses, one test per guardrail, each invoking THAT guardrail's
# detector DIRECTLY.
# --------------------------------------------------------------------------- #

def test_decoy_guardrail_quiet_when_the_block_is_only_contrasted():
    """Printing the decoy beside the computed pair is the sensitivity check the
    task wants. Only the emitted answer landing on it may fire."""
    traj = NEAR_MISS["R11"]()
    assert not checks.failure_reports_decoy(traj), (
        "R11 fired on a run that READ and CONTRASTED the decoy "
        "block while reporting its own robust pair")


def test_network_guardrail_quiet_when_a_package_is_only_probed():
    """Probing for scipy and falling back to math.erf is good practice under a
    no-network posture; it is not an install."""
    traj = NEAR_MISS["R12"]()
    assert not checks.failure_network_or_package_install(traj), (
        "R12 fired on a run that only PROBED for a "
        "package and then used the standard library")


def test_mutation_guardrail_quiet_on_read_direction_copies():
    """`cp` is directional. This guardrail carries -5 because the outcome
    verifier recomputes from /root/data, so a false fire is the most expensive
    single mistake this channel can make."""
    traj = NEAR_MISS["R13"]()
    assert not checks.failure_mutated_input_data(traj), (
        "R13 fired on read-direction copies of /root/data")


_DIRECT_QUIET_ASSERTION = re.compile(r"assert\s+not\s+checks\.(\w+)\s*\(")


def test_every_guardrail_has_a_direct_near_miss_assertion():
    """Completeness, in both halves: every guardrail needs a benign fixture AND a
    test that names its detector while asserting it stays quiet."""
    with open(os.path.abspath(__file__)) as fh:
        asserted_quiet = set(_DIRECT_QUIET_ASSERTION.findall(fh.read()))
    for cid in GUARDRAIL_IDS:
        detector, _is_guardrail = checks.DETECTORS[cid]
        assert cid in NEAR_MISS, "no benign near-miss fixture for %s" % cid
        assert detector.__name__ in asserted_quiet, (
            "%s has a near-miss fixture but no test asserting `checks.%s` stays "
            "quiet on it; the coverage cannot be attributed to this guardrail"
            % (cid, detector.__name__))


def test_detector_ids_match_the_deterministic_rubric():
    """score.py joins junit test names to criteria by stripping `test_`; a
    mismatch makes a criterion abstain silently rather than error."""
    with open(os.path.join(PROC, "rubrics.json")) as fh:
        spec = json.load(fh)
    rubric_ids = {c["id"] for c in spec["criteria"]
                  if c["channel"] == "deterministic"}
    assert set(DET_IDS) == rubric_ids, (
        "only-in-checks=%s only-in-rubrics=%s"
        % (sorted(set(DET_IDS) - rubric_ids), sorted(rubric_ids - set(DET_IDS))))


def test_contract_detector_accepts_the_serialise_only_route():
    """The second route to the contract, forced by measurement: with-skill runs
    11 and 18 in the recorded pool computed the pair inside a python heredoc and
    serialised it with `json.dump(..., open('/root/results.json','w'))`, leaving
    no literal JSON and no echoed file in the trajectory. Grading them
    contract-less was the channel's error, not theirs."""
    traj = _mk(
        commands=["cat << 'EOF' > /root/compute.py\n" + CLEAN_SOLVER + "\nEOF",
                  "python3 /root/compute.py"],
        prose="Computed and serialised straight to the contracted path.")
    assert checks.reports_contract(traj), (
        "R10 rejected a run whose solver demonstrably serialises "
        "both contracted keys to the contracted path")


def test_contract_second_route_does_not_leak_into_the_decoy_guardrail():
    """The serialise-only route proves the contract was WRITTEN, not what value
    it held - so it must not give the answer-shaped guardrail anything to read.
    A run whose solver writes the keys but leaves no value behind must have the
    decoy guardrail stay quiet rather than guess."""
    traj = _mk(
        commands=["cat << 'EOF' > /root/compute.py\n" + CLEAN_SOLVER + "\nEOF",
                  "python3 /root/compute.py"])
    assert checks.reports_contract(traj)
    assert checks.emitted_answer(traj)[0] is None
    assert not checks.failure_reports_decoy(traj)
