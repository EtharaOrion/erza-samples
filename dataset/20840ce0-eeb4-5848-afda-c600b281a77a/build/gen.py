"""Build the information-return-brecord-emission bundle.

Emits `environment/data/*` (agent-visible) and `verifier/expected_values.json`
(grader-side). Every golden record and every control-gap multiple is DERIVED
here by running the published field table over the payee data; nothing is
hand-typed.

WHAT IS REAL AND WHAT IS SYNTHETIC
----------------------------------
The FORMAT is real: the 750-position payee detail record of the IRS electronic
transmission specification, Publication 1220, Tax Year 2025 revision. Every
field position, length, justification and indicator code used here is
transcribed from that document (see `build_report.json:sources`).

The PAYEE DATA is entirely synthetic. Real information returns carry taxpayer
identification numbers, legal names and home addresses; none of that may be
baked into a distributed image, and no public corpus of real payee records
exists to draw on. The names, addresses, account numbers and identification
numbers below are invented, and the identification numbers are drawn from
ranges the US Social Security Administration has never issued, so none of them
can collide with a real one. This is recorded in `build_report.json:anonymisation`
rather than left implicit.

WHAT THIS BUILD DELIBERATELY DOES NOT PRODUCE
---------------------------------------------
A worked example record. Not in `instruction.md`, not in `environment/data/`, not in
the skill. The withheld object is a positional field map, and a single assembled
record hands most of it over at a glance: an agent that can see one correct
record can read the name block's start position straight off it. That is the one
leak channel this task has, and it is fully under the author's control.
`verifier/test_outputs.py::test_no_assembled_record_reaches_the_agent` asserts
the absence on every graded run rather than trusting this comment.

SEED
----
Declared for the template's sake and used for nothing: there is no random
component. The instance is authored, not sampled, so re-running this script is
byte-reproducible by construction.
"""

import json
import os
import sys
from decimal import Decimal

SEED = 20260729

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "solution"))
import layout  # noqa: E402

DATA = os.path.join(ROOT, "environment", "data")
VERIFIER = os.path.join(ROOT, "tests")

FORM_TYPE = "1099-MISC"
PAYMENT_YEAR = "2025"

# One graded case per field group per record, plus one file-level case.
# 3 records x 10 groups + 1 = 31, and 31 is prime, so no partial score lands on
# a round fraction and no golden is a round value.
N_RECORDS = 3
N_GROUPS = 10
N_CASES = N_RECORDS * N_GROUPS + 1

# The graded quantity is the number of fields in a group that DO decode back to
# the payee's own value, so a group's reference is its own field count and the
# tolerance admits no shortfall. Counted this way rather than as a fault count
# because a uniform reference of zero collides with the zero-dollar amounts the
# payee data legitimately carries, and a leak scanner cannot tell the two apart.
TOLERANCE = 0.5

PAYEES = [
    {
        "payee_ref": "R0001",
        "name_control": "HERN",
        "tin_type": "SSN",
        "payee_tin": "412556309",
        "issuer_account_number": "AC-4471902",
        "issuer_office_code": "NC03",
        "correction_status": "original",
        "payment_amounts": {"1": "18450.00", "4": "2767.50"},
        "foreign_address": False,
        "first_payee_name_line": "HERNANDEZ ROSA M",
        "second_payee_name_line": "",
        "payee_mailing_address": "3184 CALLE VERDE APT 12",
        "payee_city": "CHARLOTTE",
        "payee_state": "NC",
        "payee_zip_code": "28202",
        "record_sequence_number": 3,
        "second_tin_notice": False,
        "direct_sales_5000_or_more": True,
        "fatca_filing_requirement": False,
        "special_data_entries": "",
        "state_income_tax_withheld": "923.75",
        "local_income_tax_withheld": "0.00",
        "combined_federal_state_code": "37",
    },
    {
        "payee_ref": "R0002",
        "name_control": "PINE",
        "tin_type": "EIN",
        "payee_tin": "364418857",
        "issuer_account_number": "0000012947-B",
        "issuer_office_code": "WI11",
        "correction_status": "one-transaction correction",
        "payment_amounts": {"2": "7315.20", "6": "24980.00",
                            "A": "1150.00", "C": "9600.00"},
        "foreign_address": False,
        "first_payee_name_line": "PINEHURST FARMS COOPERATIVE",
        "second_payee_name_line": "AND MIDLAND GRAIN PARTNERS LLC",
        "payee_mailing_address": "1420 COUNTY ROAD K",
        "payee_city": "FOND DU LAC",
        "payee_state": "WI",
        "payee_zip_code": "549359102",
        "record_sequence_number": 4,
        "second_tin_notice": True,
        "direct_sales_5000_or_more": False,
        "fatca_filing_requirement": True,
        "special_data_entries": "",
        "state_income_tax_withheld": "1462.30",
        "local_income_tax_withheld": "0.00",
        "combined_federal_state_code": "55",
    },
    {
        "payee_ref": "R0003",
        "name_control": "OKEE",
        "tin_type": "SSN",
        "payee_tin": "587223416",
        "issuer_account_number": "SP-2025-0088",
        "issuer_office_code": "TX07",
        "correction_status": "original",
        "payment_amounts": {"3": "5400.00", "8": "2140.75", "D": "31000.00"},
        "foreign_address": False,
        "first_payee_name_line": "OKEEFE DANIEL J",
        "second_payee_name_line": "",
        "payee_mailing_address": "PO BOX 4471",
        "payee_city": "EL PASO",
        "payee_state": "TX",
        "payee_zip_code": "799120044",
        "record_sequence_number": 5,
        "second_tin_notice": True,
        "direct_sales_5000_or_more": False,
        "fatca_filing_requirement": False,
        "special_data_entries": "",
        "state_income_tax_withheld": "0.00",
        "local_income_tax_withheld": "0.00",
        "combined_federal_state_code": "",
    },
]

DELIMITED_COLUMNS = [
    "payee_ref", "name_control", "tin_type", "payee_tin",
    "issuer_account_number", "issuer_office_code", "correction_status",
    "first_payee_name_line", "second_payee_name_line", "payee_mailing_address",
    "payee_city", "payee_state", "payee_zip_code", "record_sequence_number",
    "state_income_tax_withheld", "local_income_tax_withheld",
    "combined_federal_state_code",
]


def delimited_rendering(payee):
    """The same payee data as the payables system exports it: one comma-joined
    line. Supplied to the agent for orientation, and measured as a control."""
    return ",".join(str(payee[c]) for c in DELIMITED_COLUMNS)


# --------------------------------------------------------------------------- #
# Control paths. Each is a real route a competent implementer without the field
# map actually takes, rendered as a full 750-position submission so its distance
# can be measured rather than asserted.
# --------------------------------------------------------------------------- #

def _rendered_fields(payee):
    return [(name, layout.render_field(name, length, kind, payee, PAYMENT_YEAR))
            for name, _start, length, kind in layout.FIELDS]


def _fit(text):
    return text[:750] if len(text) >= 750 else text.ljust(750)


def control_shifted_name_and_address_block(payee):
    """Correct through the payment amounts, then the payee identification block
    packed straight on with no reserved runs between the amounts and the name
    lines or between the mailing address and the city."""
    out = []
    for name, text in _rendered_fields(payee):
        if name in ("blank_271_286", "blank_408_447"):
            continue
        out.append(text)
    return _fit("".join(out))


def control_comma_delimited(payee):
    """Emit the payee data comma-delimited instead of at fixed positions."""
    return _fit(delimited_rendering(payee))


def control_left_justified_amounts(payee):
    """Amounts written as dollars-and-cents text, left-justified and
    blank-filled, instead of right-justified and zero-filled in cents."""
    out = []
    for name, text in _rendered_fields(payee):
        if name.startswith("amount_"):
            code = name.split("_", 1)[1]
            dollars = payee["payment_amounts"].get(code, "0.00")
            out.append(str(dollars).ljust(12))
        elif name in ("state_income_tax_withheld", "local_income_tax_withheld"):
            out.append(str(payee[name]).ljust(12))
        else:
            out.append(text)
    return _fit("".join(out))


def control_missing_form_specific_tail(payee):
    """The block common to every return type, then blanks: the return-specific
    tail is never placed at all."""
    golden = layout.emit_record(payee, PAYMENT_YEAR)
    return golden[:543] + " " * 207


def control_nec_tail_instead_of_misc(payee):
    """The neighbouring form's tail table applied to this form. Form 1099-NEC
    runs blanks from 548 to 662; Form 1099-MISC carries an account-reporting
    indicator at 548 and starts its blank run at 549."""
    golden = layout.emit_record(payee, PAYMENT_YEAR)
    return golden[:547] + " " + golden[548:]


def control_reserved_runs_zero_filled(payee):
    """Every unused position zero-filled rather than blank-filled - the standard
    fixed-width habit, and the opposite of what this specification says."""
    out = []
    for name, text in _rendered_fields(payee):
        if name.startswith("blank_"):
            out.append("0" * len(text))
        else:
            out.append(text)
    return _fit("".join(out))


CONTROLS = {
    "shifted_name_and_address_block": control_shifted_name_and_address_block,
    "comma_delimited_instead_of_fixed_width": control_comma_delimited,
    "left_justified_amount_fields": control_left_justified_amounts,
    "missing_form_specific_tail": control_missing_form_specific_tail,
    "nec_tail_instead_of_misc": control_nec_tail_instead_of_misc,
    "reserved_runs_zero_filled": control_reserved_runs_zero_filled,
}

CONTROL_NOTES = {
    "shifted_name_and_address_block": {
        "description": "place the head and the payment amounts correctly, then "
                       "pack the payee identification block straight on with no "
                       "reserved run between the amounts and the name lines, and "
                       "none between the mailing address and the city",
        "note": "The nearest real competitor method: the route a competent "
                "implementer without the field map actually produces. Recall of "
                "this specification is real for the opening positions and decays "
                "afterwards, so the head lands and everything past the amounts "
                "slides. Not a strawman.",
        "nearest_real_competitor": True,
    },
    "comma_delimited_instead_of_fixed_width": {
        "description": "emit the payee data comma-delimited, as the payables "
                       "extract supplies it, padded to the declared length",
        "note": "A real competing method: the delimited export is what most "
                "downstream tax systems consume, and it is what the orientation "
                "block in question.json shows.",
        "nearest_real_competitor": True,
    },
    "left_justified_amount_fields": {
        "description": "write payment amounts as dollars-and-cents text, "
                       "left-justified and blank-filled, rather than "
                       "right-justified and zero-filled with implied cents",
        "note": "A real competing convention: left-justified blank-filled is the "
                "default in most fixed-width business formats, and this "
                "specification inverts it for money fields only.",
        "nearest_real_competitor": True,
    },
    "missing_form_specific_tail": {
        "description": "emit the block common to every return type and leave the "
                       "return-specific tail blank",
        "note": "A real competing method: the common block is the part of the "
                "specification that is widely reproduced, and the per-form tails "
                "are the part that is not.",
        "nearest_real_competitor": True,
    },
    "nec_tail_instead_of_misc": {
        "description": "apply the neighbouring form's tail table, which runs "
                       "blanks where this form carries its account-reporting "
                       "indicator",
        "note": "A real competing method - the two tails are adjacent sections of "
                "the same publication - but MEASURED NON-DISCRIMINATING on the two "
                "payees that carry no account-reporting requirement, where the two "
                "tables agree position for position. It separates only on the payee "
                "that does, and there by a single field. Recorded rather than "
                "dropped; see build_report.json:graded_set.",
    },
    "reserved_runs_zero_filled": {
        "description": "zero-fill every reserved run instead of blank-filling it",
        "note": "A real competing convention: zero-fill is the usual fixed-width "
                "habit, and this specification distinguishes 'enter blanks' from "
                "'enter zeros' field by field.",
    },
}

# Readings of the publication that are equally faithful and must NOT be failed.
CONVENTION_VARIANTS = {
    "issuer_account_number_right_justified": (
        "the issuer's account-number field right-justified rather than "
        "left-justified; the publication permits either"),
    "record_terminated_with_crlf": (
        "the last two positions carrying a carriage return and line feed rather "
        "than blanks; the publication permits either"),
}


def variant_right_justified_account(record, payee):
    from_, to_ = 21, 40
    value = str(payee["issuer_account_number"])
    return record[:from_ - 1] + value.rjust(to_ - from_ + 1) + record[to_:]


def variant_crlf_terminator(record, _payee):
    return record[:748] + "\r\n"


VARIANT_BUILDERS = {
    "issuer_account_number_right_justified": variant_right_justified_account,
    "record_terminated_with_crlf": variant_crlf_terminator,
}


def main():
    layout.check_table()
    sys.path.insert(0, VERIFIER)
    import brecord_layout as parse  # noqa: E402  (grader-side, second formulation)
    parse.check_spans()

    if len(PAYEES) != N_RECORDS:
        raise AssertionError("payee count and N_RECORDS disagree")
    if len(parse.GROUP_KEYS) != N_GROUPS:
        raise AssertionError("group count and N_GROUPS disagree")

    goldens = {p["payee_ref"]: layout.emit_record(p, PAYMENT_YEAR) for p in PAYEES}
    for ref, rec in goldens.items():
        if len(rec) != 750:
            raise AssertionError("%s is %d positions" % (ref, len(rec)))

    # The golden must decode cleanly through the verifier's independent table.
    for payee in PAYEES:
        rec = goldens[payee["payee_ref"]]
        for group in parse.GROUP_KEYS:
            faults = parse.field_faults(rec, group, payee, PAYMENT_YEAR)
            if faults:
                raise AssertionError("golden %s fails %s: %r"
                                     % (payee["payee_ref"], group, faults))

    # ---- agent-visible inputs ------------------------------------------------
    os.makedirs(DATA, exist_ok=True)
    payee_payload = {
        "form_type": FORM_TYPE,
        "payment_year": PAYMENT_YEAR,
        "payees": PAYEES,
    }
    with open(os.path.join(DATA, "payees.json"), "w") as fh:
        json.dump(payee_payload, fh, indent=2, sort_keys=True)
        fh.write("\n")

    question = {
        "specification": {
            "publisher": "Internal Revenue Service, United States",
            "document": "Publication 1220",
            "title": "Specifications for Electronic Filing of Forms 1097, 1098, "
                     "1099, 3921, 3922, 5498, and W-2G",
            "revision": "Tax Year 2025",
            "url": "https://www.irs.gov/pub/irs-pdf/p1220.pdf",
            "record_name": "Payee \"B\" Record",
            "record_length_positions": 750,
            "currency": "United States dollars",
            "status_note": "The Tax Year 2025 revision is the governing revision "
                           "for this transmission. The fixed-length record format "
                           "it specifies is in force for this filing; treat it as "
                           "current and conform to it.",
        },
        "form_type": FORM_TYPE,
        "payment_year": PAYMENT_YEAR,
        "payee_refs": [p["payee_ref"] for p in PAYEES],
        "output_path": "/root/results.json",
        "output_contract": {
            "top_level_key": "records",
            "keyed_by": "payee_ref",
            "value": "one string per payee, of exactly "
                     "specification.record_length_positions characters",
            "scoring": "one case per field group per record, plus one case for "
                       "the shape of the answer file as a whole; %d in total"
                       % N_CASES,
        },
        "decoy_reference": {
            "delimited_columns": DELIMITED_COLUMNS,
            "delimited_rendering": {p["payee_ref"]: delimited_rendering(p)
                                    for p in PAYEES},
            "supplied_for": "orientation only - this is the same payee data as it "
                            "leaves the payables system, before any transmission "
                            "format is applied",
        },
    }
    with open(os.path.join(DATA, "question.json"), "w") as fh:
        json.dump(question, fh, indent=2, sort_keys=True)
        fh.write("\n")

    # ---- graded case ledger --------------------------------------------------
    items = []
    for payee in PAYEES:
        for group in parse.GROUP_KEYS:
            items.append({
                "case_id": "%s_%s" % (payee["payee_ref"], group),
                "kind": "field_group",
                "payee_ref": payee["payee_ref"],
                "group": group,
                "ref": float(len(dict(parse.GROUPS)[group])),
                "tolerance": TOLERANCE,
            })
    items.append({
        "case_id": "answer_file_shape_and_charset",
        "kind": "file_level",
        "payee_ref": None,
        "group": None,
        "ref": float(N_RECORDS),
        "tolerance": TOLERANCE,
    })
    if len(items) != N_CASES:
        raise AssertionError("built %d cases, expected %d" % (len(items), N_CASES))

    # ---- control gaps, measured ---------------------------------------------
    control_gaps = {}
    for path_name, builder in CONTROLS.items():
        worst_faults = 0
        per_case = {}
        cases_failed = 0
        for payee in PAYEES:
            submission = builder(payee)
            for group in parse.GROUP_KEYS:
                if len(submission) != 750:
                    faults = len(dict(parse.GROUPS)[group])
                else:
                    faults = len(parse.field_faults(submission, group, payee,
                                                    PAYMENT_YEAR))
                key = "%s_%s" % (payee["payee_ref"], group)
                per_case[key] = faults
                worst_faults = max(worst_faults, faults)
                if faults > TOLERANCE:
                    cases_failed += 1
        entry = dict(CONTROL_NOTES[path_name])
        entry["field_mismatch_gap_over_tol"] = round(worst_faults / TOLERANCE, 3)
        entry["graded_cases_failed_of_%d" % N_CASES] = cases_failed
        entry["worst_group_field_mismatches"] = worst_faults
        if cases_failed == 0:
            entry["non_discriminating_note"] = (
                "MEASURED AT ZERO on every graded case.")
        control_gaps[path_name] = entry

    # ---- convention variants, measured: neither may false-fail ---------------
    convention_variants = {}
    worst_variant_faults = 0
    for vname, vdesc in CONVENTION_VARIANTS.items():
        builder = VARIANT_BUILDERS[vname]
        faults_here = 0
        for payee in PAYEES:
            variant = builder(goldens[payee["payee_ref"]], payee)
            for group in parse.GROUP_KEYS:
                faults_here = max(
                    faults_here,
                    len(parse.field_faults(variant, group, payee, PAYMENT_YEAR)))
        worst_variant_faults = max(worst_variant_faults, faults_here)
        convention_variants[vname] = {
            "description": vdesc,
            "measured_deviation_field_mismatches": faults_here,
            "must_not_false_fail": True,
        }

    smallest_gap = min(e["field_mismatch_gap_over_tol"] for e in control_gaps.values())

    expected = {
        "form_type": FORM_TYPE,
        "payment_year": PAYMENT_YEAR,
        "record_length_positions": 750,
        "n_cases": N_CASES,
        "n_records": N_RECORDS,
        "n_field_groups": N_GROUPS,
        "group_keys": list(parse.GROUP_KEYS),
        "payee_refs": [p["payee_ref"] for p in PAYEES],
        "graded_output": ["records"],
        "method": "each payee's semantic record placed at the field positions the "
                  "published table fixes for this return type, with each field "
                  "justified and filled as that table requires, and graded by "
                  "slicing the submission back apart at those positions and "
                  "decoding every field to the value the payee data carries",
        "graded_quantity": "number of fields in the group that decode back to the "
                           "payee's own value; the reference is the group's own field "
                           "count and the tolerance admits no shortfall",
        "golden_records": goldens,
        "items": items,
        "control_gaps": control_gaps,
        "convention_variants": convention_variants,
        "smallest_wrong_path_gap_multiple": smallest_gap,
        "published_precision_ambiguity_mismatches_maxabs":
            float(worst_variant_faults),
        "published_precision_ambiguity_method":
            "re-derived through a second route and the worst disagreement taken: "
            "every reading of the publication that is equally faithful - either "
            "justification in the issuer's account-number field, and the "
            "carriage-return/line-feed terminator the last two positions permit - "
            "was rebuilt and re-graded, and the largest number of fields any of "
            "them failed to decode was recorded",
        "published_precision_ambiguity_note":
            "Zero by measurement, not by assertion. The publication fixes one "
            "spelling for every graded field except two, and both of those are "
            "decoded rather than byte-compared, so both permitted readings pass.",
        "tolerance_field_mismatches_abs": TOLERANCE,
        "tolerance_rationale":
            "The graded quantity is a count of fields that decode back to the "
            "payee's own value, so a group's reference is its own field count and "
            "the tolerance, 0.500, admits no shortfall while remaining a positive "
            "band rather than an equality test. LOWER BOUND (defensible-reading "
            "spread): zero, measured - the "
            "two readings the publication explicitly permits were rebuilt and "
            "re-graded and neither loses a field. UPPER BOUND (nearest wrong "
            "route): the closest recorded competing method is %s tolerances away "
            "on its widest group. The band is therefore wide enough that no "
            "faithful reading fails and narrow enough that no competing method "
            "passes." % ("%.3f" % smallest_gap),
        "seed": SEED,
    }
    for item in items:
        expected["ref_%s" % item["case_id"]] = item["ref"]
        expected["tolerance_%s_abs" % item["case_id"]] = item["tolerance"]

    os.makedirs(VERIFIER, exist_ok=True)
    with open(os.path.join(VERIFIER, "expected_values.json"), "w") as fh:
        json.dump(expected, fh, indent=2, sort_keys=True)
        fh.write("\n")

    print("records          : %d" % len(goldens))
    print("graded cases     : %d (prime: %s)"
          % (N_CASES, all(N_CASES % d for d in range(2, int(N_CASES ** 0.5) + 1))))
    print("tolerance        : %.3f field mismatches" % TOLERANCE)
    print("variant spread   : %d field mismatches (must be 0)" % worst_variant_faults)
    for name, entry in sorted(control_gaps.items()):
        print("  %-42s %8.3fx tol, %2d/%d graded cases failed"
              % (name, entry["field_mismatch_gap_over_tol"],
                 entry["graded_cases_failed_of_%d" % N_CASES], N_CASES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
