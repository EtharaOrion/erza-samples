"""Deterministic channel: one test per deterministic rubric criterion.

Each test is named `test_<criterion_id>` so the junit report joins straight back
to `rubrics.json` (see `score.py: read_junit`). The tests read the *normalised
trajectory* - the source the agent authored and the commands it ran - never the
final artifact. Detection logic lives in `checks.py`; every detector is bound by
a fixture in `../verification/negative_fixtures_test.py`.

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
_RUBRICS = os.path.join(_HERE, "..", "rubrics.json")


# --------------------------- positive criteria ---------------------------

def test_d_reads_roster(traj):
    assert checks.reads_roster(traj), \
        "never opened the baked roster or contract under /root/data"


def test_d_writes_solver(traj):
    assert checks.writes_solver(traj), \
        "no solver authored; 119 comparisons cannot be made by hand"


def test_d_executes_solver(traj):
    assert checks.executes_solver(traj), \
        "did not execute python to produce the results"


def test_d_normalises_to_one_clock(traj):
    assert checks.normalises_to_one_clock(traj), \
        "clock times and durations were not both reduced to whole minutes and " \
        "the overnight wrap handled; nothing downstream may compare a string"


def test_d_splits_augmented_regime(traj):
    assert checks.splits_augmented_regime(traj), \
        "never routed the augmented pairings to their own matrix on crew size " \
        "and rest-facility class"


def test_d_indexes_matrix_on_both_axes(traj):
    assert checks.indexes_matrix_on_both_axes(traj), \
        "CRUX: the published duty-period matrix was not written down and " \
        "indexed on both the report-time band and the segment (or crew/class) " \
        "axis"


def test_d_applies_acclimation_reduction(traj):
    assert checks.applies_acclimation_reduction(traj), \
        "the reduction for an unacclimated crew never enters the derivation"


def test_d_tests_split_duty_conditions(traj):
    assert checks.tests_split_duty_conditions(traj), \
        "the accommodation rest was handled without testing the published " \
        "conditions on it"


def test_d_enumerates_all_limits(traj):
    assert checks.enumerates_all_limits(traj), \
        "the enumeration is truncated: not every limit the part imposes got a " \
        "margin"


def test_d_includes_pairing_in_rolling_totals(traj):
    assert checks.includes_pairing_in_rolling_totals(traj), \
        "the rolling ceilings were compared against the history alone, without " \
        "adding the pairing under test"


def test_d_takes_minimum_margin(traj):
    assert checks.takes_minimum_margin(traj), \
        "no minimum over the margins; the governing limit cannot have been " \
        "selected"


def test_d_reports_contract(traj):
    assert checks.reports_contract(traj), \
        "/root/results.json not written with all three contracted fields"


# --------------------------- guardrails ----------------------------------

def test_d_g_flat_duty_ceiling(traj):
    assert not checks.failure_flat_duty_ceiling(traj), \
        "a single flat duty ceiling stood in for the matrix"


def test_d_g_extension_applied_to_schedule(traj):
    assert not checks.failure_extension_applied_to_schedule(traj), \
        "the relief for unforeseen circumstances was added to a scheduled " \
        "ceiling"


def test_d_g_grader_path_access(traj):
    assert not checks.failure_grader_path_access(traj), \
        "the run read or probed the grading surface"


def test_d_g_network_egress(traj):
    assert not checks.failure_network_egress(traj), \
        "the run attempted a network fetch or a package install"


# --------------------------- meta ----------------------------------------

def test_zz_meta_every_detector_pairs_with_a_rubric_id():
    """The junit join must be total in both directions.

    A deterministic criterion with no test abstains silently and can drag the
    channel under its coverage floor; a test whose name is not a criterion id
    scores nothing and looks like coverage.
    """
    with open(_RUBRICS) as fh:
        spec = json.load(fh)
    rubric_ids = {c["id"] for c in spec["criteria"]
                  if c["channel"] == "deterministic"}
    test_ids = {name[len("test_"):] for name in globals()
                if name.startswith("test_d_")}
    assert test_ids == rubric_ids, (
        "deterministic criteria without a test: %s; tests without a criterion: %s"
        % (sorted(rubric_ids - test_ids), sorted(test_ids - rubric_ids)))
    assert set(checks.DETECTORS) == rubric_ids, (
        "detector registry and rubric disagree: %s"
        % sorted(set(checks.DETECTORS) ^ rubric_ids))
