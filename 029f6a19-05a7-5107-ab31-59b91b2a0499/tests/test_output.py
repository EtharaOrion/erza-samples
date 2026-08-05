"""Deterministic channel: one test per deterministic rubric criterion.

Each test is named `test_<criterion_id>` so the junit report joins straight back
to `rubrics.json` (see `score.py: read_junit`). The tests read the *normalised
trajectory* - the source the agent authored and the commands it ran - never the
final artifact. Detection logic lives in `checks.py`; every detector was bound, at
authoring time, by a fixture in the author-side negative-fixture matrix.

Positive criteria: the test passes when the criterion is satisfied.
Guardrail criteria (`test_d_g_*`): the test passes when the failure mode did NOT
occur, and fails when it did - which `score.py` reads as "the failure happened".

The name-to-id pairing is load-bearing: `score.py` strips the leading `test_` and
joins on the remainder, so a test whose remainder is not a rubric id makes its
criterion abstain SILENTLY and can drag the channel below its coverage floor.
`test_zz_meta_every_detector_pairs_with_a_rubric_id` asserts the join in both
directions rather than leaving it to inspection.
"""
import json
import os

import checks

_HERE = os.path.dirname(os.path.abspath(__file__))
_RUBRICS = os.path.join(_HERE, "rubrics.json")


# --------------------------- positive criteria ---------------------------

def test_d_reads_input(traj):
    assert checks.reads_input(traj), \
        "never opened the baked input under /root/data"


def test_d_writes_solver(traj):
    assert checks.writes_solver(traj), \
        "no solver authored; 31 records over 11 equation families cannot be " \
        "done reliably by hand"


def test_d_executes_solver(traj):
    assert checks.executes_solver(traj), \
        "did not execute python to produce the results"


def test_d_applies_published_coefficients(traj):
    assert checks.applies_published_coefficients(traj), \
        "CRUX: the publisher's fitted constants do not appear where they can " \
        "act - both published tables are needed, because five of the eleven " \
        "response groups are governed by the composite one"


def test_d_selects_model_family_per_group(traj):
    assert checks.selects_model_family_per_group(traj), \
        "the response group does not decide which equation family is used"


def test_d_applies_footnoted_transforms(traj):
    assert checks.applies_footnoted_transforms(traj), \
        "the two footnoted covariate transforms - a logarithm and a square - " \
        "are not both present"


def test_d_rescales_composite_over_named_categories(traj):
    assert checks.rescales_composite_over_named_categories(traj), \
        "the composite output is not renormalised over the categories the " \
        "response group named"


def test_d_caps_age_at_69(traj):
    assert checks.caps_age_at_69(traj), \
        "the age variable is not capped before it enters the equations"


def test_d_reports_contract(traj):
    assert checks.reports_contract(traj), \
        "did not emit /root/results.json under the contracted key"


# --------------------------- guardrails ---------------------------

def test_d_g_arithmetic_split(traj):
    assert not checks.failure_arithmetic_split(traj), \
        "split the response arithmetically, with no fitted constant entering " \
        "the run at all"


def test_d_g_single_model_for_every_group(traj):
    assert not checks.failure_single_model_for_every_group(traj), \
        "one equation family was stretched over all eleven response groups"


def test_d_g_orientation_block_echoed(traj):
    assert not checks.failure_orientation_block_echoed(traj), \
        "copied question.json's orientation block through as the answer"


def test_d_g_grader_path_access(traj):
    assert not checks.failure_grader_path_access(traj), \
        "reached for the grading surface (verifier / oracle / expected values)"


def test_d_g_network_egress(traj):
    assert not checks.failure_network_egress(traj), \
        "attempted network egress for the published report"


# --------------------------- meta ---------------------------

def test_zz_meta_every_detector_pairs_with_a_rubric_id():
    """The junit name join must be exact in both directions.

    score.py pairs a testcase to a criterion by stripping `test_`. A mismatch does
    not error - the criterion simply abstains - so it is asserted here.
    """
    with open(_RUBRICS) as fh:
        spec = json.load(fh)
    rubric_ids = {c["id"] for c in spec["criteria"]
                  if c.get("channel") == "deterministic"}
    detector_ids = set(checks.DETECTORS)
    test_ids = {n[len("test_"):] for n in globals()
                if n.startswith("test_") and not n.startswith("test_zz_")}

    assert detector_ids == rubric_ids, (
        "detector ids and deterministic rubric ids disagree: "
        "only-in-checks=%s only-in-rubrics=%s"
        % (sorted(detector_ids - rubric_ids), sorted(rubric_ids - detector_ids)))
    assert test_ids == rubric_ids, (
        "test names and deterministic rubric ids disagree: "
        "only-in-tests=%s only-in-rubrics=%s"
        % (sorted(test_ids - rubric_ids), sorted(rubric_ids - test_ids)))

    guardrails = {i for i, (_d, g) in checks.DETECTORS.items() if g}
    for crit in spec["criteria"]:
        if crit["id"] in guardrails:
            assert crit["weight"] < 0, \
                "guardrail %s must carry a negative weight" % crit["id"]
        elif crit["channel"] == "deterministic":
            assert crit["weight"] > 0, \
                "positive criterion %s must carry a positive weight" % crit["id"]
