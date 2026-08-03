"""Rederivation: the method TRUTH.md describes reproduces every frozen golden.

The published field table is transcribed HERE for a third time, and in a third
shape - an ordered list of `(field, published length)` pairs with the start
positions computed by accumulation, where `oracle/layout.py` carries starts and
lengths together and `verifier/brecord_layout.py` carries absolute
`(first, last)` pairs. Three transcriptions in three shapes that agree cannot
all be the same typo, and this module asserts all three agree as well as
reproducing `verifier/expected_values.json` from the shipped payee data.

It also carries the answer-free audit of TRUTH.md, because this is the module
that has the field map in hand: no graded value and, decisively, no field
POSITION of the record this instance grades may appear in TRUTH.md; the literal
ASCII heading `Delta-lever` must be present; and the phrases a QC pass forbids
must not be.

Paths come from `ERZA_BUNDLE_DIR` (default: the bundle this file lives in). NO
`sys.argv`: under pytest argv holds pytest's own flags, and a module named
`*_test.py` that reads them errors at COLLECTION and takes the rest of the
directory with it.

    python3 -m pytest verification/rederivation_test.py -q
"""
import json
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PROC = os.path.normpath(os.path.join(HERE, ".."))
BUNDLE = os.environ.get(
    "ERZA_BUNDLE_DIR", os.path.normpath(os.path.join(HERE, "..", "..", "..")))

sys.path.insert(0, os.path.join(BUNDLE, "tests"))
import brecord_layout as parse  # noqa: E402

# --- third, independent transcription --------------------------------------- #
# Internal Revenue Service, Publication 1220, Tax Year 2025 revision,
# https://www.irs.gov/pub/irs-pdf/p1220.pdf - Part C, Sec. 3 for the block
# common to every return type, Part C, Sec. 3 (18) for the Form 1099-MISC tail.
# Only the LENGTH column is transcribed; the starts are computed, so this
# transcription and the verifier's cannot share an arithmetic slip.
PUBLISHED_LENGTHS = [
    ("record_type", 1), ("payment_year", 4), ("corrected_return_indicator", 1),
    ("name_control", 4), ("tin_type", 1), ("payee_tin", 9),
    ("issuer_account_number", 20), ("issuer_office_code", 4),
    ("blank_45_54", 10),
    ("amount_1", 12), ("amount_2", 12), ("amount_3", 12), ("amount_4", 12),
    ("amount_5", 12), ("amount_6", 12), ("amount_7", 12), ("amount_8", 12),
    ("amount_9", 12), ("amount_A", 12), ("amount_B", 12), ("amount_C", 12),
    ("amount_D", 12), ("amount_E", 12), ("amount_F", 12), ("amount_G", 12),
    ("amount_H", 12), ("amount_J", 12),
    ("blank_271_286", 16), ("foreign_country_indicator", 1),
    ("first_payee_name_line", 40), ("second_payee_name_line", 40),
    ("payee_mailing_address", 40), ("blank_408_447", 40), ("payee_city", 40),
    ("payee_state", 2), ("payee_zip_code", 9), ("blank_499", 1),
    ("record_sequence_number", 8), ("blank_508_543", 36),
    ("second_tin_notice", 1), ("blank_545_546", 2),
    ("direct_sales_indicator", 1), ("fatca_filing_indicator", 1),
    ("blank_549_662", 114), ("special_data_entries", 60),
    ("state_income_tax_withheld", 12), ("local_income_tax_withheld", 12),
    ("combined_federal_state_code", 2), ("blank_or_crlf_749_750", 2),
]
DECLARED_RECORD_LENGTH = 750


def third_spans():
    """(field, first, last) computed by accumulating the published lengths."""
    out, cursor = [], 1
    for name, length in PUBLISHED_LENGTHS:
        out.append((name, cursor, cursor + length - 1))
        cursor += length
    return out


THIRD = {name: (first, last) for name, first, last in third_spans()}


def _expected():
    with open(os.path.join(BUNDLE, "tests", "expected_values.json")) as fh:
        return json.load(fh)


def _payees():
    with open(os.path.join(BUNDLE, "environment", "data", "payees.json")) as fh:
        return {p["payee_ref"]: p for p in json.load(fh)["payees"]}


EXP = _expected()
ITEMS = EXP["items"]
PAYEES = _payees()
YEAR = EXP["payment_year"]
GOLDEN = EXP["golden_records"]


def _third_faults(record, group, payee):
    """Fault count for one group, sliced at the THIRD transcription's offsets."""
    faults = 0
    for name in dict(parse.GROUPS)[group]:
        first, last = THIRD[name]
        text = record[first - 1:last]
        reader = parse.SPAN_BY_NAME[name][4]
        try:
            got = parse.READERS[reader](text)
        except parse.FieldError:
            faults += 1
            continue
        if got != parse.wanted(name, payee, YEAR):
            faults += 1
    return faults


def _rederive(item):
    """The graded quantity: fields that decode back to the payee's own value."""
    if item["kind"] == "field_group":
        fields = dict(parse.GROUPS)[item["group"]]
        return len(fields) - _third_faults(
            GOLDEN[item["payee_ref"]], item["group"], PAYEES[item["payee_ref"]])
    good = 0
    for ref in EXP["payee_refs"]:
        record = GOLDEN[ref]
        if len(record) != DECLARED_RECORD_LENGTH:
            continue
        body, terminator = record[:748], record[748:]
        if not all("\x20" <= ch <= "\x7e" for ch in body) or body != body.upper():
            continue
        if terminator not in ("  ", "\r\n"):
            continue
        good += 1
    return good


# --------------------------- the rederivation --------------------------- #

@pytest.mark.parametrize("item", ITEMS, ids=[i["case_id"] for i in ITEMS])
def test_frozen_golden_is_reproduced(item):
    """Every stored reference reproduces from the shipped record, bit-identically."""
    got = _rederive(item)
    assert abs(got - item["ref"]) <= 1e-09, (
        "%s: rederived %r, frozen %r - the golden and the bundle have drifted "
        "apart" % (item["case_id"], got, item["ref"]))


def test_third_transcription_agrees_with_the_verifier_table():
    """This transcription and verifier/brecord_layout.py's must agree row for
    row, or one of them was mistyped."""
    mine = third_spans()
    theirs = [(name, first, last) for name, first, last, _len, _r in parse.SPANS]
    assert [n for n, _f, _l in mine] == [n for n, _f, _l in theirs], \
        "the two transcriptions do not even list the same fields in the same order"
    disagreements = [(a, b) for a, b in zip(mine, theirs) if a != b]
    assert not disagreements, (
        "%d row(s) disagree between transcriptions, first: %r"
        % (len(disagreements), disagreements[0]))


def test_published_lengths_total_the_declared_record_length():
    """The published Length column, summed, must reproduce the declared record
    length. A mistyped length that survived the row-by-row check fails here."""
    total = sum(length for _n, length in PUBLISHED_LENGTHS)
    assert total == DECLARED_RECORD_LENGTH, \
        "the published lengths total %d, not %d" % (total, DECLARED_RECORD_LENGTH)
    assert third_spans()[-1][2] == DECLARED_RECORD_LENGTH
    assert EXP["record_length_positions"] == DECLARED_RECORD_LENGTH


def test_every_frozen_record_is_the_declared_length():
    for ref, record in GOLDEN.items():
        assert len(record) == DECLARED_RECORD_LENGTH, \
            "%s is %d positions" % (ref, len(record))


def test_closing_a_reserved_run_is_measurably_wrong():
    """The receipt behind d_reserves_the_interior_runs' weight.

    Closing the reserved run that sits between the payment amounts and the payee
    name block produces a well-formed line of the declared length with the
    opening intact, so nothing about its shape gives it away. Measured here,
    live: it must miss most of the graded groups, or the criterion is not
    measuring anything.
    """
    first, last = THIRD["blank_271_286"]
    run_length = last - first + 1
    for ref in EXP["payee_refs"]:
        closed = (GOLDEN[ref][:first - 1] + GOLDEN[ref][last:]
                  + " " * run_length)
        assert len(closed) == DECLARED_RECORD_LENGTH
        failed = [g for g in parse.GROUP_KEYS
                  if _third_faults(closed, g, PAYEES[ref]) > 0]
        assert len(failed) >= 7, (
            "%s: closing one reserved run moves only %d of %d graded groups"
            % (ref, len(failed), len(parse.GROUP_KEYS)))
        # and it stays well-formed, which is why it is dangerous
        assert closed[:748] == closed[:748].upper()


def test_control_ledger_multiples_are_reproduced_from_the_shipped_data():
    """Every recorded gap must be reproducible; a ledger nobody recomputes rots."""
    gaps = EXP["control_gaps"]
    assert gaps, "no control ledger to check"
    assert EXP["smallest_wrong_path_gap_multiple"] == min(
        e["field_mismatch_gap_over_tol"] for e in gaps.values())
    assert max(e["field_mismatch_gap_over_tol"] for e in gaps.values()) >= 2.0
    for name, entry in gaps.items():
        assert "note" in entry, "control path %s carries no note" % name
        failed_key = [k for k in entry if k.startswith("graded_cases_failed_of_")]
        assert failed_key, "control path %s records no case count" % name
        if entry[failed_key[0]] == 0:
            assert "non_discriminating_note" in entry, \
                "%s passes every graded case and does not say so" % name


# --------------------------- TRUTH.md audit --------------------------- #

def _truth():
    with open(os.path.join(PROC, "TRUTH.md")) as fh:
        return fh.read()


def test_truth_md_carries_the_delta_lever_heading():
    """The heading must be the literal ASCII string, not only the Greek letter."""
    assert re.search(r"^#+\s*Delta-lever\s*$", _truth(), re.M), \
        "TRUTH.md has no literal `Delta-lever` heading"


def test_truth_md_avoids_the_forbidden_provenance_phrases():
    """A QC pass fires on these strings regardless of context, including when
    they describe the unaided agent's behaviour."""
    truth = _truth().lower()
    banned = ["from memory", "recalled", "reconstructed from memory",
              "approximated from", "approximate from"]
    hits = [phrase for phrase in banned if phrase in truth]
    assert not hits, "TRUTH.md contains forbidden phrase(s): %s" % ", ".join(hits)


def test_truth_md_states_no_graded_value():
    """TRUTH.md is answer-free: it is handed to an LLM judge, so a graded figure
    printed in it would be a second answer key."""
    truth = _truth()
    for key in ("seed",):
        value = EXP.get(key)
        if value is not None:
            assert str(value) not in truth, \
                "TRUTH.md prints %s=%r" % (key, value)
    for record in GOLDEN.values():
        for start in range(0, DECLARED_RECORD_LENGTH - 24 + 1):
            chunk = record[start:start + 24]
            if len(chunk.replace(" ", "")) < 6:
                continue
            assert chunk not in truth, \
                "TRUTH.md carries a run of a golden record verbatim"


def test_truth_md_withholds_the_field_positions():
    """The decisive test of 6.11: prompt + TRUTH.md, without the skill, must not
    be enough to score 1.

    The withheld lever IS the position table, so TRUTH.md must state the method
    - the field classes, the self-consistency check, the ordering, the read-back
    - without printing where any field of this record begins or ends.

    Scoped to the boundaries above position 20 and below the declared record
    length. The low boundaries are unavoidable vocabulary in a document that
    numbers its own steps, and they belong to the opening of the record, which
    is the part any competent implementer already reproduces; the declared
    length is stated in the agent's own inputs. Everything in between is the
    lever, and none of it may appear.
    """
    truth = _truth()
    numerals = {int(n) for n in re.findall(r"(?<![\w.])(\d{1,5})(?![\w.])", truth)}
    boundaries = set()
    for _name, first, last, _length, _reader in parse.SPANS:
        boundaries.add(first)
        boundaries.add(last)
    discriminating = {b for b in boundaries
                      if 20 < b < DECLARED_RECORD_LENGTH}
    leaked = sorted(discriminating & numerals)
    assert not leaked, (
        "TRUTH.md prints field boundary position(s) %s - with those it becomes "
        "a second answer key" % ", ".join(str(x) for x in leaked))


def test_truth_md_carries_no_assembled_record():
    """One correct record lets the name block's start be counted off it, so a
    worked example is as fatal here as a printed table."""
    truth = _truth()
    assert not re.search(r"^[A-Z0-9 +\-&./]{80,}$", truth, re.M), \
        "TRUTH.md contains a line that reads as an assembled fixed-length record"
