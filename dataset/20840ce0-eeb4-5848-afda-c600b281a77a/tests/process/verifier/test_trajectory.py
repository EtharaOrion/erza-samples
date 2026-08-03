"""Deterministic channel: one test per deterministic rubric criterion.

Each test is named `test_<criterion_id>` so the junit report joins straight back
to `rubrics.json` (see `score.py: read_junit`). The tests read the *normalised
trajectory* - the source the agent authored and the commands it ran - never the
final artifact. Detection logic lives in `checks.py`; every detector is bound by
a fixture in `../verification/negative_fixtures_test.py`.

Positive criteria: the test passes when the criterion is satisfied.
Guardrail criteria (`test_d_g_*`): the test passes when the failure mode did NOT
occur, and fails when it did - which `score.py` reads as "the failure happened".

The name-to-id pairing is load-bearing: `score.py` strips the leading `test_`
and joins on the remainder, so a test whose remainder is not a rubric id makes
its criterion abstain SILENTLY and can drag the channel below its coverage
floor. `test_zz_meta_every_detector_pairs_with_a_rubric_id` asserts the join in
both directions rather than leaving it to inspection.
"""
import json
import os

import checks

_HERE = os.path.dirname(os.path.abspath(__file__))
_RUBRICS = os.path.join(_HERE, "..", "rubrics.json")


# --------------------------- positive criteria ---------------------------

def test_d_reads_inputs(traj):
    assert checks.reads_inputs(traj), \
        "never opened the baked inputs under /root/data"


def test_d_writes_emitter(traj):
    assert checks.writes_emitter(traj), \
        "no emitter authored; three 750-position records cannot be typed by hand"


def test_d_executes_emitter(traj):
    assert checks.executes_emitter(traj), \
        "did not execute python to produce the records"


def test_d_pins_the_declared_length(traj):
    assert checks.pins_the_declared_length(traj), \
        "the declared record length was never used or asserted"


def test_d_places_payee_block_at_published_offsets(traj):
    assert checks.places_payee_block_at_published_offsets(traj), \
        "CRUX: the payee identification block was not placed at its published " \
        "positions - the name line and city starts are absent from the source"


def test_d_reserves_the_interior_runs(traj):
    assert checks.reserves_the_interior_runs(traj), \
        "the reserved runs inside the record were closed rather than emitted"


def test_d_emits_return_specific_tail(traj):
    assert checks.emits_return_specific_tail(traj), \
        "the return-specific tail was not placed"


def test_d_amount_fields_right_justified_zero_filled(traj):
    assert checks.amount_fields_right_justified_zero_filled(traj), \
        "payment amount fields were not right-justified and zero-filled"


def test_d_sequence_number_zero_filled(traj):
    assert checks.sequence_number_zero_filled(traj), \
        "the record sequence number was not right-justified with leading zeros"


def test_d_converts_amounts_to_cents(traj):
    assert checks.converts_amounts_to_cents(traj), \
        "dollars were never converted to whole cents"


def test_d_reports_contract(traj):
    assert checks.reports_contract(traj), \
        "did not emit /root/results.json under the contracted top-level key"


# --------------------------- guardrails ---------------------------

def test_d_g_delimited_output(traj):
    assert not checks.failure_delimited_output(traj), \
        "emitted a delimited rendering instead of a positional record"


def test_d_g_padded_remainder_without_placing(traj):
    assert not checks.failure_padded_remainder_without_placing(traj), \
        "built the opening and padded the remainder to length without placing " \
        "any field of the record's interior or tail"


def test_d_g_grader_path_access(traj):
    assert not checks.failure_grader_path_access(traj), \
        "reached for the grading surface (verifier / oracle / expected values)"


def test_d_g_network_egress(traj):
    assert not checks.failure_network_egress(traj), \
        "attempted network egress for the published specification"


# --------------------------- meta ---------------------------

def test_zz_meta_every_detector_pairs_with_a_rubric_id():
    """The junit name join must be exact in both directions.

    score.py pairs a testcase to a criterion by stripping `test_`. A mismatch
    does not error - the criterion simply abstains - so it is asserted here.
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
