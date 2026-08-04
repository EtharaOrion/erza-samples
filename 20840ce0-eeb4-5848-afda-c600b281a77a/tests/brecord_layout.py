"""Verifier-side SECOND FORMULATION. Deliberately not the oracle's code.

The oracle builds a record FORWARD: it walks a field table in order and
concatenates each field's rendered text, so its table is a list of starts and
lengths consumed by a cursor. This module never renders anything. It carries an
INDEPENDENT transcription of the same published table, expressed as absolute
(first_position, last_position) pairs read off the publication's "Field
Position" column with the "Length" column kept beside them, and it grades by
PARSING A SUBMITTED RECORD BACK: each field is sliced at its own offsets,
decoded to a semantic value, and compared against the payee data the task
supplies.

Why that is a genuinely different formulation, and not a restatement:

  * A shared arithmetic slip cannot cancel. The oracle derives offsets by
    accumulating lengths; this module states them absolutely and then checks the
    lengths against them (`check_spans`). A mistyped start in one table and a
    mistyped length in the other cannot agree by construction.
  * It grades DECODED VALUES, not bytes. Nothing here compares a submission to
    the oracle's output, so a record that reaches the right semantic content by
    a different but permitted spelling - either justification in the issuer's
    account-number field, a five-digit ZIP Code blank-filled to nine, the
    carriage-return/line-feed variant the publication allows in the last two
    positions - passes, and a record whose bytes happen to match an oracle that
    was itself wrong does not.
  * Decoding surfaces errors emitting cannot. A field written right-justified
    where the publication requires left-justified blank-fill renders a plausible
    750-position record and fails to decode.

Transcription source: Internal Revenue Service, Publication 1220,
"Specifications for Electronic Filing of Forms 1097, 1098, 1099, 3921, 3922,
5498, and W-2G", Tax Year 2025 revision, https://www.irs.gov/pub/irs-pdf/p1220.pdf
 - Part C, Sec. 3 for positions 1-543 and Part C, Sec. 3 (18) for the Form
1099-MISC block at 544-750.
"""

from decimal import Decimal

RECORD_LENGTH = 750

# (field, first_position, last_position, published_length, reader)
# Positions are 1-based and inclusive, exactly as the publication prints them.
SPANS = [
    ("record_type",                     1,    1,   1, "record_type"),
    ("payment_year",                    2,    5,   4, "year"),
    ("corrected_return_indicator",      6,    6,   1, "correction_class"),
    ("name_control",                    7,   10,   4, "left_text"),
    ("tin_type",                       11,   11,   1, "tin_class"),
    ("payee_tin",                      12,   20,   9, "digit_string"),
    ("issuer_account_number",          21,   40,  20, "either_text"),
    ("issuer_office_code",             41,   44,   4, "left_text"),
    ("blank_45_54",                    45,   54,  10, "blank"),
    ("amount_1",                       55,   66,  12, "money"),
    ("amount_2",                       67,   78,  12, "money"),
    ("amount_3",                       79,   90,  12, "money"),
    ("amount_4",                       91,  102,  12, "money"),
    ("amount_5",                      103,  114,  12, "money"),
    ("amount_6",                      115,  126,  12, "money"),
    ("amount_7",                      127,  138,  12, "money"),
    ("amount_8",                      139,  150,  12, "money"),
    ("amount_9",                      151,  162,  12, "money"),
    ("amount_A",                      163,  174,  12, "money"),
    ("amount_B",                      175,  186,  12, "money"),
    ("amount_C",                      187,  198,  12, "money"),
    ("amount_D",                      199,  210,  12, "money"),
    ("amount_E",                      211,  222,  12, "money"),
    ("amount_F",                      223,  234,  12, "money"),
    ("amount_G",                      235,  246,  12, "money"),
    ("amount_H",                      247,  258,  12, "money"),
    ("amount_J",                      259,  270,  12, "money"),
    ("blank_271_286",                 271,  286,  16, "blank"),
    ("foreign_country_indicator",     287,  287,   1, "foreign_flag"),
    ("first_payee_name_line",         288,  327,  40, "left_text"),
    ("second_payee_name_line",        328,  367,  40, "left_text"),
    ("payee_mailing_address",         368,  407,  40, "left_text"),
    ("blank_408_447",                 408,  447,  40, "blank"),
    ("payee_city",                    448,  487,  40, "left_text"),
    ("payee_state",                   488,  489,   2, "left_text"),
    ("payee_zip_code",                490,  498,   9, "postal_code"),
    ("blank_499",                     499,  499,   1, "blank"),
    ("record_sequence_number",        500,  507,   8, "counter"),
    ("blank_508_543",                 508,  543,  36, "blank"),
    ("second_tin_notice",             544,  544,   1, "second_tin_flag"),
    ("blank_545_546",                 545,  546,   2, "blank"),
    ("direct_sales_indicator",        547,  547,   1, "direct_sales_flag"),
    ("fatca_filing_indicator",        548,  548,   1, "fatca_flag"),
    ("blank_549_662",                 549,  662, 114, "blank"),
    ("special_data_entries",          663,  722,  60, "left_text"),
    ("state_income_tax_withheld",     723,  734,  12, "money"),
    ("local_income_tax_withheld",     735,  746,  12, "money"),
    ("combined_federal_state_code",   747,  748,   2, "left_text"),
    ("blank_or_crlf_749_750",         749,  750,   2, "record_terminator"),
]

SPAN_BY_NAME = {row[0]: row for row in SPANS}

# The graded field groups, in record order. Every position of the record belongs
# to exactly one group; `check_spans` and the verifier's coverage test prove it.
#
# The grouping is not arbitrary. A run of reserved positions is never graded on
# its own: each one is carried in the same group as a neighbouring field that
# must hold content for EVERY payee, so a submission of 750 blanks - or of any
# constant character - cannot collect a graded case for free. That free-pass was
# measured at fourteen of forty-one cases under an earlier grouping and removed
# rather than documented away.
GROUPS = [
    ("head_1_54", ["record_type", "payment_year", "corrected_return_indicator",
                   "name_control", "tin_type", "payee_tin",
                   "issuer_account_number", "issuer_office_code", "blank_45_54"]),
    ("amounts_55_270", ["amount_1", "amount_2", "amount_3", "amount_4", "amount_5",
                        "amount_6", "amount_7", "amount_8", "amount_9", "amount_A",
                        "amount_B", "amount_C", "amount_D", "amount_E", "amount_F",
                        "amount_G", "amount_H", "amount_J"]),
    ("reserved_and_first_name_271_327", ["blank_271_286",
                                         "foreign_country_indicator",
                                         "first_payee_name_line"]),
    ("second_name_and_address_328_407", ["second_payee_name_line",
                                         "payee_mailing_address"]),
    ("reserved_and_city_408_487", ["blank_408_447", "payee_city"]),
    ("state_and_postal_488_498", ["payee_state", "payee_zip_code"]),
    ("reserved_and_counter_499_543", ["blank_499", "record_sequence_number",
                                      "blank_508_543"]),
    ("indicators_and_reserved_544_662", ["second_tin_notice", "blank_545_546",
                                         "direct_sales_indicator",
                                         "fatca_filing_indicator",
                                         "blank_549_662"]),
    ("free_text_and_state_withholding_663_734", ["special_data_entries",
                                                 "state_income_tax_withheld"]),
    ("local_withholding_and_program_code_735_750",
     ["local_income_tax_withheld", "combined_federal_state_code",
      "blank_or_crlf_749_750"]),
]

GROUP_KEYS = [k for k, _ in GROUPS]

CORRECTION_CLASS_FROM_CODE = {" ": "ORIGINAL", "G": "CORRECTION_FIRST_OR_ONLY",
                              "C": "CORRECTION_SECOND_OF_TWO"}
CORRECTION_CLASS_FROM_STATUS = {
    "original": "ORIGINAL",
    "one-transaction correction": "CORRECTION_FIRST_OR_ONLY",
    "first of a two-transaction correction": "CORRECTION_FIRST_OR_ONLY",
    "second transaction of a two-transaction correction": "CORRECTION_SECOND_OF_TWO",
}
TIN_CLASS_FROM_CODE = {"1": "ENTITY", "2": "PERSON", " ": "UNDETERMINED"}
TIN_CLASS_FROM_KIND = {"EIN": "ENTITY", "SSN": "PERSON", "ITIN": "PERSON",
                       "ATIN": "PERSON", "not determinable": "UNDETERMINED"}

AMOUNT_CODE_FIELDS = [name for name, *_rest in SPANS if name.startswith("amount_")]


class FieldError(Exception):
    """The slice at a field's offsets cannot be decoded as that field."""


def check_spans():
    """Standing tripwire on the table itself, asserted on every graded run.

    Three independent properties, each of which a transcription error breaks:

      1. every published length equals last - first + 1;
      2. the spans are CONTIGUOUS and NON-OVERLAPPING - each field begins one
         position after the previous field ends;
      3. the record is exactly 750 positions.

    A wrong start caught by (1) needs a compensating wrong length to survive,
    and that compensating length is then caught by (2).
    """
    previous_end = 0
    for name, first, last, length, _reader in SPANS:
        if last - first + 1 != length:
            raise AssertionError(
                "%s: positions %d-%d span %d, but the published length is %d"
                % (name, first, last, last - first + 1, length))
        if first != previous_end + 1:
            raise AssertionError(
                "%s begins at %d; the previous field ends at %d, so the table is "
                "not contiguous" % (name, first, previous_end))
        previous_end = last
    if previous_end != RECORD_LENGTH:
        raise AssertionError("the table ends at position %d, not %d"
                             % (previous_end, RECORD_LENGTH))
    covered = sum(length for _n, _f, _l, length, _r in SPANS)
    if covered != RECORD_LENGTH:
        raise AssertionError("the published lengths total %d, not %d"
                             % (covered, RECORD_LENGTH))
    return True


def slice_of(record, name):
    _n, first, last, _length, _reader = SPAN_BY_NAME[name]
    return record[first - 1:last]


# --------------------------------------------------------------------------- #
# Readers. Each takes the slice and returns the semantic value it encodes, or
# raises FieldError when the slice is not a well-formed instance of that field.
# --------------------------------------------------------------------------- #

def _read_blank(text):
    if text.strip(" ") != "":
        raise FieldError("reserved positions carry %r, not blanks" % text)
    return "RESERVED"


def _read_left_text(text):
    value = text.rstrip(" ")
    if value != text[:len(value)] or text != value + " " * (len(text) - len(value)):
        raise FieldError("not left-justified and blank-filled: %r" % text)
    if value.startswith(" "):
        raise FieldError("leading blanks in a left-justified field: %r" % text)
    return value


def _read_either_text(text):
    value = text.strip(" ")
    width = len(text)
    if text not in (value.ljust(width), value.rjust(width)):
        raise FieldError("neither left- nor right-justified with blank fill: %r" % text)
    return value


def _read_digit_string(text):
    if not text.isdigit():
        raise FieldError("expected only digits, got %r" % text)
    return text


def _read_money(text):
    if not text.isdigit():
        raise FieldError("a payment amount field must be all digits, got %r" % text)
    return Decimal(text) / Decimal(100)


def _read_counter(text):
    if not text.isdigit():
        raise FieldError("a sequence number must be all digits, got %r" % text)
    return int(text.lstrip("0") or "0")


def _read_postal_code(text):
    value = text.rstrip(" ")
    if text != value.ljust(len(text)):
        raise FieldError("postal code is not left-justified: %r" % text)
    if not value.isdigit() or len(value) not in (5, 9):
        raise FieldError("postal code %r is neither five nor nine digits" % value)
    return value


def _read_record_type(text):
    if text != "B":
        raise FieldError("record type is %r, not the payee detail type" % text)
    return "PAYEE_DETAIL"


def _read_year(text):
    if not text.isdigit() or len(text) != 4:
        raise FieldError("payment year %r is not four digits" % text)
    return text


def _read_correction_class(text):
    if text not in CORRECTION_CLASS_FROM_CODE:
        raise FieldError("unknown correction indicator %r" % text)
    return CORRECTION_CLASS_FROM_CODE[text]


def _read_tin_class(text):
    if text not in TIN_CLASS_FROM_CODE:
        raise FieldError("unknown taxpayer-number type %r" % text)
    return TIN_CLASS_FROM_CODE[text]


def _flag_reader(true_code, label):
    def reader(text):
        if text == true_code:
            return True
        if text == " ":
            return False
        raise FieldError("%s must carry %r or a blank, got %r"
                         % (label, true_code, text))
    return reader


def _read_terminator(text):
    if text not in ("  ", "\r\n"):
        raise FieldError("the last two positions must be blanks or CR/LF, got %r" % text)
    return "END"


READERS = {
    "blank": _read_blank,
    "left_text": _read_left_text,
    "either_text": _read_either_text,
    "digit_string": _read_digit_string,
    "money": _read_money,
    "counter": _read_counter,
    "postal_code": _read_postal_code,
    "record_type": _read_record_type,
    "year": _read_year,
    "correction_class": _read_correction_class,
    "tin_class": _read_tin_class,
    "foreign_flag": _flag_reader("1", "the foreign-address indicator"),
    "second_tin_flag": _flag_reader("2", "the repeated-notice indicator"),
    "direct_sales_flag": _flag_reader("1", "the direct-sales indicator"),
    "fatca_flag": _flag_reader("1", "the account-reporting indicator"),
    "record_terminator": _read_terminator,
}


# --------------------------------------------------------------------------- #
# What each field must decode TO, taken from the payee data the task supplies.
# --------------------------------------------------------------------------- #

def _money_of(text):
    return Decimal(str(text).strip())


def wanted(name, payee, payment_year):
    if name == "record_type":
        return "PAYEE_DETAIL"
    if name == "payment_year":
        return str(payment_year)
    if name == "corrected_return_indicator":
        return CORRECTION_CLASS_FROM_STATUS[payee["correction_status"]]
    if name == "tin_type":
        return TIN_CLASS_FROM_KIND[payee["tin_type"]]
    if name == "payee_tin":
        return str(payee["payee_tin"])
    if name == "issuer_account_number":
        return str(payee["issuer_account_number"])
    if name == "issuer_office_code":
        return str(payee["issuer_office_code"])
    if name == "foreign_country_indicator":
        return bool(payee["foreign_address"])
    if name == "second_tin_notice":
        return bool(payee["second_tin_notice"])
    if name == "direct_sales_indicator":
        return bool(payee["direct_sales_5000_or_more"])
    if name == "fatca_filing_indicator":
        return bool(payee["fatca_filing_requirement"])
    if name == "record_sequence_number":
        return int(payee["record_sequence_number"])
    if name == "payee_zip_code":
        return str(payee["payee_zip_code"])
    if name == "special_data_entries":
        return str(payee.get("special_data_entries", ""))
    if name == "combined_federal_state_code":
        return str(payee.get("combined_federal_state_code") or "")
    if name == "blank_or_crlf_749_750":
        return "END"
    if name.startswith("blank_"):
        return "RESERVED"
    if name.startswith("amount_"):
        code = name.split("_", 1)[1]
        return _money_of(payee["payment_amounts"].get(code, "0.00"))
    if name in ("state_income_tax_withheld", "local_income_tax_withheld"):
        return _money_of(payee[name])
    return str(payee[name])


def decode_field(record, name):
    """Semantic value carried at this field's own offsets, or FieldError."""
    _n, _f, _l, _len, reader = SPAN_BY_NAME[name]
    return READERS[reader](slice_of(record, name))


def field_matches(record, group_key, payee, payment_year):
    """How many fields of this group decode back to the payee's own value.

    This is the graded quantity: the reference for a group is its own field
    count, and the tolerance admits no shortfall. Counting matches rather than
    faults keeps the reference a property of the group rather than a uniform
    zero, so a submission that fails to be parsed at all can never coincide with
    it by accident.
    """
    fields = dict(GROUPS)[group_key]
    return len(fields) - len(field_faults(record, group_key, payee, payment_year))


def field_faults(record, group_key, payee, payment_year):
    """Fields in this group whose decoded value is not the payee's own value.

    Returns a list of (field, explanation), for diagnosis and for the control
    ledger. `field_matches` is the graded view of the same computation.
    """
    fields = dict(GROUPS)[group_key]
    faults = []
    for name in fields:
        try:
            got = decode_field(record, name)
        except FieldError as exc:
            faults.append((name, str(exc)))
            continue
        want = wanted(name, payee, payment_year)
        if isinstance(want, Decimal) and isinstance(got, Decimal):
            same = got == want
        else:
            same = got == want
        if not same:
            faults.append((name, "decodes to %r, but the payee record carries %r"
                           % (got, want)))
    return faults
