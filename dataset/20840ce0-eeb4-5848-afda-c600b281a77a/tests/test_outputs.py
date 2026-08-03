"""Outcome verifier for information-return-brecord-emission.

Deterministic. Grades /root/results.json against the payee data baked into the
image. The scored tests are `test_graded_case[...]`; everything below the
divider is a grader self-check and is excluded from the reward by test.sh, which
also GATES the run on them.

Section 6.1 compliance. This module never imports the oracle's emitter and never
compares a submission to the oracle's output. It grades by PARSING THE
SUBMISSION BACK: `brecord_layout` carries a second, independently written
transcription of the published field table - absolute (first, last) position
pairs with the published length beside them, rather than the oracle's cursor
over a list of lengths - slices every field at its own offsets, decodes it to a
semantic value, and compares that value against the payee record the task
supplies. A shared offset error cannot survive, because `check_spans` asserts
the two columns of the published table against each other, that the spans are
contiguous and non-overlapping, and that they total 750 positions, and that
tripwire runs on every graded run rather than only at build time.

Grading by decode rather than by bytes is also what keeps the tolerance honest:
the two readings the publication explicitly permits - either justification in
the issuer's account-number field, and the carriage-return/line-feed terminator
in the last two positions - decode to the same values and therefore pass.
"""

import json
import math
import os
import re
import sys

import pytest

VER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, VER)
import brecord_layout as parse  # noqa: E402

EXP = json.load(open(os.path.join(VER, "expected_values.json")))
ITEMS = EXP["items"]


def _data_dir():
    """The baked inputs. `/root/data` in the container; the bundle's own copy
    when the suite is run from a checkout, so a collection error can never be
    mistaken for a grading result."""
    explicit = os.environ.get("DATA_DIR")
    if explicit:
        return explicit
    if os.path.isdir("/root/data"):
        return "/root/data"
    return os.path.join(os.path.dirname(VER), "environment", "data")


DATA = _data_dir()
RESULTS_PATH = os.environ.get("RESULTS_PATH", "/root/results.json")
RECORD_LENGTH = EXP["record_length_positions"]
PAYMENT_YEAR = EXP["payment_year"]

PRINTABLE = re.compile(r"^[\x20-\x7e]*$")


def _payees():
    with open(os.path.join(DATA, "payees.json")) as fh:
        return {p["payee_ref"]: p for p in json.load(fh)["payees"]}


PAYEES = _payees()
REFS = EXP["payee_refs"]


def _load_results():
    """The submission, or a shape that scores 0 without raising."""
    if not os.path.isfile(RESULTS_PATH):
        return None
    try:
        with open(RESULTS_PATH) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def submitted_records(results):
    """{payee_ref: record} for every well-typed entry the submission carries."""
    if not isinstance(results, dict):
        return {}
    node = results.get("records")
    if not isinstance(node, dict):
        return {}
    out = {}
    for key, value in node.items():
        if isinstance(value, str):
            out[str(key)] = value
    return out


def group_matches(results, payee_ref, group):
    """How many fields of this group decode back to the payee's own value."""
    records = submitted_records(results)
    record = records.get(payee_ref)
    if record is None or len(record) != RECORD_LENGTH:
        return 0
    return parse.field_matches(record, group, PAYEES[payee_ref], PAYMENT_YEAR)


def well_formed_records(results):
    """Well-formedness of the answer file, independent of where fields sit.

    One entry per payee reference and no others; each a string of exactly the
    declared length; every character printable and, where alphabetic, upper
    case; and the last two positions carrying one of the two terminators the
    specification admits. Extra entries count against the total, so a
    submission cannot buy the case by padding the object out.

    This is the case a run that has committed to an answer collects without
    knowing the field map. It is deliberately one case out of thirty-one: a task
    that no-skill cannot ANSWER is a defect, only one it cannot get RIGHT is the
    point.
    """
    if not isinstance(results, dict):
        return 0
    node = results.get("records")
    if not isinstance(node, dict):
        return 0
    good = 0
    for ref in REFS:
        value = node.get(ref)
        if not isinstance(value, str) or len(value) != RECORD_LENGTH:
            continue
        body, terminator = value[:748], value[748:]
        if not PRINTABLE.match(body) or body != body.upper():
            continue
        if terminator not in ("  ", "\r\n"):
            continue
        good += 1
    extras = len([k for k in node if str(k) not in REFS])
    return max(0, good - extras)


def measure(results, item):
    if item["kind"] == "field_group":
        return group_matches(results, item["payee_ref"], item["group"])
    return well_formed_records(results)


@pytest.mark.parametrize("item", ITEMS, ids=[i["case_id"] for i in ITEMS])
def test_graded_case(item):
    results = _load_results()
    assert results is not None, \
        "%s is missing, empty or not valid JSON" % RESULTS_PATH
    got = float(measure(results, item))
    assert not math.isnan(got) and not math.isinf(got)
    ref, tol = float(item["ref"]), float(item["tolerance"])
    if item["kind"] == "field_group":
        records = submitted_records(results)
        record = records.get(item["payee_ref"])
        detail = ""
        if record is not None and len(record) == RECORD_LENGTH:
            faults = parse.field_faults(record, item["group"],
                                        PAYEES[item["payee_ref"]], PAYMENT_YEAR)
            detail = "; ".join("%s %s" % (n, why) for n, why in faults[:4])
        elif record is None:
            detail = "no record supplied for this payee"
        else:
            detail = "record is %d positions, not %d" % (len(record), RECORD_LENGTH)
        assert abs(got - ref) <= tol, \
            "%s: %g of %g field(s) decode back to the payee record - %s" % (
                item["case_id"], got, ref, detail)
    else:
        assert abs(got - ref) <= tol, \
            "%s: %g of %g records are well formed" % (
                item["case_id"], got, ref)


# ---- grader self-checks (NOT scored; test.sh GATES the run on them) ---------

def test_field_table_is_contiguous_and_totals_750():
    """Standing tripwire on the transcription itself.

    Every published length must equal its own position range, the ranges must be
    contiguous and non-overlapping, and they must total exactly 750 positions.
    A mistyped start needs a compensating mistyped length to survive the first
    assertion, and that compensation is caught by the second. This is the check
    that a byte-identical copy of the oracle's table could not provide.
    """
    assert parse.check_spans()
    assert parse.SPANS[0][1] == 1, "the table does not start at position 1"
    assert parse.SPANS[-1][2] == RECORD_LENGTH, "the table does not end at 750"
    seen = set()
    for name, first, last, _length, _reader in parse.SPANS:
        span = set(range(first, last + 1))
        assert not (span & seen), "%s overlaps an earlier field" % name
        seen |= span
    assert len(seen) == RECORD_LENGTH, \
        "the table covers %d positions, not %d" % (len(seen), RECORD_LENGTH)


def test_every_position_belongs_to_exactly_one_graded_group():
    """Grading must cover the whole record, not only its memorable opening.

    Also records the weighting the task is built on: recall of this
    specification is real for the first few dozen positions and decays after,
    so most of the graded mass has to sit past the payment-amount block.
    """
    covered = set()
    for _key, fields in parse.GROUPS:
        for name in fields:
            _n, first, last, _len, _r = parse.SPAN_BY_NAME[name]
            span = set(range(first, last + 1))
            assert not (span & covered), "%s is graded twice" % name
            covered |= span
    assert len(covered) == RECORD_LENGTH, \
        "the graded groups cover %d positions, not %d" % (len(covered), RECORD_LENGTH)
    late = [k for k, fields in parse.GROUPS
            if parse.SPAN_BY_NAME[fields[0]][1] > 247]
    assert len(late) * 2 >= len(parse.GROUPS), \
        "fewer than half the graded groups begin past position 247"


def test_frozen_golden_records_decode_to_the_payee_data():
    """The stored reference reproduces through the INDEPENDENT formulation.

    Nothing here evaluates the oracle's emitter. Every frozen record is sliced
    apart at this module's own offsets and every field is decoded back to a
    semantic value, which must equal the value the shipped payee record carries.
    """
    for ref in REFS:
        record = EXP["golden_records"][ref]
        assert len(record) == RECORD_LENGTH, \
            "frozen golden %s is %d positions" % (ref, len(record))
        for group in parse.GROUP_KEYS:
            faults = parse.field_faults(record, group, PAYEES[ref], PAYMENT_YEAR)
            assert not faults, \
                "freeze drift at %s/%s: %r" % (ref, group, faults[:3])


def test_permitted_readings_of_the_specification_do_not_false_fail():
    """The two variants the publication explicitly allows must both pass.

    A tolerance that fails a faithful reading manufactures a floor that looks
    like a lever. Both variants are rebuilt here and re-graded, and the recorded
    ambiguity band is asserted against the tolerance.
    """
    for ref in REFS:
        payee, golden = PAYEES[ref], EXP["golden_records"][ref]
        value = str(payee["issuer_account_number"])
        right = golden[:20] + value.rjust(20) + golden[40:]
        crlf = golden[:748] + "\r\n"
        for variant, label in ((right, "right-justified account number"),
                               (crlf, "CR/LF terminator")):
            assert len(variant) == RECORD_LENGTH
            for group in parse.GROUP_KEYS:
                faults = parse.field_faults(variant, group, payee, PAYMENT_YEAR)
                assert not faults, \
                    "%s false-fails %s at %s: %r" % (label, ref, group, faults[:2])
    band = EXP["published_precision_ambiguity_mismatches_maxabs"]
    tol = EXP["tolerance_field_mismatches_abs"]
    assert band < tol, "a faithful reading would false-fail"


def test_control_paths_are_measured_live_and_clear_the_tolerance():
    """The ledger's separation, recomputed here rather than trusted.

    Each control is rebuilt from the shipped payee data and re-graded through
    the same decode path a submission goes through, and its recorded multiple
    must match. The nearest real competitor must clear the tolerance by at least
    two, and at least one path must be decisively caught.
    """
    gaps = EXP["control_gaps"]
    live = {}
    for name in gaps:
        worst = 0
        for ref in REFS:
            payee = PAYEES[ref]
            submission = _control_record(name, ref, payee)
            for group in parse.GROUP_KEYS:
                if len(submission) != RECORD_LENGTH:
                    worst = max(worst, len(dict(parse.GROUPS)[group]))
                    continue
                worst = max(worst, len(parse.field_faults(
                    submission, group, payee, PAYMENT_YEAR)))
        live[name] = worst / EXP["tolerance_field_mismatches_abs"]
    for name, entry in gaps.items():
        assert abs(live[name] - entry["field_mismatch_gap_over_tol"]) <= 1e-09, \
            "%s: ledger says %.3fx, live recompute says %.3fx" % (
                name, entry["field_mismatch_gap_over_tol"], live[name])
        if entry.get("nearest_real_competitor"):
            assert live[name] >= 2.0, \
                "%s is the nearest real competitor and sits at %.2fx" % (name, live[name])
    assert max(live.values()) >= 2.0, "no control path is decisively caught"


def _control_record(name, ref, payee):
    """Rebuild one control path from the shipped data, verifier-side.

    Written here rather than imported from build/, so the ledger is checked
    against an independent construction of the same wrong route.
    """
    golden = EXP["golden_records"][ref]
    if name == "missing_form_specific_tail":
        return golden[:543] + " " * 207
    if name == "nec_tail_instead_of_misc":
        return golden[:547] + " " + golden[548:]
    if name == "reserved_runs_zero_filled":
        out = list(golden)
        for fname, first, last, _len, _r in parse.SPANS:
            if fname.startswith("blank_"):
                for i in range(first - 1, last):
                    out[i] = "0"
        return "".join(out)
    if name == "shifted_name_and_address_block":
        keep = []
        for fname, first, last, _len, _r in parse.SPANS:
            if fname in ("blank_271_286", "blank_408_447"):
                continue
            keep.append(golden[first - 1:last])
        return _fit("".join(keep))
    if name == "left_justified_amount_fields":
        out = []
        for fname, first, last, length, _r in parse.SPANS:
            if fname.startswith("amount_"):
                code = fname.split("_", 1)[1]
                out.append(str(payee["payment_amounts"].get(code, "0.00")).ljust(length))
            elif fname in ("state_income_tax_withheld", "local_income_tax_withheld"):
                out.append(str(payee[fname]).ljust(length))
            else:
                out.append(golden[first - 1:last])
        return _fit("".join(out))
    if name == "comma_delimited_instead_of_fixed_width":
        with open(os.path.join(DATA, "question.json")) as fh:
            question = json.load(fh)
        return _fit(question["decoy_reference"]["delimited_rendering"][ref])
    raise KeyError("no verifier-side construction for control path %r" % name)


def _fit(text):
    return text[:RECORD_LENGTH] if len(text) >= RECORD_LENGTH \
        else text.ljust(RECORD_LENGTH)


def test_plausibility_envelope_and_guess_resistance():
    """Degenerate and copied answers must score zero on every graded case.

    The plausible range for the graded quantity is closed and small: a field
    group can have between 0 and len(group) fields decode correctly, so every
    measurement lies in [0, 18] and the reference sits at the top of it, which
    is what a conformance task means. Anything a run can emit without doing the
    placement must land below it by more than the tolerance.
    """
    for item in ITEMS:
        hi = (len(dict(parse.GROUPS)[item["group"]])
              if item["kind"] == "field_group" else len(REFS))
        assert 0 <= item["ref"] <= hi, "reference outside the plausible range"
        assert item["ref"] == hi, \
            "%s: the reference must be full conformance for that group" % item["case_id"]

    blank = {"records": {ref: " " * RECORD_LENGTH for ref in REFS}}
    placeholder = {"records": {ref: "Z" * RECORD_LENGTH for ref in REFS}}
    zeros = {"records": {ref: "0" * RECORD_LENGTH for ref in REFS}}
    with open(os.path.join(DATA, "question.json")) as fh:
        decoy = json.load(fh)["decoy_reference"]["delimited_rendering"]
    echoed = {"records": {ref: _fit(decoy[ref]) for ref in REFS}}
    for label, guess in (("all blanks", blank), ("the prompt placeholder", placeholder),
                         ("all zeros", zeros), ("the orientation extract", echoed)):
        passed = [i["case_id"] for i in ITEMS
                  if i["kind"] == "field_group"
                  and abs(measure(guess, i) - i["ref"]) <= i["tolerance"]]
        assert not passed, "%s passes %d graded field-group case(s): %r" % (
            label, len(passed), passed[:4])
    # Only a submission that is well-formed collects the well-formedness case,
    # and it collects nothing else. Recorded rather than assumed, because a
    # partial-credit floor a run can reach without doing the work is exactly
    # what compresses the measurement.
    file_case = [i for i in ITEMS if i["kind"] == "file_level"][0]
    assert measure(blank, file_case) == file_case["ref"], \
        "a well-formed but empty submission should still be scoreable"
    for label, guess in (("the prompt placeholder", placeholder),
                         ("all zeros", zeros), ("the orientation extract", echoed)):
        assert abs(measure(guess, file_case) - file_case["ref"]) > \
            file_case["tolerance"], \
            "%s should not be a well-formed record set" % label

    # The prompt's own shape example, copied through verbatim. Section 6.7
    # requires every placeholder to be audited against the reference and
    # confirmed to fail, rather than assumed obviously fake.
    prompt_shape = {"records": {"XX0000": "Z" * RECORD_LENGTH}}
    assert "XX0000" not in REFS, "the prompt's placeholder key is a real payee"
    for item in ITEMS:
        assert abs(measure(prompt_shape, item) - item["ref"]) > item["tolerance"], \
            "the prompt's shape example passes %s" % item["case_id"]

    for junk in ({}, {"records": {}}, {"records": []}, {"records": None},
                 {"records": {r: None for r in REFS}},
                 {"records": {r: 0 for r in REFS}},
                 {"records": {r: float("nan") for r in REFS}},
                 {"RECORDS": {r: EXP["golden_records"][r] for r in REFS}},
                 {"records": {r: EXP["golden_records"][r][:-1] for r in REFS}},
                 {"records": {r: EXP["golden_records"][r] + " " for r in REFS}}):
        for item in ITEMS:
            value = measure(junk, item)
            assert isinstance(value, int) and \
                abs(value - item["ref"]) > item["tolerance"], \
                "a degenerate submission scored %s on %s" % (value, item["case_id"])


def test_no_assembled_record_reaches_the_agent():
    """The one leak channel, closed and checked.

    The withheld object is a positional field map, and a single correct record
    hands most of it over: the start position of the name block can be counted
    straight off it. No agent-visible file may therefore contain any substantial
    contiguous run of a golden record.

    Scans every agent-visible surface reachable from where the verifier is
    running. Inside the container that is the baked data under /root/data,
    which is the only thing the Dockerfile copies; run from a checkout it is
    also the skill and the prompt, which is where a worked example would most
    plausibly be pasted. Both settings are exercised: the container runs it on
    every graded run, and the authoring and QC runs cover all three surfaces.
    """
    bundle = os.path.dirname(VER)
    bases = [DATA,
             os.path.join(bundle, "environment", "data"),
             os.path.join(bundle, "environment", "skills")]
    surfaces, seen = [], set()
    for base in bases:
        for dirpath, _dirs, files in os.walk(base):
            for fname in files:
                path = os.path.realpath(os.path.join(dirpath, fname))
                if path in seen:
                    continue
                seen.add(path)
                try:
                    with open(path, encoding="utf-8", errors="replace") as fh:
                        surfaces.append((path, fh.read()))
                except OSError:
                    continue
    task_md = os.path.join(bundle, "task.md")
    if os.path.isfile(task_md):
        with open(task_md, encoding="utf-8", errors="replace") as fh:
            surfaces.append((task_md, fh.read()))
    assert surfaces, "no agent-visible surface found to scan"
    assert any(os.path.basename(p) == "payees.json" for p, _b in surfaces), \
        "the baked payee record was not among the scanned surfaces"

    window = 40
    for ref in REFS:
        record = EXP["golden_records"][ref]
        for start in range(0, RECORD_LENGTH - window + 1):
            chunk = record[start:start + window]
            if len(chunk.replace(" ", "")) < 6:
                continue    # a run of reserved positions carries no offset
            for path, body in surfaces:
                assert chunk not in body, \
                    "%s carries positions %d-%d of record %s verbatim" % (
                        os.path.basename(path), start + 1, start + window, ref)


def test_isomorphic_invariance_under_relabel_and_reindex():
    """V-09: the grader is a property of the data, not of memorised bytes.

    Move a payee's sequence number and rewrite its city, splice the new values
    into the record at this module's own offsets, and the transformed record
    must grade clean against the transformed payee while the untransformed
    comparison must fail. A verifier keyed to remembered surface bytes would
    accept the first and also accept the second.
    """
    ref = REFS[0]
    payee = dict(PAYEES[ref])
    golden = EXP["golden_records"][ref]

    moved = dict(payee)
    moved["record_sequence_number"] = payee["record_sequence_number"] + 114
    moved["payee_city"] = "GREENSBORO"
    _n, cf, cl, _len, _r = parse.SPAN_BY_NAME["payee_city"]
    _n, sf, sl, _slen, _sr = parse.SPAN_BY_NAME["record_sequence_number"]
    record = (golden[:cf - 1] + moved["payee_city"].ljust(cl - cf + 1)
              + golden[cl:])
    record = (record[:sf - 1]
              + str(moved["record_sequence_number"]).rjust(sl - sf + 1, "0")
              + record[sl:])
    assert len(record) == RECORD_LENGTH

    for group in parse.GROUP_KEYS:
        assert not parse.field_faults(record, group, moved, PAYMENT_YEAR), \
            "the transformed record does not grade clean at %s" % group
    stale = sum(len(parse.field_faults(record, g, payee, PAYMENT_YEAR))
                for g in parse.GROUP_KEYS)
    assert stale == 2, \
        "the transform should move exactly two fields, it moved %d" % stale


def test_amount_convention_alone_does_not_carry_the_task():
    """The design constraint, made a standing assertion.

    The payment-amount convention - twelve positions, right-justified,
    zero-filled, cents implied - is the part of this specification a model
    reproduces without help, so the task must not rest on it. A submission that
    gets every amount field right and slides the payee identification block must
    still fail, and the amount block must be a minority of the graded mass.
    """
    amounts_only = [i for i in ITEMS if i["group"] == "amounts_55_270"]
    assert len(amounts_only) * 4 <= len(ITEMS), \
        "the payment-amount block carries too much of the graded mass"
    for ref in REFS:
        payee = PAYEES[ref]
        shifted = _control_record("shifted_name_and_address_block", ref, payee)
        assert not parse.field_faults(shifted, "amounts_55_270", payee, PAYMENT_YEAR), \
            "the shifted control was supposed to keep the amount block correct"
        failed = [g for g in parse.GROUP_KEYS
                  if parse.field_faults(shifted, g, payee, PAYMENT_YEAR)]
        assert len(failed) >= 8, \
            "%s: a correct-amounts, shifted-block submission fails only %d group(s)" % (
                ref, len(failed))


def test_tolerances_are_positive_and_the_case_set_is_well_formed():
    assert len(ITEMS) == EXP["n_cases"], "item set malformed"
    assert all(EXP["n_cases"] % d for d in range(2, int(EXP["n_cases"] ** 0.5) + 1)), \
        "the graded case count is not prime, so a partial score can be a round value"
    seen = set()
    for item in ITEMS:
        assert item["tolerance"] > 0, "non-positive tolerance"
        assert math.isfinite(item["ref"])
        seen.add(item["case_id"])
    assert len(seen) == len(ITEMS), "duplicate case ids"
    gap = EXP["smallest_wrong_path_gap_multiple"]
    assert gap >= 2.0, "a competing method sits inside twice the tolerance"
    band = EXP["published_precision_ambiguity_mismatches_maxabs"]
    assert band < EXP["tolerance_field_mismatches_abs"], \
        "the tolerance is inside its own defensible-reading spread"
