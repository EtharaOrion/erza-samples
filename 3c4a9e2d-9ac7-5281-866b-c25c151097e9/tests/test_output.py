"""OUTCOME tests for ghg-conversion-factor-vintage, in the shared sample-set convention.

The grading semantics live in ``from_answer_key.py`` beside this file, the same generic
outcome verifier that graded this task's recorded runs, driven entirely by
``expected_values.json``. This module is a pytest adapter over it, nothing more: one
``test_score_kg_co2e[<case_id>]`` per graded (output, case_id) pair, so ``../tests/test.sh``
can count ``test_score_`` cases from the structured report exactly as it does for every
other bundle in this set. Re-implementing the comparison here would create a second
grader that could drift from the one the published measurements used; wrapping it cannot.

Self-checks (``test_selfcheck_*``) are unscored grader audits wired to the kill-switch in
``test.sh``: if one fails, the run scores 0 fail-closed as a BUNDLE DEFECT, never as an
agent failure. They prove the spec is intact and that the graded band is real - the
distractor strategies recorded at generation time must still fail the graded set, and the
tolerances must be tight enough that three-significant-figure recall cannot pass.
"""

import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import from_answer_key as fak  # noqa: E402  (sibling module, shared grader)

with open(os.path.join(HERE, "expected_values.json"), encoding="utf-8") as _fh:
    SPEC = json.load(_fh)

CASES = SPEC["cases"]
CASE_IDS = [c.get("test_id") or c["case_id"] for c in CASES]


@pytest.fixture(scope="module")
def verdicts():
    """One grading pass, shared by every scored case: {test_id: (ok, detail)}."""
    results, _notes = fak.grade(SPEC)
    return {test_id: (ok, detail) for test_id, _cid, _out, ok, detail in results}


@pytest.mark.outcome
@pytest.mark.parametrize("case_id", CASE_IDS)
def test_score_kg_co2e(verdicts, case_id):
    ok, detail = verdicts[case_id]
    assert ok, f"{case_id}: {detail}"


# ---------------------------------------------------------------------------
# Grader self-audits (unscored; a failure trips the kill-switch in test.sh)
# ---------------------------------------------------------------------------


@pytest.mark.selfcheck
def test_selfcheck_spec_is_intact():
    """The generated spec must pass the shared verifier's own structural audit."""
    problems = fak.check_spec(SPEC)
    assert problems == [], f"expected_values.json failed its audit: {problems}"


@pytest.mark.selfcheck
def test_selfcheck_graded_set_shape():
    """14 tolerance-graded kg_co2e cases, each with a finite golden and a positive tolerance."""
    assert len(CASES) == 14, f"graded set has {len(CASES)} cases, generated with 14"
    for c in CASES:
        assert c["match"] == "tolerance_abs", c
        assert c["output"] == "kg_co2e", c
        golden, tol = float(c["golden"]), float(c["tolerance_abs"])
        assert golden > 0 and golden == golden, c
        assert tol > 0, c


@pytest.mark.selfcheck
def test_selfcheck_distractor_routes_still_fail():
    """The control strategies recorded at generation time must not clear the graded set.

    Each entry in ``control_gaps`` is a route an unaided run plausibly takes - the latest
    factor edition applied everywhere, an off-by-one vintage, a factor recalled to three
    significant figures, a tuned constant. The generator measured how many graded cases
    each clears; if any control could pass the whole set, the task would be gradeable
    without the withheld factor editions and the graded band would be fake. Enforcing the
    recorded bound keeps this audit live against a regenerated or hand-edited spec.
    """
    gaps = SPEC["control_gaps"]
    assert gaps, "control_gaps absent: the graded band has no recorded negative controls"
    for name, gap in gaps.items():
        cleared = gap.get("cases_this_route_would_pass")
        assert cleared is not None, f"{name}: no recorded pass count"
        assert cleared < len(CASES), (
            f"control strategy {name!r} clears {cleared}/{len(CASES)} graded cases; "
            f"the task is solvable by a distractor route")


@pytest.mark.selfcheck
def test_selfcheck_output_contract():
    """The submission contract must stay the one the instruction states."""
    out = SPEC["output"]
    assert out["format"] == "json_nested"
    assert out["path"] == "/root/results.json"
    assert out["value_key"] == "kg_co2e"
@pytest.mark.selfcheck
def test_selfcheck_graded_case_count_is_pinned():
    """Collection-count guard: exactly 14 graded cases must be collected.

    test.sh scores `cases_passed / cases_total` over the `test_score_` prefix,
    so the DENOMINATOR is whatever pytest happened to collect. This module
    parametrises straight off `expected_values.json`, which means a case
    quietly dropped from `cases` does not fail anything - it simply stops
    being graded, and the run still reports full marks on the cases that
    remain. The shape self-check above pins the ledger, but a scored test
    renamed out of the `test_score_` prefix would leave the ledger green while
    the collected count silently falls to zero. The count is pinned here so a
    shrunken denominator reads as a BUNDLE DEFECT rather than as a full-marks
    run.

    Counted the way test.sh counts: every `test_score_`-named callable in this
    module, multiplied out by the parametrize arguments the decorator was
    actually handed. The ledger those ids are read from is pinned alongside it,
    so the guard cannot be satisfied by a decorator that has drifted away from
    the frozen data.
    """
    pinned = 14
    scored, collected = [], 0
    for name, obj in sorted(globals().items()):
        if not name.startswith("test_score_") or not callable(obj):
            continue
        cases = 1
        for mark in getattr(obj, "pytestmark", []):
            if mark.name == "parametrize":
                cases *= len(mark.args[1])
        scored.append(f"{name} x{cases}")
        collected += cases
    assert collected == pinned, (
        f"collection-count guard: {collected} graded cases collected, {pinned} "
        f"pinned ({', '.join(scored) or 'no test_score_ callable at all'}) - "
        f"the score denominator has moved")

    assert len(CASE_IDS) == pinned and len(set(CASE_IDS)) == pinned, (
        f"collection-count guard: the parametrize ledger yields {len(CASE_IDS)} "
        f"case ids, {pinned} distinct pinned")
    with open(os.path.join(HERE, "expected_values.json"), encoding="utf-8") as f:
        frozen = json.load(f)
    frozen_ids = [c.get("test_id") or c["case_id"] for c in frozen["cases"]]
    assert frozen_ids == CASE_IDS, (
        "collection-count guard: the module's CASE_IDS have drifted from the "
        "frozen expected_values.json cases")
