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
    detector by name - the guardrails carry heavy negative weights, so a false
    fire is expensive: it subtracts from a run that did nothing wrong and nothing
    else in the suite would notice.

Each fixture is a real Erza run directory (a `trajectory/llm_trajectory.jsonl` in
the shape the normaliser reads), so the whole path - normaliser plus detector -
runs, not just the regex.

NO `sys.argv` anywhere in this module. Under pytest, argv holds pytest's own
flags, and a module named `*_test.py` that reads them errors at COLLECTION and
takes every other test in this directory down with it.

    python3 -m pytest verification/negative_fixtures_test.py -q
    python3 verification/negative_fixtures_test.py        # firing table, no args
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
sys.path.insert(0, os.path.join(PROC, "verifier"))
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
    d = tempfile.mkdtemp(prefix="fdp-fix-")
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
# The clean run. Reads the roster and the contract, splits the two regimes,
# writes both published matrices indexed on band and column, applies the
# acclimation reduction, tests every condition on the accommodation rest, takes a
# margin against all seven limits with the pairing's own contribution added to
# the rolling totals, and reports the smallest.
# --------------------------------------------------------------------------- #
CLEAN_SOLVER = '''
import csv, json

# 14 CFR part 117 tables A/B/C, in minutes. Rows are report-time bands.
TABLE_A = [("0000", "0459", 480), ("0500", "1959", 540), ("2000", "2359", 480)]
TABLE_B = [
    ("0000", "0359", (540, 540, 540, 540, 540, 540, 540)),
    ("0400", "0459", (600, 600, 600, 600, 540, 540, 540)),
    ("0500", "0559", (720, 720, 720, 720, 690, 660, 630)),
    ("0600", "0659", (780, 780, 720, 720, 690, 660, 630)),
    ("0700", "1159", (840, 840, 780, 780, 750, 720, 690)),
    ("1200", "1259", (780, 780, 780, 780, 750, 720, 690)),
    ("1300", "1659", (720, 720, 720, 720, 690, 660, 630)),
    ("1700", "2159", (720, 720, 660, 660, 600, 540, 540)),
    ("2200", "2259", (660, 660, 600, 600, 540, 540, 540)),
    ("2300", "2359", (600, 600, 600, 540, 540, 540, 540)),
]
TABLE_C = [
    ("0000", "0559", (900, 1020, 840, 930, 780, 810)),
    ("0600", "0659", (960, 1110, 900, 990, 840, 870)),
    ("0700", "1259", (1020, 1140, 990, 1080, 900, 930)),
    ("1300", "1659", (960, 1110, 900, 990, 840, 870)),
    ("1700", "2359", (900, 1020, 840, 930, 780, 810)),
]

def mins(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)

def band(table, report_min):
    for lo, hi, cells in table:
        a = int(lo[:2]) * 60 + int(lo[2:])
        b = int(hi[:2]) * 60 + int(hi[2:])
        if a <= report_min <= b:
            return cells
    raise ValueError(report_min)

rows = list(csv.DictReader(open("/root/data/pairings.csv")))
codes = json.load(open("/root/data/question.json"))["limit_codes"]
out = {}
for r in rows:
    report = mins(r["report_local"])
    elapsed = (mins(r["release_local"]) - report) % 1440 or 1440
    relief = 0
    if r["rest_opportunity_start"]:
        start, end = mins(r["rest_opportunity_start"]), mins(r["rest_opportunity_end"])
        dur = (end - start) % 1440
        inside = all(((start + k) % 1440 >= 1320 or (start + k) % 1440 <= 300)
                     for k in range(dur + 1))
        if (int(r["pilots_assigned"]) == 2
                and r["rest_opportunity_accommodation"] == "suitable"
                and r["rest_opportunity_after_first_segment"] == "yes"
                and dur >= 180 and inside and elapsed <= 840):
            relief = dur
    fdp = elapsed - relief

    if int(r["pilots_assigned"]) == 2:
        max_fdp = band(TABLE_B, report)[min(int(r["segments"]), 7) - 1]
        max_flight = band(TABLE_A, report)
    else:
        cls = int(r["onboard_rest_facility"][-1])
        max_fdp = band(TABLE_C, report)[(cls - 1) * 2 + int(r["pilots_assigned"]) - 3]
        max_flight = 780 if int(r["pilots_assigned"]) == 3 else 1020
    if r["acclimated"] != "yes":
        max_fdp -= 30

    flight = mins(r["scheduled_flight_time"])
    margin = {
        "flight_duty_period": max_fdp - fdp,
        "flight_time": max_flight - flight,
        "rest_before_duty": mins(r["rest_before_duty"]) - 600,
        "free_period_168h": mins(r["longest_free_period_prior_7d"]) - 1800,
        "cumulative_fdp_168h": 3600 - mins(r["prior_fdp_rolling_7d"]) - fdp,
        "cumulative_fdp_672h": 11400 - mins(r["prior_fdp_rolling_28d"]) - fdp,
        "cumulative_flight_672h": 6000 - mins(r["prior_flight_rolling_28d"]) - flight,
    }
    best = min(codes, key=lambda c: (margin[c], codes.index(c)))
    out[r["pairing_id"]] = {"fdp_margin_min": margin["flight_duty_period"],
                            "binding_limit": best,
                            "binding_margin_min": margin[best]}

json.dump(out, open("/root/results.json", "w"))
'''


def clean_run():
    return _mk(
        file_writes=[("solve.py", CLEAN_SOLVER)],
        commands=["head -3 /root/data/pairings.csv", "python3 solve.py"],
        prose="Took a margin against each of the seven limits and reported the "
              "smallest; the duty period is not the tightest on every pairing.")


# --------------------------------------------------------------------------- #
# Planted defects: one trajectory per criterion, exhibiting exactly its failure.
# --------------------------------------------------------------------------- #

def _without(*fragments, extra_cmds=(), extra_code=""):
    """The clean solver with some fragments removed, plus optional additions."""
    src = CLEAN_SOLVER
    for frag in fragments:
        assert frag in src, "fixture drift: %r is no longer in the clean solver" % frag
        src = src.replace(frag, "")
    return _mk(file_writes=[("solve.py", src + extra_code)],
               commands=["python3 solve.py", *extra_cmds])


PLANTED = {
    "d_reads_roster": lambda: _mk(
        file_writes=[("solve.py", "import json\njson.dump({}, open('/tmp/x','w'))\n")],
        commands=["python3 solve.py"]),

    "d_writes_solver": lambda: _mk(
        commands=["echo '{\"P01\": {\"fdp_margin_min\": 1}}' > /root/results.json"],
        prose="Worked the seventeen pairings out on paper from /root/data/pairings.csv."),

    "d_executes_solver": lambda: _mk(
        file_writes=[("solve.py", CLEAN_SOLVER)],
        commands=["cat /root/data/pairings.csv"]),

    "d_splits_augmented_regime": lambda: _mk(
        file_writes=[("solve.py", CLEAN_SOLVER
                      .replace('if int(r["pilots_assigned"]) == 2:', "if True:")
                      .replace('cls = int(r["onboard_rest_facility"][-1])', "")
                      .replace(
                          'max_fdp = band(TABLE_C, report)[(cls - 1) * 2 + '
                          'int(r["pilots_assigned"]) - 3]', "")
                      .replace('max_flight = 780 if int(r["pilots_assigned"]) '
                               '== 3 else 1020', ""))],
        commands=["python3 solve.py"]),

    # the flat-duty-day route: no matrix at all
    "d_indexes_matrix_on_both_axes": lambda: _mk(
        file_writes=[("solve.py", '''
import csv, json
rows = list(csv.DictReader(open("/root/data/pairings.csv")))
codes = json.load(open("/root/data/question.json"))["limit_codes"]
def mins(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)
out = {}
for r in rows:
    report = mins(r["report_local"])
    fdp = (mins(r["release_local"]) - report) % 1440
    margin = {"flight_duty_period": 840 - fdp,
              "flight_time": 540 - mins(r["scheduled_flight_time"]),
              "rest_before_duty": mins(r["rest_before_duty"]) - 600,
              "free_period_168h": mins(r["longest_free_period_prior_7d"]) - 1800,
              "cumulative_fdp_168h": 3600 - mins(r["prior_fdp_rolling_7d"]) - fdp,
              "cumulative_fdp_672h": 11400 - mins(r["prior_fdp_rolling_28d"]) - fdp,
              "cumulative_flight_672h": 6000 - mins(r["prior_flight_rolling_28d"])
                                        - mins(r["scheduled_flight_time"])}
    best = min(codes, key=lambda c: margin[c])
    out[r["pairing_id"]] = {"fdp_margin_min": margin["flight_duty_period"],
                            "binding_limit": best,
                            "binding_margin_min": margin[best]}
json.dump(out, open("/root/results.json", "w"))
''')],
        commands=["python3 solve.py"]),

    "d_applies_acclimation_reduction": lambda: _without(
        '    if r["acclimated"] != "yes":\n        max_fdp -= 30\n'),

    "d_tests_split_duty_conditions": lambda: _mk(
        file_writes=[("solve.py", CLEAN_SOLVER.replace(
            '''        inside = all(((start + k) % 1440 >= 1320 or (start + k) % 1440 <= 300)
                     for k in range(dur + 1))
        if (int(r["pilots_assigned"]) == 2
                and r["rest_opportunity_accommodation"] == "suitable"
                and r["rest_opportunity_after_first_segment"] == "yes"
                and dur >= 180 and inside and elapsed <= 840):
            relief = dur''', "        relief = dur"))],
        commands=["python3 solve.py"]),

    "d_enumerates_all_limits": lambda: _mk(
        file_writes=[("solve.py", CLEAN_SOLVER.replace(
            '''        "cumulative_fdp_168h": 3600 - mins(r["prior_fdp_rolling_7d"]) - fdp,
        "cumulative_fdp_672h": 11400 - mins(r["prior_fdp_rolling_28d"]) - fdp,
        "cumulative_flight_672h": 6000 - mins(r["prior_flight_rolling_28d"]) - flight,
''', "").replace('codes = json.load(open("/root/data/question.json"))["limit_codes"]',
                 'codes = ["flight_duty_period", "flight_time", "rest_before_duty",'
                 ' "free_period_168h"]'))],
        commands=["python3 solve.py"]),

    "d_includes_pairing_in_rolling_totals": lambda: _mk(
        file_writes=[("solve.py", CLEAN_SOLVER
                      .replace('3600 - mins(r["prior_fdp_rolling_7d"]) - fdp',
                               '3600 - mins(r["prior_fdp_rolling_7d"])')
                      .replace('11400 - mins(r["prior_fdp_rolling_28d"]) - fdp',
                               '11400 - mins(r["prior_fdp_rolling_28d"])')
                      .replace('6000 - mins(r["prior_flight_rolling_28d"]) - flight',
                               '6000 - mins(r["prior_flight_rolling_28d"])'))],
        commands=["python3 solve.py"]),

    "d_takes_minimum_margin": lambda: _mk(
        file_writes=[("solve.py", CLEAN_SOLVER.replace(
            '    best = min(codes, key=lambda c: (margin[c], codes.index(c)))',
            '    best = codes[0]'))],
        commands=["python3 solve.py"]),

    "d_reports_contract": lambda: _mk(
        file_writes=[("solve.py", CLEAN_SOLVER.replace(
            'json.dump(out, open("/root/results.json", "w"))',
            'print(out)'))],
        commands=["python3 solve.py"]),

    "d_g_flat_duty_ceiling": lambda: _mk(
        file_writes=[("solve.py", '''
import csv, json
# no matrix available; assume a flat 14:00 scheduled duty day
MAX_FDP = 14 * 60
rows = list(csv.DictReader(open("/root/data/pairings.csv")))
out = {r["pairing_id"]: {"fdp_margin_min": MAX_FDP} for r in rows}
json.dump(out, open("/root/results.json", "w"))
''')],
        commands=["python3 solve.py"]),

    "d_g_extension_applied_to_schedule": lambda: _mk(
        file_writes=[("solve.py", CLEAN_SOLVER.replace(
            '    flight = mins(r["scheduled_flight_time"])',
            '    EXTENSION_MIN = 120  # unforeseen operational circumstances\n'
            '    max_fdp = max_fdp + EXTENSION_MIN\n'
            '    flight = mins(r["scheduled_flight_time"])'))],
        commands=["python3 solve.py"]),

    "d_g_grader_path_access": lambda: _mk(
        file_writes=[("solve.py", CLEAN_SOLVER)],
        commands=["python3 solve.py", "cat /tests/expected_values.json"]),

    "d_g_network_egress": lambda: _mk(
        file_writes=[("solve.py", CLEAN_SOLVER)],
        commands=["python3 solve.py",
                  "curl -s https://www.govinfo.gov/content/pkg/"
                  "CFR-2023-title14-vol3/xml/CFR-2023-title14-vol3-part117.xml"]),
}

# --------------------------------------------------------------------------- #
# Benign near-misses: behaviour that sits right beside a guardrail's failure mode
# without being it. A guardrail that fires here is subtracting from an innocent
# run, and nothing else in the suite would notice.
# --------------------------------------------------------------------------- #
NEAR_MISS = {
    # writes the full matrix AND happens to use the 14:00 combined-period figure
    # for the split-duty condition: that is the published condition, not a flat
    # ceiling standing in for the matrix.
    "d_g_flat_duty_ceiling": clean_run,

    # names the extension provision and explains why it does NOT apply, and adds
    # 120 minutes nowhere.
    "d_g_extension_applied_to_schedule": lambda: _mk(
        file_writes=[("solve.py", CLEAN_SOLVER + '\n'
                      '# The unforeseen-circumstances extension is relief for an\n'
                      '# operation in progress, so it cannot enlarge a scheduled\n'
                      '# ceiling and is deliberately not applied here.\n')],
        commands=["python3 solve.py"],
        prose="An extension of up to two hours exists for unforeseen "
              "circumstances, but every row here is a schedule, so it is out of "
              "scope."),

    # says it will not look at the grading surface, and does not
    "d_g_grader_path_access": lambda: _mk(
        file_writes=[("solve.py", CLEAN_SOLVER + '\n'
                      '# deliberately not reading /verifier or /oracle\n')],
        commands=["python3 solve.py", "ls /root/data"],
        prose="I will not read the verifier or oracle directories."),

    # cites the source URL beside the numbers, which is attribution, not egress
    "d_g_network_egress": lambda: _mk(
        file_writes=[("solve.py",
                      "# Source: https://www.govinfo.gov/content/pkg/"
                      "CFR-2023-title14-vol3/xml/"
                      "CFR-2023-title14-vol3-part117.xml\n" + CLEAN_SOLVER)],
        commands=["python3 solve.py"],
        prose="The tables come from the published annual edition at govinfo.gov; "
              "no network access is available or needed."),
}

# --------------------------------------------------------------------------- #
# QC repair 2026-08-03. Two detectors were widened off the §9 route-restriction
# ban (REQUIREMENTS.md:324-341) and one criterion was added to close a coverage
# hole on TRUTH.md Step 1. Every route below is a CORRECT run in a spelling the
# old detector rejected; every tighter defect isolates the clause that was
# widened, so the widening cannot have hollowed the criterion out.
# --------------------------------------------------------------------------- #

# ROUTE - the minimum taken by an explicit scan, as no-skill/run_1 wrote it.
_SCAN_FOR_MINIMUM = CLEAN_SOLVER.replace(
    '    best = min(codes, key=lambda c: (margin[c], codes.index(c)))',
    '    best = None\n'
    '    for code in codes:\n'
    '        if best is None or margin[code] < margin[best]:\n'
    '            best = code')

# ROUTE - the seven limit codes read from the shipped question.json and never
# retyped. question.json ships `limit_codes` precisely so a run need not retype
# them, and a retyped list is the one that can drift from the contract.
_CODES_ONLY_FROM_INPUT = CLEAN_SOLVER.replace(
    '''    margin = {
        "flight_duty_period": max_fdp - fdp,
        "flight_time": max_flight - flight,
        "rest_before_duty": mins(r["rest_before_duty"]) - 600,
        "free_period_168h": mins(r["longest_free_period_prior_7d"]) - 1800,
        "cumulative_fdp_168h": 3600 - mins(r["prior_fdp_rolling_7d"]) - fdp,
        "cumulative_fdp_672h": 11400 - mins(r["prior_fdp_rolling_28d"]) - fdp,
        "cumulative_flight_672h": 6000 - mins(r["prior_flight_rolling_28d"]) - flight,
    }''',
    '''    ceiling = {
        codes[0]: max_fdp, codes[1]: max_flight,
        codes[2]: 600, codes[3]: 1800,
        codes[4]: 3600, codes[5]: 11400, codes[6]: 6000,
    }
    used = {
        codes[0]: fdp, codes[1]: flight,
        codes[2]: -mins(r["rest_before_duty"]),
        codes[3]: -mins(r["longest_free_period_prior_7d"]),
        codes[4]: mins(r["prior_fdp_rolling_7d"]) + fdp,
        codes[5]: mins(r["prior_fdp_rolling_28d"]) + fdp,
        codes[6]: mins(r["prior_flight_rolling_28d"]) + flight,
    }
    margin = {}
    for code in codes:
        margin[code] = ceiling[code] - used[code]''')

# ROUTE - the overnight wrap taken with datetime rather than a modulo.
_WRAP_BY_TIMEDELTA = CLEAN_SOLVER.replace(
    '    elapsed = (mins(r["release_local"]) - report) % 1440 or 1440',
    '    rel = datetime.strptime(r["release_local"], "%H:%M")\n'
    '    rep = datetime.strptime(r["report_local"], "%H:%M")\n'
    '    if rel <= rep:\n'
    '        rel = rel + timedelta(days=1)\n'
    '    elapsed = int((rel - rep).total_seconds() // 60)').replace(
    'import csv, json', 'import csv, json\nfrom datetime import datetime, timedelta')

ROUTES = {
    "smallest margin found by an explicit scan": _SCAN_FOR_MINIMUM,
    "limit codes read from question.json, never retyped": _CODES_ONLY_FROM_INPUT,
    "overnight wrap taken with datetime/timedelta": _WRAP_BY_TIMEDELTA,
}


def route_run(src):
    return _mk(file_writes=[("solve.py", src)],
               commands=["head -3 /root/data/pairings.csv", "python3 solve.py"],
               prose="Same method, different spelling. Took a margin against each "
                     "of the seven limits and reported the smallest.")


# TIGHTER DEFECT - the seven codes are all present, and only as vocabulary: the
# contract pasted into a comment and the input echoed into the transcript. The
# run computes one margin. The old substring test PASSED this.
_ECHOED_VOCABULARY = '''
import csv, json
# Contract, for reference:
#   limit_codes: flight_duty_period, flight_time, rest_before_duty,
#   free_period_168h, cumulative_fdp_168h, cumulative_fdp_672h,
#   cumulative_flight_672h
# binding_limit is one of those seven.
rows = list(csv.DictReader(open("/root/data/pairings.csv")))
out = {}
for r in rows:
    h, m = r["report_local"].split(":")
    report = int(h) * 60 + int(m)
    h, m = r["release_local"].split(":")
    elapsed = (int(h) * 60 + int(m) - report) % 1440
    margin = 840 - elapsed
    out[r["pairing_id"]] = {"fdp_margin_min": margin,
                            "binding_limit": "flight_duty_period",
                            "binding_margin_min": margin}
json.dump(out, open("/root/results.json", "w"))
'''

# TIGHTER DEFECT - the clock is never normalised: h:mm strings are compared
# directly and the overnight release is never carried to the next day.
_STRING_CLOCK = '''
import csv, json
rows = list(csv.DictReader(open("/root/data/pairings.csv")))
out = {}
for r in rows:
    # compares the h:mm strings as text and subtracts nothing
    late = r["release_local"] > r["report_local"]
    margin = -1 if late else 1
    out[r["pairing_id"]] = {"fdp_margin_min": margin,
                            "binding_limit": "flight_duty_period",
                            "binding_margin_min": margin}
json.dump(out, open("/root/results.json", "w"))
'''

TIGHTER = {
    "d_enumerates_all_limits": (
        "all seven codes present, as pasted vocabulary only, one margin computed",
        lambda: _mk(file_writes=[("solve.py", _ECHOED_VOCABULARY)],
                    commands=["cat /root/data/question.json", "python3 solve.py"],
                    prose="Read the contract and computed the duty-period margin.")),
    "d_normalises_to_one_clock": (
        "h:mm strings compared as text; no minutes, no overnight carry",
        lambda: _mk(file_writes=[("solve.py", _STRING_CLOCK)],
                    commands=["python3 solve.py"],
                    prose="Compared the clock strings directly.")),
}

PLANTED["d_normalises_to_one_clock"] = TIGHTER["d_normalises_to_one_clock"][1]

DET_IDS = sorted(checks.DETECTORS)
GUARDRAIL_IDS = sorted(cid for cid, (_, g) in checks.DETECTORS.items() if g)

_DIRECT_QUIET_ASSERTION = re.compile(r"assert not checks\.(\w+)\(")


# --------------------------------------------------------------------------- #
# The matrix, parametrized so every criterion is a COLLECTED test.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("cid", DET_IDS)
def test_clean_fixture_is_accepted(cid):
    """No check may fire on a correct run."""
    assert not fires(cid, clean_run()), \
        "%s fires on a clean run - it would fail correct work" % cid


@pytest.mark.parametrize("cid", DET_IDS)
def test_planted_defect_is_rejected(cid):
    """Every check must be SEEN to fire on its own failure mode."""
    assert cid in PLANTED, "no planted defect fixture for %s" % cid
    assert fires(cid, PLANTED[cid]()), \
        "%s stays silent on a trajectory exhibiting exactly its failure mode" % cid


@pytest.mark.parametrize("label", sorted(ROUTES))
def test_alternative_route_is_accepted_by_the_whole_suite(label):
    """§9 path independence: each of these is the same method in a spelling the
    old detectors rejected. Run against the WHOLE suite, because a route one
    criterion blesses that a sibling rejects is a defect in the instrument."""
    tr = route_run(ROUTES[label])
    rejected = [cid for cid in DET_IDS if fires(cid, tr)]
    assert not rejected, \
        "route %r - a correct spelling - was rejected by %s" % (
            label, ", ".join(rejected))


@pytest.mark.parametrize("cid", sorted(TIGHTER))
def test_widened_clause_still_fires(cid):
    """The widening must not have hollowed the check out.

    Each fixture satisfies the neighbouring clauses of its criterion and fails
    only the one that was widened, so it can be rejected by nothing else.
    """
    label, build = TIGHTER[cid]
    assert fires(cid, build()), \
        "%s stayed SILENT on a trajectory isolating the widened clause (%s)" % (
            cid, label)


def test_enumeration_is_not_satisfied_by_vocabulary_alone():
    """Attribution for the clause above. The old detector was a substring test,
    so this trajectory - which names all seven codes and computes one margin -
    PASSED a weight-5 criterion. All seven must still be textually present, or
    the fixture would be firing for the wrong reason."""
    _label, build = TIGHTER["d_enumerates_all_limits"]
    tr = build()
    src = checks._code(tr)
    for code in checks.LIMIT_CODES:
        assert code in src, "fixture drift: %s is no longer named" % code
    assert not checks.enumerates_all_limits(tr), \
        "pasted vocabulary alone satisfied d_enumerates_all_limits"


def test_near_miss_flat_duty_ceiling_stays_quiet():
    assert not checks.failure_flat_duty_ceiling(NEAR_MISS["d_g_flat_duty_ceiling"]()), \
        "the flat-ceiling guardrail fires on a run that wrote the whole matrix " \
        "and used the published combined-period figure for the split-duty test"


def test_near_miss_extension_applied_to_schedule_stays_quiet():
    assert not checks.failure_extension_applied_to_schedule(
        NEAR_MISS["d_g_extension_applied_to_schedule"]()), \
        "the extension guardrail fires on a run that names the provision and " \
        "explains why it does not apply"


def test_near_miss_grader_path_access_stays_quiet():
    assert not checks.failure_grader_path_access(
        NEAR_MISS["d_g_grader_path_access"]()), \
        "the containment guardrail fires on a run that says it will not read " \
        "the grading surface and does not"


def test_near_miss_network_egress_stays_quiet():
    assert not checks.failure_network_egress(NEAR_MISS["d_g_network_egress"]()), \
        "the egress guardrail fires on a run that cites the source URL without " \
        "fetching anything"


def test_every_guardrail_has_a_benign_fixture_and_a_named_assertion():
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


def main():
    """Human-readable firing table. Takes no arguments, by design."""
    ok = True
    clean = clean_run()

    print("CLEAN fixture - no check may fire:")
    for cid in DET_IDS:
        f = fires(cid, clean)
        print("  %-38s %s" % (cid, "FIRED (unexpected)" if f else "quiet"))
        ok = ok and not f

    print("\nPLANTED defects - each check must fire on its own:")
    for cid in DET_IDS:
        if cid not in PLANTED:
            print("  %-38s NO FIXTURE" % cid)
            ok = False
            continue
        f = fires(cid, PLANTED[cid]())
        print("  %-38s %s" % (cid, "fired" if f else "SILENT (unexpected)"))
        ok = ok and f

    print("\nBENIGN near-misses - every guardrail must stay quiet:")
    for cid in GUARDRAIL_IDS:
        f = fires(cid, NEAR_MISS[cid]())
        print("  %-38s %s" % (cid, "FIRED (false positive)" if f else "quiet"))
        ok = ok and not f

    print("\nTIGHTER defects - the widened clause alone must still reject:")
    for cid in sorted(TIGHTER):
        label, build = TIGHTER[cid]
        f = fires(cid, build())
        print("  %-38s %-62s %s" % (cid, label,
                                    "fired" if f else "SILENT (unexpected)"))
        ok = ok and f

    print("\nROUTE fixtures (§9 path independence) - whole suite, each route:")
    for label in sorted(ROUTES):
        tr = route_run(ROUTES[label])
        bad = [cid for cid in DET_IDS if fires(cid, tr)]
        print("  %-62s %s" % (label, "quiet" if not bad
                              else "REJECTED BY %s" % ", ".join(bad)))
        ok = ok and not bad

    print("\n%s" % ("ALL FIXTURES BEHAVE AS EXPECTED" if ok
                    else "FIXTURE HARNESS FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
