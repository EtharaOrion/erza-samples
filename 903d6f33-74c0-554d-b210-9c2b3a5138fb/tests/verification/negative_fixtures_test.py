"""Negative-fixture matrix: both halves of every deterministic criterion, as
COLLECTED pytest tests.

"A test you have never seen fail is not a test; a guardrail you have never seen
stay quiet under temptation is not a guardrail."

The fixtures themselves are not new - `make_fixtures.py` has built them since the
verifier was authored, and `run_fixtures.py` prints a table from them. What was
missing is that nothing the TEST RUNNER runs consulted them: the matrix lived in
two scripts that had to be remembered, run in the right order, with a
`/tmp/fixmap.json` handed between them, so `pytest verification` collected zero
tests and the mutual-exclusivity / negative-fixture arm of the suite passed
vacuously. This module reuses that machinery in-process:

  * `test_good_fixture_is_accepted[<id>]`      - no criterion may fire on the
    correct run (adapted from `truth_armed/golden_run`; see `make_fixtures.CORRECT`)
  * `test_planted_defect_fires[<fixture>]`     - every firing fixture must trip
    the criterion it names
  * `test_benign_near_miss_stays_quiet[<fixture>]` - every `!`-prefixed control
    must leave its named guardrail quiet
  * one written-out near-miss test per guardrail, naming that guardrail's graded
    function, so the coverage can be attributed to it
  * completeness: every deterministic criterion has a firing fixture, and every
    guardrail has a quiet one

Each fixture is a real Erza run directory (a `trajectory/llm_trajectory.jsonl` in
the shape the normaliser reads), so the whole path - normaliser plus criterion -
runs, not just the regex.

WHY THE CRITERIA ARE IMPORTED, NEVER COPIED. This bundle's deterministic channel
has no `checks.py` registry: each criterion IS the pytest function
`verifier/test_trajectory.py::test_<id>`. This module imports that module at RUN
time and calls those functions, resolving their pytest fixtures (`traj`, `code`,
`everything`) through the module's own fixture definitions. Re-implementing a
detector here would mean the fixtures bind a copy, and the graded criterion could
drift away from them unnoticed - which is the failure mode this file exists to
prevent. It also means these tests need no subprocess: `run_fixtures.py` spawns
one pytest per fixture, which is why it costs seconds per row.

THE `o_*` CRITERIA ARE UNEVALUATED HERE, BY DESIGN. The outcome channel decides
its two criteria by reconstructing the run's solver and RE-EXECUTING it against
the shipped inputs. A synthetic trajectory cannot exhibit "the probe re-derived an
answer outside tolerance" without carrying a whole working solver, and what that
would then test is the arithmetic, not the criterion. They are listed in
`UNEVALUATED` and excluded from the matrix, the way the sibling suites' registries
carry deterministic ids only. (`run_fixtures.py` reports them as collateral on the
two fixtures that author nothing at all; that is the outcome channel's own
fail-closed reading of "the agent produced nothing", not a fixture for it.)

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
GOLDEN_RUN = os.path.join(PROC, "truth_armed", "golden_run")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(PROC, "lib"))
sys.path.insert(0, PROC)
import trajectory as T  # noqa: E402

import make_fixtures as MF  # noqa: E402


# --------------------------------------------------------------------------- #
# calling the graded criteria                                                  #
# --------------------------------------------------------------------------- #

def _criteria_module():
    """The graded deterministic channel, imported at RUN time.

    Imported here rather than at module scope so that an edit landing in
    `verifier/test_trajectory.py` while this suite runs cannot half-import it: a
    failed import is retried once after `invalidate_caches()`, which is what a
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

    pytest 8 wraps the function in `__pytest_wrapped__`; pytest 9 replaces it with
    a `FixtureFunctionDefinition` exposing `_get_wrapped_function()`. Calling the
    decorated object directly is an error in both.
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

    The criteria take `traj` and the module's own derived views: `code`
    (`agent_code` with comments and docstrings stripped, which is what the
    behavioural criteria read) and `everything` (code plus prose, deliberately
    unstripped, which only the narration-tier criteria read). Building those views
    from the module's fixture definitions - rather than restating them - is what
    keeps this suite honest: if the graded `code` view changes, these fixtures see
    the change.
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
# loading make_fixtures' runs, without shelling out                            #
# --------------------------------------------------------------------------- #

_TMP: list = []


def _load(rec):
    """Materialise one `make_fixtures` record and load it through the normaliser."""
    d = tempfile.mkdtemp(prefix="wcs-fix-")
    _TMP.append(d)
    return T.load(MF.write_run(d, rec))


@atexit.register
def _cleanup():
    for d in _TMP:
        shutil.rmtree(d, ignore_errors=True)


def good_run():
    """The correct run, condensed from `truth_armed/golden_run`.

    NOT `make_fixtures.GOOD`, which is the skeleton the negative cases mutate and
    deliberately fails `R7` - that is what makes `no_lonpole_name` a
    fixture. Using the skeleton as the clean control would assert that a criterion
    fires and does not fire on the same trajectory.
    """
    return _load(MF.correct_record())


def case_run(name):
    return _load(MF.case_record(name))


def target_of(name):
    """The criterion a fixture is about, and whether it must fire or stay quiet."""
    target = MF.CASES[name][2]
    return target.lstrip("!"), not target.startswith("!")


FIRING = [n for n in MF.CASES if not MF.CASES[n][2].startswith("!")]
QUIET = [n for n in MF.CASES if MF.CASES[n][2].startswith("!")]


# --------------------------------------------------------------------------- #
# the criterion inventory, read off the rubric                                 #
# --------------------------------------------------------------------------- #

with open(os.path.join(PROC, "rubrics.json")) as _fh:
    _SPEC = json.load(_fh)

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


# --------------------------------------------------------------------------- #
# the collected matrix                                                         #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("cid", DET_IDS)
def test_good_fixture_is_accepted(cid):
    """No criterion may fire on the correct run. A criterion that always fires
    would fail a correct run and is worse than no criterion."""
    assert not fires(cid, good_run()), (
        "%s fired on the CORRECT fixture - it would fail a correct run" % cid)


@pytest.mark.parametrize("name", FIRING)
def test_planted_defect_fires(name):
    """Every firing fixture must trip the criterion it names."""
    cid, _must_fire = target_of(name)
    assert fires(cid, case_run(name)), (
        "%s stayed SILENT on fixture %r, which exhibits exactly its failure mode"
        % (cid, name))


@pytest.mark.parametrize("name", QUIET)
def test_benign_near_miss_stays_quiet(name):
    """Every `!` control must leave its named guardrail quiet. These guardrails
    carry negative weight, so a false fire silently subtracts from a run that did
    nothing wrong."""
    cid, _must_fire = target_of(name)
    assert not fires(cid, case_run(name)), (
        "%s FIRED on benign fixture %r - it would charge a correct run" % (cid, name))


def test_every_criterion_has_a_firing_fixture():
    """A criterion with no negative fixture has never been seen to fail."""
    covered = {target_of(n)[0] for n in FIRING}
    missing = sorted(set(DET_IDS) - covered)
    assert not missing, "no firing fixture for: %s" % ", ".join(missing)


def test_every_guardrail_has_a_quiet_fixture():
    """And a guardrail with no benign control has never been seen to stay quiet."""
    covered = {target_of(n)[0] for n in QUIET}
    missing = sorted(set(GUARDRAIL_IDS) - covered)
    assert not missing, "no benign near-miss fixture for: %s" % ", ".join(missing)


def test_fixture_targets_are_real_criteria():
    """A fixture naming a criterion that no longer exists tests nothing, and
    `run_fixtures.py` would report it as passing (its target never appears in the
    failure set, so a QUIET expectation is trivially met)."""
    unknown = sorted({target_of(n)[0] for n in MF.CASES} - set(DET_IDS))
    assert not unknown, "fixtures target non-existent criteria: %s" % ", ".join(unknown)


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


def test_the_skeleton_is_not_mistaken_for_a_correct_run():
    """`make_fixtures.GOOD` is a mutation base, not a clean control.

    It carries `phi_p = 180.0` with nothing tying the symbol to the convention it
    comes from, which is exactly the failure `R7` records - and is
    why `no_lonpole_name` uses it unmutated. Pinned here so a later edit that
    "fixes" the skeleton cannot silently turn one of the fixtures into a copy of
    the clean run.
    """
    skeleton = _load(MF.record(code=MF.GOOD, commands=["python3 solve.py"]))
    assert fires("R7", skeleton), (
        "make_fixtures.GOOD now names the convention; the no_lonpole_name "
        "fixture no longer exhibits its failure mode")
    assert not fires("R6", skeleton), (
        "make_fixtures.GOOD no longer applies the rotation; every negative "
        "fixture mutated from it now fails the weight-5 gate collaterally")


def test_the_golden_run_itself_is_all_green():
    """The recorded oracle-armed golden trajectory, graded directly.

    The correct fixture is a condensation of this run, and a condensation can
    drift from what it condenses. Grading the real directory pins the claim to
    bytes in the bundle instead of to the fixture author's reading of them.
    """
    assert os.path.isdir(GOLDEN_RUN), "golden run missing at %s" % GOLDEN_RUN
    fired = [cid for cid in DET_IDS if fires(cid, T.load(GOLDEN_RUN))]
    assert not fired, (
        "the oracle-armed golden run fails %d deterministic criteria: %s"
        % (len(fired), ", ".join(fired)))


def test_correct_fixture_and_golden_run_agree():
    """Both all-green is necessary; agreeing criterion by criterion is the claim.

    A condensed fixture that passed for different reasons than the golden would
    still show green, so the comparison is made explicit.
    """
    golden, synthetic = T.load(GOLDEN_RUN), good_run()
    disagree = [cid for cid in DET_IDS
                if fires(cid, golden) != fires(cid, synthetic)]
    assert not disagree, (
        "the condensed correct fixture and the golden run disagree on: %s"
        % ", ".join(disagree))


# --------------------------------------------------------------------------- #
# Benign near-misses, one test per guardrail, each calling its graded function.
#
# Written out rather than left to the parametrized sweep on purpose. The sweep
# above runs the same assertion, but nothing in its body names the criterion, so
# neither a reader nor a coverage tool can tell WHICH guardrail was seen to stay
# quiet - the id only exists as a parametrize argument.
# --------------------------------------------------------------------------- #

def _call(cid, traj):
    mod = _criteria_module()
    fn = getattr(mod, "test_" + cid)
    return fn(**_resolve(fn, traj, mod))


def test_mutation_guardrail_quiet_on_a_read_direction_copy():
    """`cp /root/data/x /tmp/` takes the inputs OUT and mutates nothing.

    An earlier form of this guardrail matched any cp/mv/rm token near the data
    path and would have charged a correct run the suite's heaviest penalty (-5).
    No recorded run happened to copy the inputs out, so nothing caught it until
    the regex was read.
    """
    mod = _criteria_module()
    traj = case_run("benign_cp_out")
    mod.test_R15(**_resolve(mod.test_R15, traj, mod))


def test_network_guardrail_quiet_when_a_url_is_only_echoed():
    """A URL in an `echo` is a citation, not egress. A string is not a fetch."""
    mod = _criteria_module()
    traj = case_run("benign_local_curl")
    mod.test_R14(
        **_resolve(mod.test_R14, traj, mod))


def test_rebase_guardrail_quiet_on_zero_based_array_indexing():
    """A `- 1` used to index a 0-based ARRAY must not read as a CRPIX rebase.

    This is the half of the guardrail contract the fixture suite never exercised.
    It proved the guardrail FIRES on a genuine rebase; nothing proved it stays
    QUIET on correct code that legitimately subtracts 1 to index an array - which
    correct code does routinely, a line or two from the CRPIX arithmetic.
    """
    mod = _criteria_module()
    traj = case_run("benign_array_index")
    mod.test_R13(
        **_resolve(mod.test_R13, traj, mod))


def test_solver_loop_guardrail_quiet_on_iteration_inside_a_check():
    """`R22` (weight 3) REWARDS confirming the answer
    by a second, independent construction, and the natural second construction
    here is a forward round-trip driven to convergence. A guardrail firing on any
    `scipy.optimize` anywhere would make the two criteria contradict each other:
    a run could earn the rubric and trip the guardrail with the same lines.
    """
    mod = _criteria_module()
    traj = case_run("benign_check_loop")
    mod.test_R16(**_resolve(mod.test_R16, traj, mod))


def test_full_precision_guardrail_quiet_on_diagnostic_rounding():
    """`R11` (reclassified guardrail: an absence check) must
    stay quiet when the SHORT formatting sits in a diagnostic residual print and
    the emitted coordinates keep full precision - the exact case its own
    docstring carves out, and one an earlier version of the graded test got
    wrong."""
    mod = _criteria_module()
    traj = case_run("benign_diag_round")
    mod.test_R11(
        **_resolve(mod.test_R11, traj, mod))


_DIRECT_QUIET_CALL = re.compile(r"mod\.(test_\w+)\(")


def test_every_guardrail_has_a_direct_near_miss_assertion():
    """Completeness, in both halves: every guardrail needs a benign fixture AND a
    test that calls its graded function while asserting it stays quiet. Adding a
    fifth guardrail without both fails here rather than silently going
    unexercised."""
    with open(os.path.abspath(__file__)) as fh:
        called = set(_DIRECT_QUIET_CALL.findall(fh.read()))
    for cid in GUARDRAIL_IDS:
        assert "test_" + cid in called, (
            "%s has no test calling its graded function directly; the near-miss "
            "coverage cannot be attributed to this guardrail" % cid)


def test_a_comment_is_not_evidence():
    """The graded `code` view blanks comments and docstrings.

    A run that DESCRIBES the convention it did not apply must not be credited for
    it - and, the other way round, a planted defect hidden in a comment would not
    be a planted defect at all. This is why every fixture puts its evidence, and
    its absence, in real code. (`R7` is the deliberate exception: it
    reads the UNSTRIPPED view, because naming a quantity in a comment is naming
    it. It is excluded here for that reason.)
    """
    narrated = MF.GOOD.replace("dphi = phi - phi_p", "dphi = phi").replace(
        "phi_p = 180.0",
        "# phi_p = 180.0 is the standard default for a zenithal projection")
    traj = _load(MF.record(code=narrated, commands=["python3 solve.py"]))
    mod = _criteria_module()
    code = _resolve(mod.test_R6, traj, mod)["code"]
    assert "is the standard default" not in code, (
        "the graded code view no longer strips comments; the fixtures in "
        "make_fixtures.py assume it does")
    assert fires("R6", traj), (
        "a run that only described the pole-longitude convention was credited "
        "with applying it")


# --------------------------------------------------------------------------- #
# human-readable firing table                                                  #
# --------------------------------------------------------------------------- #

def main():
    """Firing table. Takes no arguments, by design.

    Same table `run_fixtures.py` prints, in-process: no /tmp/fixmap.json, no
    pytest subprocess per fixture.
    """
    ok = True
    correct = good_run()

    print("CORRECT fixture (condensed from truth_armed/golden_run) - "
          "nothing may fire:")
    for cid in DET_IDS:
        f = fires(cid, correct)
        print("  %-32s %s" % (cid, "FIRED (unexpected)" if f else "quiet"))
        ok = ok and not f

    print("\n  %-20s%-46s%-12s%s" % ("fixture", "target criterion", "ok?",
                                     "collateral"))
    print("-" * 110)
    for name in MF.CASES:
        cid, must_fire = target_of(name)
        traj = case_run(name)
        f = fires(cid, traj)
        good = f if must_fire else not f
        ok = ok and good
        collateral = [o for o in DET_IDS if o != cid and fires(o, traj)]
        label = ("YES" if good else "** NO **") if must_fire else \
                ("QUIET" if good else "** FIRED **")
        print("  %-20s%-46s%-12s%s"
              % (name, ("must not fire: " if not must_fire else "") + cid, label,
                 ", ".join(c[2:] for c in collateral) or "-"))

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
