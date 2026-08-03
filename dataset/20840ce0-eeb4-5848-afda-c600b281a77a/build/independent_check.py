"""Supplementary independent check. Runs from the shipped bundle, no network.

Section 6.1 puts the load-bearing second formulation INSIDE the verifier, where
it runs on every graded run and cannot rot: `verifier/brecord_layout.py` slices
each submitted record apart at its own independently transcribed offsets and
decodes every field back to a semantic value. This file is a supplement, not the
anchor, and it takes a FOURTH route on purpose.

The oracle emits by walking a table of starts and lengths with a cursor. The
verifier decodes by absolute `(first, last)` pairs. The process verifier's
rederivation test accumulates a length-only column. This module does the one
remaining thing none of them does: it rebuilds every golden record by writing
each field into a pre-sized buffer at an absolute offset taken from the
publication's Field Position column, in an order deliberately unrelated to the
record's own - the fields are placed back-to-front - and requires the result to
be byte-identical to the frozen golden. Placing in reverse order means any
implicit reliance on one field's end to locate the next one's start would show
up immediately.

It also states the plausibility envelope and checks the golden against it, and
re-measures the two readings of the specification that must not false-fail.

    python3 build/independent_check.py        # exit 0 when everything agrees

Every path resolves relative to this file's own bundle, and everything it needs
is inside the bundle, so it runs from `dataset/<uuid>/` exactly as it runs from
`harness/tasks/<slug>/`.
"""

import json
import os
import sys
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import brecord_layout as parse  # noqa: E402

RECORD_LENGTH = 750

# Absolute start positions, transcribed a fourth time from the publication's
# Field Position column: Internal Revenue Service, Publication 1220, Tax Year
# 2025 revision, https://www.irs.gov/pub/irs-pdf/p1220.pdf, Part C, Sec. 3 and
# Sec. 3 (18).
START = {
    "record_type": 1, "payment_year": 2, "corrected_return_indicator": 6,
    "name_control": 7, "tin_type": 11, "payee_tin": 12,
    "issuer_account_number": 21, "issuer_office_code": 41, "blank_45_54": 45,
    "amount_1": 55, "amount_2": 67, "amount_3": 79, "amount_4": 91,
    "amount_5": 103, "amount_6": 115, "amount_7": 127, "amount_8": 139,
    "amount_9": 151, "amount_A": 163, "amount_B": 175, "amount_C": 187,
    "amount_D": 199, "amount_E": 211, "amount_F": 223, "amount_G": 235,
    "amount_H": 247, "amount_J": 259, "blank_271_286": 271,
    "foreign_country_indicator": 287, "first_payee_name_line": 288,
    "second_payee_name_line": 328, "payee_mailing_address": 368,
    "blank_408_447": 408, "payee_city": 448, "payee_state": 488,
    "payee_zip_code": 490, "blank_499": 499, "record_sequence_number": 500,
    "blank_508_543": 508, "second_tin_notice": 544, "blank_545_546": 545,
    "direct_sales_indicator": 547, "fatca_filing_indicator": 548,
    "blank_549_662": 549, "special_data_entries": 663,
    "state_income_tax_withheld": 723, "local_income_tax_withheld": 735,
    "combined_federal_state_code": 747, "blank_or_crlf_749_750": 749,
}
WIDTH = {
    "record_type": 1, "payment_year": 4, "corrected_return_indicator": 1,
    "name_control": 4, "tin_type": 1, "payee_tin": 9,
    "issuer_account_number": 20, "issuer_office_code": 4, "blank_45_54": 10,
    "blank_271_286": 16, "foreign_country_indicator": 1,
    "first_payee_name_line": 40, "second_payee_name_line": 40,
    "payee_mailing_address": 40, "blank_408_447": 40, "payee_city": 40,
    "payee_state": 2, "payee_zip_code": 9, "blank_499": 1,
    "record_sequence_number": 8, "blank_508_543": 36, "second_tin_notice": 1,
    "blank_545_546": 2, "direct_sales_indicator": 1,
    "fatca_filing_indicator": 1, "blank_549_662": 114,
    "special_data_entries": 60, "state_income_tax_withheld": 12,
    "local_income_tax_withheld": 12, "combined_federal_state_code": 2,
    "blank_or_crlf_749_750": 2,
}
for _code in ("1", "2", "3", "4", "5", "6", "7", "8", "9",
              "A", "B", "C", "D", "E", "F", "G", "H", "J"):
    WIDTH["amount_" + _code] = 12

CORRECTED = {"original": " ",
             "one-transaction correction": "G",
             "first of a two-transaction correction": "G",
             "second transaction of a two-transaction correction": "C"}
TIN_TYPE = {"EIN": "1", "SSN": "2", "ITIN": "2", "ATIN": "2",
            "not determinable": " "}


def whole_cents(text):
    return int(Decimal(str(text).strip()) * 100)


def field_text(name, payee, year):
    width = WIDTH[name]
    if name == "record_type":
        return "B"
    if name == "payment_year":
        return str(year).ljust(width)
    if name == "corrected_return_indicator":
        return CORRECTED[payee["correction_status"]]
    if name == "tin_type":
        return TIN_TYPE[payee["tin_type"]]
    if name == "payee_tin":
        return str(payee["payee_tin"])
    if name == "issuer_account_number":
        return str(payee["issuer_account_number"]).ljust(width)
    if name == "issuer_office_code":
        return str(payee["issuer_office_code"]).ljust(width)
    if name == "foreign_country_indicator":
        return "1" if payee["foreign_address"] else " "
    if name == "second_tin_notice":
        return "2" if payee["second_tin_notice"] else " "
    if name == "direct_sales_indicator":
        return "1" if payee["direct_sales_5000_or_more"] else " "
    if name == "fatca_filing_indicator":
        return "1" if payee["fatca_filing_requirement"] else " "
    if name == "record_sequence_number":
        return str(int(payee["record_sequence_number"])).rjust(width, "0")
    if name == "payee_zip_code":
        return str(payee["payee_zip_code"]).ljust(width)
    if name == "combined_federal_state_code":
        return str(payee.get("combined_federal_state_code") or "").ljust(width)
    if name == "special_data_entries":
        return str(payee.get("special_data_entries", "")).ljust(width)
    if name.startswith("blank_"):
        return " " * width
    if name.startswith("amount_"):
        code = name.split("_", 1)[1]
        return str(whole_cents(
            payee["payment_amounts"].get(code, "0.00"))).rjust(width, "0")
    if name in ("state_income_tax_withheld", "local_income_tax_withheld"):
        return str(whole_cents(payee[name])).rjust(width, "0")
    return str(payee[name]).ljust(width)


def rebuild(payee, year):
    """Write every field into a pre-sized buffer at its absolute offset, LAST
    field first, so nothing can implicitly depend on the previous field's end."""
    buf = [None] * RECORD_LENGTH
    for name in sorted(START, key=lambda n: -START[n]):
        text = field_text(name, payee, year)
        first, width = START[name], WIDTH[name]
        if len(text) != width:
            raise AssertionError("%s rendered %d positions, not %d"
                                 % (name, len(text), width))
        for i, ch in enumerate(text):
            slot = first - 1 + i
            if buf[slot] is not None:
                raise AssertionError("%s overwrites position %d" % (name, slot + 1))
            buf[slot] = ch
    if any(ch is None for ch in buf):
        holes = [i + 1 for i, ch in enumerate(buf) if ch is None]
        raise AssertionError("positions %r are covered by no field" % holes[:8])
    return "".join(buf)


def main():
    with open(os.path.join(ROOT, "environment", "data", "payees.json")) as fh:
        payees = json.load(fh)["payees"]
    with open(os.path.join(ROOT, "tests", "expected_values.json")) as fh:
        exp = json.load(fh)
    year = exp["payment_year"]

    parse.check_spans()
    print("verifier field table  : contiguous, non-overlapping, totals %d"
          % RECORD_LENGTH)

    worst = 0
    for payee in payees:
        ref = payee["payee_ref"]
        mine = rebuild(payee, year)
        frozen = exp["golden_records"][ref]
        if len(mine) != RECORD_LENGTH:
            raise AssertionError("%s rebuilt to %d positions" % (ref, len(mine)))
        diff = sum(1 for a, b in zip(mine, frozen) if a != b)
        worst = max(worst, diff)
        print("  %-6s rebuilt back-to-front: %d position(s) differ from the "
              "frozen golden" % (ref, diff))
        if diff:
            first_bad = next(i for i, (a, b) in enumerate(zip(mine, frozen))
                             if a != b)
            raise AssertionError(
                "%s first disagrees at position %d: rebuilt %r, frozen %r"
                % (ref, first_bad + 1, mine[first_bad], frozen[first_bad]))

    # Plausibility envelope. The graded quantity is a count of fields that
    # decode back to the payee's own value, so the expected range for a group is
    # 0 to that group's own field count, and the golden must sit at the top of
    # it: full conformance, which is what a byte-exact task means.
    largest_group = max(len(fields) for _k, fields in parse.GROUPS)
    groups = dict(parse.GROUPS)
    for item in exp["items"]:
        hi = (len(groups[item["group"]]) if item["kind"] == "field_group"
              else len(exp["payee_refs"]))
        if not 0 <= item["ref"] <= hi:
            raise AssertionError("reference for %s outside the plausible range "
                                 "[0, %d]" % (item["case_id"], hi))
        if item["ref"] != hi:
            raise AssertionError("reference for %s is %r, not full conformance "
                                 "(%d)" % (item["case_id"], item["ref"], hi))
    print("plausibility envelope : every reference in [0, %d] and every one sits "
          "at full conformance for its group" % largest_group)

    # The two readings of the specification that must not false-fail.
    payee_by_ref = {p["payee_ref"]: p for p in payees}
    spread = 0
    for ref, record in exp["golden_records"].items():
        payee = payee_by_ref[ref]
        variants = (
            record[:20] + str(payee["issuer_account_number"]).rjust(20) + record[40:],
            record[:748] + "\r\n",
        )
        for variant in variants:
            for group in parse.GROUP_KEYS:
                spread = max(spread, len(parse.field_faults(
                    variant, group, payee, year)))
    print("permitted readings    : worst disagreement %d field(s) (recorded band "
          "%g)" % (spread, exp["published_precision_ambiguity_mismatches_maxabs"]))
    if spread != exp["published_precision_ambiguity_mismatches_maxabs"]:
        raise AssertionError("the recorded ambiguity band does not reproduce")

    print("OK: the fourth formulation reproduces every frozen record exactly "
          "(worst disagreement %d positions)" % worst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
