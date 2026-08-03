"""Reference emitter for the 750-position payee detail record of the IRS
electronic transmission specification (Publication 1220, Tax Year 2025 revision,
https://www.irs.gov/pub/irs-pdf/p1220.pdf).

This module is the ORACLE side. It builds a record FORWARD: it walks the field
table in order and concatenates each field's rendered text. The verifier never
imports it; `verifier/brecord_layout.py` carries a second, independently written
transcription of the same published table and grades by PARSING a record BACK
into semantic values.

Transcription source, field by field:
  * Part C, Sec. 3, "Record Name: Payee 'B' Record" — the field descriptions for
    positions 1-543, common to every return type.
  * Part C, Sec. 3 (18), "Payee 'B' Record - Record Layout Positions 544-750 for
    Form 1099-MISC" — the return-specific block.

Both tables print a Field Position range AND a Length column. The length column
is carried here as the third element of every row so that a mistyped start
cannot pass unnoticed: `check_table()` asserts the two agree, that the spans are
contiguous and non-overlapping, and that they total 750.
"""

# (name, start_position_1_based, published_length, kind)
STANDARD_BLOCK = [
    ("record_type",                     1,   1, "literal_B"),
    ("payment_year",                    2,   4, "payment_year"),
    ("corrected_return_indicator",      6,   1, "corrected"),
    ("name_control",                    7,   4, "alpha_left"),
    ("tin_type",                       11,   1, "tin_type"),
    ("payee_tin",                      12,   9, "digits"),
    ("issuer_account_number",          21,  20, "alpha_either"),
    ("issuer_office_code",             41,   4, "alpha_left"),
    ("blank_45_54",                    45,  10, "filler"),
    ("amount_1",                       55,  12, "amount"),
    ("amount_2",                       67,  12, "amount"),
    ("amount_3",                       79,  12, "amount"),
    ("amount_4",                       91,  12, "amount"),
    ("amount_5",                      103,  12, "amount"),
    ("amount_6",                      115,  12, "amount"),
    ("amount_7",                      127,  12, "amount"),
    ("amount_8",                      139,  12, "amount"),
    ("amount_9",                      151,  12, "amount"),
    ("amount_A",                      163,  12, "amount"),
    ("amount_B",                      175,  12, "amount"),
    ("amount_C",                      187,  12, "amount"),
    ("amount_D",                      199,  12, "amount"),
    ("amount_E",                      211,  12, "amount"),
    ("amount_F",                      223,  12, "amount"),
    ("amount_G",                      235,  12, "amount"),
    ("amount_H",                      247,  12, "amount"),
    ("amount_J",                      259,  12, "amount"),
    ("blank_271_286",                 271,  16, "filler"),
    ("foreign_country_indicator",     287,   1, "foreign"),
    ("first_payee_name_line",         288,  40, "alpha_left"),
    ("second_payee_name_line",        328,  40, "alpha_left"),
    ("payee_mailing_address",         368,  40, "alpha_left"),
    ("blank_408_447",                 408,  40, "filler"),
    ("payee_city",                    448,  40, "alpha_left"),
    ("payee_state",                   488,   2, "alpha_left"),
    ("payee_zip_code",                490,   9, "zip"),
    ("blank_499",                     499,   1, "filler"),
    ("record_sequence_number",        500,   8, "sequence"),
    ("blank_508_543",                 508,  36, "filler"),
]

# Return-specific block for Form 1099-MISC. The FATCA indicator at 548 is what
# separates this tail from the 1099-NEC tail, which runs blanks from 548 to 662.
MISC_TAIL = [
    ("second_tin_notice",             544,   1, "second_tin"),
    ("blank_545_546",                 545,   2, "filler"),
    ("direct_sales_indicator",        547,   1, "direct_sales"),
    ("fatca_filing_indicator",        548,   1, "fatca"),
    ("blank_549_662",                 549, 114, "filler"),
    ("special_data_entries",          663,  60, "alpha_left"),
    ("state_income_tax_withheld",     723,  12, "amount"),
    ("local_income_tax_withheld",     735,  12, "amount"),
    ("combined_federal_state_code",   747,   2, "cfsf"),
    ("blank_or_crlf_749_750",         749,   2, "filler"),
]

FIELDS = STANDARD_BLOCK + MISC_TAIL
RECORD_LENGTH = 750

AMOUNT_CODES = ["1", "2", "3", "4", "5", "6", "7", "8", "9",
                "A", "B", "C", "D", "E", "F", "G", "H", "J"]

CORRECTED_CODE = {
    "original": " ",
    "one-transaction correction": "G",
    "first of a two-transaction correction": "G",
    "second transaction of a two-transaction correction": "C",
}
TIN_TYPE_CODE = {"EIN": "1", "SSN": "2", "ITIN": "2", "ATIN": "2",
                 "not determinable": " "}


def check_table():
    """Standing tripwire on the transcription itself.

    Asserts the published Length column agrees with the published Field Position
    range for every row, that the rows are contiguous and non-overlapping, and
    that they total 750 positions. A single mistyped digit in either column
    breaks one of the three.
    """
    cursor = 1
    for name, start, length, _kind in FIELDS:
        if start != cursor:
            raise AssertionError(
                "field %s starts at %d but the preceding fields end at %d"
                % (name, start, cursor - 1))
        if length < 1:
            raise AssertionError("field %s has a non-positive length" % name)
        cursor += length
    if cursor - 1 != RECORD_LENGTH:
        raise AssertionError(
            "the field table spans %d positions, not %d" % (cursor - 1, RECORD_LENGTH))
    return True


def cents(amount_text):
    """Dollars-and-cents text to an integer number of cents, exactly.

    Parsed as text rather than through a float so that no binary rounding can
    move the last cent of a payment amount.
    """
    s = str(amount_text).strip()
    if s.startswith("-"):
        raise ValueError("negative payment amounts are not reportable on this form")
    if "." in s:
        whole, frac = s.split(".", 1)
    else:
        whole, frac = s, ""
    frac = (frac + "00")[:2]
    whole = whole or "0"
    if not whole.isdigit() or not frac.isdigit():
        raise ValueError("unparseable amount %r" % (amount_text,))
    return int(whole) * 100 + int(frac)


def _amount_field(amount_text, width):
    return str(cents(amount_text)).rjust(width, "0")


def _alpha_left(value, width):
    value = "" if value is None else str(value)
    if len(value) > width:
        raise ValueError("value %r overflows its %d-position field" % (value, width))
    return value.ljust(width)


def _zip_field(value, width):
    value = str(value)
    if len(value) not in (5, 9):
        raise ValueError("ZIP Code must be five or nine digits, got %r" % value)
    return value.ljust(width)


def render_field(name, length, kind, payee, payment_year):
    if kind == "literal_B":
        return "B"
    if kind == "payment_year":
        return _alpha_left(payment_year, length)
    if kind == "corrected":
        return CORRECTED_CODE[payee["correction_status"]]
    if kind == "tin_type":
        return TIN_TYPE_CODE[payee["tin_type"]]
    if kind == "digits":
        v = str(payee["payee_tin"])
        if len(v) != length or not v.isdigit():
            raise ValueError("taxpayer identification number must be %d digits" % length)
        return v
    if kind == "alpha_either":
        # The publication permits either justification in this field; the
        # reference solution left-justifies and the verifier accepts both.
        return _alpha_left(payee["issuer_account_number"], length)
    if kind == "foreign":
        return "1" if payee["foreign_address"] else " "
    if kind == "second_tin":
        return "2" if payee["second_tin_notice"] else " "
    if kind == "direct_sales":
        return "1" if payee["direct_sales_5000_or_more"] else " "
    if kind == "fatca":
        return "1" if payee["fatca_filing_requirement"] else " "
    if kind == "filler":
        return " " * length
    if kind == "zip":
        return _zip_field(payee["payee_zip_code"], length)
    if kind == "sequence":
        return str(int(payee["record_sequence_number"])).rjust(length, "0")
    if kind == "cfsf":
        code = payee.get("combined_federal_state_code") or ""
        return _alpha_left(code, length)
    if kind == "amount":
        if name.startswith("amount_"):
            code = name.split("_", 1)[1]
            return _amount_field(payee["payment_amounts"].get(code, "0.00"), length)
        return _amount_field(payee[name], length)
    if kind == "alpha_left":
        if name == "special_data_entries":
            return _alpha_left(payee.get("special_data_entries", ""), length)
        return _alpha_left(payee[name], length)
    raise KeyError("unknown field kind %r" % kind)


def emit_record(payee, payment_year):
    """Build one payee detail record, forward, field by field."""
    check_table()
    out = []
    for name, _start, length, kind in FIELDS:
        text = render_field(name, length, kind, payee, payment_year)
        if len(text) != length:
            raise AssertionError("field %s rendered %d positions, not %d"
                                 % (name, len(text), length))
        out.append(text)
    record = "".join(out)
    if len(record) != RECORD_LENGTH:
        raise AssertionError("record is %d positions, not %d"
                             % (len(record), RECORD_LENGTH))
    return record
