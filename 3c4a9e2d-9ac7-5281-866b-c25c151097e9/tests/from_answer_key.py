#!/usr/bin/env python3
"""Generic OUTCOME verifier: score an agent's submission against answer_key.json.

ONE script, shared byte-identically by every dataset-only bundle.  Everything that
varies per bundle lives in the generated `expected_values.json` beside this file, so
this file never needs a per-bundle edit and a fix here fixes every bundle at once.

WHY THIS EXISTS
---------------
The 40 bundles of this batch were authored dataset-only on purpose: no `verifier/`,
no `oracle/`, no `test.sh`.  There is therefore no outcome verifier for `bench` to
read a reward from, so every run returns nothing - which reads exactly like a task
defect.  This file is the missing outcome channel, built from the `answer_key.json`
that every bundle carries at its root for precisely this purpose.

It is the ORDINARY outcome verifier the process-verifier method assumes already
exists.  It is NOT a third channel: it emits no `o_*` criteria and no rubric.  Per
VERIFIER_PIPELINE.md:566 the number it writes is CONTINUOUS - outcome test cases
passed over total, unweighted, with no process criteria in the denominator.

WHAT COUNTS AS ONE CASE
-----------------------
A graded case is one (output, case_id) PAIR, not one case_id.  Most bundles grade a
single quantity per case and the two coincide.  Some do not: the binaural bundles
grade two quantities at the same 37 case_ids and therefore have 74 graded cases, each
one its own test in the JUnit report under its own name.  Collapsing them would make
the report's total disagree with the computed total, and the cross-check below would
then refuse to score - which is the intended behaviour, not a workaround.

Which spelling of a case a submission is looked up under is decided by the OUTPUT
FORMAT, never guessed here:
    json_by_output   {output_name: {case_id: value}}   -> keyed by (output, case_id)
    json_records     {container: [{id_field: rid, output_name: value, ...}, ...]}
                                                       -> keyed by (output, record_id)
    json_nested      {container_key: {case_id: value}} -> keyed by case_id alone
    json_map         {case_id: value}                  -> keyed by case_id alone
    csv              case_column,value_column          -> keyed by case_id alone
`json_nested` covers both a container whose key happens to be the graded output's name
and one that is a generic bag (`answers`) holding a different quantity per case_id;
either way a case_id identifies exactly one graded value, so nothing more is needed.

`json_records` is the one shape whose submission address is NOT the answer key's
`case_id`.  Its bundles report several quantities per real-world entity - a fleet, a
sleeve arrangement - and task.md asks for one record per entity carrying one field per
quantity.  The answer key still grades one (output, case_id) pair per case, but the
case_id there is per-quantity (`F001_total`, `F001_headroom`) while the submission is
addressed by the ENTITY (`F001`).  So each case carries a `record_id` alongside its
case_id, and the generator fills it from the answer key's own id field.  The case_id
remains the test name in the JUnit report, so n is still the number of graded pairs.

A LIST introduces failure modes an object does not have, and each is handled here
rather than left to chance:
    a record with no id field      cannot be addressed, so it is skipped with a note
                                   and its cases read as absent (they fail)
    the same id on two records     conflicting values for one field make that field
                                   ambiguous, and an ambiguous field FAILS - the same
                                   rule the CSV reader applies to a repeated case_id
    a record missing one field     only that (output, record_id) is absent; the record's
                                   other fields still score, because a submission that
                                   answered one of two questions answered one of them
    the container is not a list    every case lives in that one container, so there is
                                   nothing to score: fatal, reward 0
    records not in the answer key  a contract note, no change to the reward - the same
                                   rule extra keys get in every other shape

HOW IT SCORES, AND WHY NOT BY GREPPING
--------------------------------------
    reward = graded cases matched / total graded cases

A case is MATCHED under the rule its own spec entry declares:

    match = "tolerance_abs"   |submitted - golden| <= tolerance_abs    (a measurement)
    match = "exact"           normalise(submitted) == golden           (a discrete value)

Exact match exists because a numeric window is meaningless for some outputs: an
admissible hyphenation is either the string the engine admits or it is not, and there
is no "close".  The normalisation applied before an exact comparison is declared per
case in the spec (`normalize`) and the vocabulary this script implements is fixed and
tiny; a spec that asks for a normalisation not implemented here is refused rather than
silently ignored, because ignoring it would grade under a rule nobody chose.  Case
folding is applied ONLY where a spec asks for it: a bundle may grade case-sensitively,
and lower-casing on its behalf would widen its answer set without being told to.

The count comes from a computed per-case comparison, is written to JUnit XML, and is
then RE-READ from that XML and cross-checked against the in-memory count.  It is
never obtained by scanning a human-readable log for "PASSED": a submission's own
contents are echoed into such a log, so counting that substring lets a submission
inflate its own score.  Measured on this corpus: a submission of the literal string
"PASSED" for every field scored 1.0000 while every test failed.  If the XML and the
in-memory count ever disagree, this script writes reward 0 and says so loudly rather
than picking one.

WHAT IS DELIBERATELY LENIENT, AND WHY IT CANNOT INFLATE A SCORE
---------------------------------------------------------------
Number parsing accepts surrounding whitespace, a leading currency symbol, thousands
separators and scientific notation, even where the task forbids them.  None of that
can turn a wrong answer into a right one - the parsed value still has to land within
`tolerance_abs` of the golden - so the leniency only removes false negatives from
formatting.  A `%` suffix is the exception and is REJECTED: it is a claim about scale,
and silently reading "73.42%" as 0.7342 would grade a scale error as correct, which is
one of the control routes these tasks exist to discriminate.  The same asymmetry
governs exact match: surrounding whitespace may be stripped where the spec says so,
but a number is never coerced to a string to be compared with one - a submission that
answers 5 where a word is required has not answered the question.

Extra keys the answer key does not grade are reported as a contract note and do not
change the reward.  The reward answers "how much of the answer was right"; folding
output hygiene into it would conflate two things and risks false-negatives on a
trailing blank row.  A duplicated case with conflicting values DOES fail that case -
it is genuinely ambiguous which value was submitted.

Stdlib only, and no network: the task images are `python:3.11-slim` and several
install nothing at all, so pytest is not available at verification time.
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC_PATH = os.path.join(HERE, "expected_values.json")

LOGDIR = os.environ.get("ERZA_VERIFIER_LOGDIR", "/logs/verifier")
XML_PATH = os.path.join(LOGDIR, "results.xml")
REWARD_PATH = os.path.join(LOGDIR, "reward.txt")
REPORT_PATH = os.path.join(LOGDIR, "outcome_report.json")

_NUM_STRIP = re.compile(r"[\s,_$£€]")

FORMATS = ("csv", "json_map", "json_nested", "json_by_output", "json_records")
MATCHES = ("tolerance_abs", "exact")
NORMALISERS = ("strip", "casefold")


class Unparseable(Exception):
    pass


def parse_number(raw) -> float:
    """Coerce a submitted cell to a float, or raise Unparseable.

    Lenient about presentation, strict about scale - see the module docstring.
    """
    if isinstance(raw, bool):
        raise Unparseable("boolean")
    if isinstance(raw, (int, float)):
        v = float(raw)
        if not math.isfinite(v):
            raise Unparseable("non-finite")
        return v
    if raw is None:
        raise Unparseable("null")
    if not isinstance(raw, str):
        raise Unparseable(f"type {type(raw).__name__}")
    s = raw.strip()
    if not s:
        raise Unparseable("empty")
    if s.endswith("%"):
        # A percent sign is a scale claim. Reading it as a fraction would grade a
        # scale error as correct; refusing to guess is the whole point.
        raise Unparseable("percent-suffixed - scale is ambiguous")
    s = _NUM_STRIP.sub("", s)
    if s.startswith("(") and s.endswith(")"):        # accounting negative
        s = "-" + s[1:-1]
    try:
        v = float(s)
    except ValueError:
        raise Unparseable(f"not a number: {raw!r:.60}")
    if not math.isfinite(v):
        raise Unparseable("non-finite")
    return v


def normalise_text(raw, ops) -> str:
    """Coerce a submitted cell to the string an exact comparison sees.

    No coercion from other types: see the module docstring on why a number is not
    quietly stringified into an answer.
    """
    if isinstance(raw, bool) or not isinstance(raw, str):
        kind = "null" if raw is None else type(raw).__name__
        raise Unparseable(f"expected a string, got {kind}")
    s = raw
    for op in ops:
        if op == "strip":
            s = s.strip()
        elif op == "casefold":
            s = s.casefold()
    if not s:
        raise Unparseable("empty")
    return s


def check_spec(spec) -> list:
    """Return the reasons this spec cannot be graded. Empty list means it can.

    A spec this script does not fully understand must not be graded PARTLY: a case
    silently skipped, or compared under a normalisation that was asked for and not
    applied, produces a number that reads like a measurement and is not one. Every
    problem found here is fatal in main(), which is why detection is exhaustive
    rather than first-failure.
    """
    bad = []
    out = spec.get("output")
    if not isinstance(out, dict):
        return ["expected_values.json has no output contract"]
    fmt = out.get("format")
    if fmt not in FORMATS:
        bad.append(f"unknown output format {fmt!r} (known: {', '.join(FORMATS)})")
    if not out.get("path"):
        bad.append("the output contract names no submission path")
    if fmt == "csv" and not (out.get("case_column") and out.get("value_column")):
        bad.append("a csv contract needs case_column and value_column")
    if fmt == "json_nested" and not out.get("value_key"):
        bad.append("a json_nested contract needs value_key")
    keys = out.get("output_keys")
    if fmt == "json_by_output" and not (isinstance(keys, list) and keys):
        bad.append("a json_by_output contract needs a non-empty output_keys list")

    fields = out.get("record_fields")
    if fmt == "json_records":
        # A record is addressed by its container, its id field and the field holding
        # each graded quantity. Missing any one of the three makes a lookup a guess.
        if not isinstance(out.get("records_key"), str) or not out.get("records_key"):
            bad.append("a json_records contract needs a records_key naming the list")
        if not isinstance(out.get("id_field"), str) or not out.get("id_field"):
            bad.append("a json_records contract needs an id_field naming the record id")
        if not (isinstance(fields, list) and fields
                and all(isinstance(f, str) and f for f in fields)):
            bad.append("a json_records contract needs a non-empty record_fields list "
                       "of field names")
        elif out.get("id_field") in fields:
            bad.append(f"id_field {out['id_field']!r} is also one of record_fields; a "
                       "record's id and one of its graded values cannot share a key")

    tests, slots = set(), {}
    for i, case in enumerate(spec.get("cases") or []):
        who = case.get("case_id", f"#{i}")
        tid = case.get("test_id") or case.get("case_id")
        if not tid:
            bad.append(f"case #{i} has no case_id")
        elif tid in tests:
            # Two cases under one test name would collapse in the JUnit report and the
            # cross-check would then refuse to score. Say so here, where it is legible.
            bad.append(f"two cases share the test name {tid!r}")
        else:
            tests.add(tid)
        match = case.get("match")
        if match not in MATCHES:
            bad.append(f"case {who} has unknown match {match!r} (known: {', '.join(MATCHES)})")
            continue
        if match == "tolerance_abs":
            try:
                tol = float(case["tolerance_abs"])
                float(case["golden"])
            except (KeyError, TypeError, ValueError):
                bad.append(f"case {who} needs a numeric golden and tolerance_abs")
                continue
            if not (tol > 0):
                bad.append(f"case {who} has tolerance_abs {tol!r}; must be > 0")
        else:
            if not isinstance(case.get("golden"), str) or not case["golden"]:
                bad.append(f"case {who} is exact-match but its golden is not a string")
            for op in case.get("normalize") or []:
                if op not in NORMALISERS:
                    bad.append(f"case {who} asks for normalisation {op!r}, "
                               f"which this verifier does not implement")
        if fmt == "json_by_output" and case.get("output") not in (keys or []):
            bad.append(f"case {who} has output {case.get('output')!r}, "
                       f"which is not one of the contract's output_keys")
        if fmt == "json_records":
            rid = case.get("record_id")
            if not isinstance(rid, str) or not rid:
                bad.append(f"case {who} has no record_id; a json_records case is looked "
                           f"up by (output, record_id), not by case_id")
            elif (case.get("output"), rid) in slots:
                # Two cases reading the same field of the same record cannot both be
                # graded from one submitted value; that is a generator bug, not an
                # agent's problem, and grading anyway would report a fiction.
                bad.append(f"cases {slots[(case.get('output'), rid)]!r} and {tid!r} both "
                           f"read field {case.get('output')!r} of record {rid!r}")
            else:
                slots[(case.get("output"), rid)] = tid
            if case.get("output") not in (fields or []):
                bad.append(f"case {who} has output {case.get('output')!r}, "
                           f"which is not one of the contract's record_fields")
    return bad


def _slot(case, fmt):
    """The address this case is submitted under, as (output, id).

    `json_records` is the one shape addressed by something other than the case_id: its
    submission is one record per entity, so the id half is the case's `record_id`.
    """
    if fmt == "json_records":
        return (case.get("output"), case["record_id"])
    return (case.get("output") if fmt == "json_by_output" else None, case["case_id"])


def _label(slot):
    out, cid = slot
    return f"{out}.{cid}" if out else cid


def _walk_to_map(obj, value_key):
    """Return {case_id: raw} from a submitted JSON document."""
    if value_key:
        if not isinstance(obj, dict):
            raise Unparseable(f"top level is {type(obj).__name__}, expected an object")
        if value_key not in obj:
            raise Unparseable(f"no {value_key!r} key at the top level")
        obj = obj[value_key]
    if not isinstance(obj, dict):
        raise Unparseable(f"expected an object of case_id -> value, got {type(obj).__name__}")
    return obj


def _record_id(raw):
    """The string a submitted record id is addressed under, or None if unusable.

    Ids in an answer key are strings, so a submitted number is stringified to give a
    numerically-typed id a chance to match; a bool is not an id under any reading.
    """
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, str):
        return raw.strip() or None
    if isinstance(raw, (int, float)):
        return str(raw)
    return None


def _read_records(doc, out, path, notes):
    """Return {(field, record_id): raw} from a {container: [record, ...]} submission.

    Every list-specific hazard is decided here; see the module docstring for the rule
    each one follows and why. Notes are aggregated rather than emitted per record, so a
    submission with 45 malformed records produces one legible note and not 45.
    """
    if not isinstance(doc, dict):
        raise Unparseable(f"top level is {type(doc).__name__}, expected an object")
    key = out["records_key"]
    if key not in doc:
        raise Unparseable(f"no {key!r} key at the top level of {path}")
    rows = doc[key]
    if not isinstance(rows, list):
        # Unlike json_by_output, where a bad block still leaves the other output
        # gradeable, every case of this bundle lives in this one container. If it is
        # not a list there is nothing to look a case up in, so this is fatal.
        raise Unparseable(f"{key!r} is {type(rows).__name__}, expected a list of records")
    for extra in sorted(k for k in doc if k != key):
        notes.append(f"top-level key {extra!r} is not the record list {key!r}, ignored")

    idf, fields = out["id_field"], out["record_fields"]
    sub, seen, conflicts, dupes, noid, nonrec, stray = {}, set(), set(), [], [], [], set()
    for i, rec in enumerate(rows):
        if not isinstance(rec, dict):
            nonrec.append(f"#{i} ({type(rec).__name__})")
            continue
        rid = _record_id(rec.get(idf))
        if rid is None:
            # Nothing addresses this record, so nothing in it can be graded. Its cases
            # are reported absent, which is exactly what happened to them.
            noid.append(f"#{i}")
            continue
        if rid in seen:
            dupes.append(rid)
        seen.add(rid)
        for f in fields:
            if f not in rec:
                continue                      # absent -> that pair fails, others do not
            v = rec[f]
            if (f, rid) in sub and str(sub[(f, rid)]).strip() != str(v).strip():
                conflicts.add((f, rid))
            sub[(f, rid)] = v
        stray |= {k for k in rec if k != idf and k not in fields}

    if nonrec:
        notes.append(f"{len(nonrec)} list entrie(s) are not objects, ignored: "
                     f"{nonrec[:8]}{' ...' if len(nonrec) > 8 else ''}")
    if noid:
        notes.append(f"{len(noid)} record(s) carry no usable {idf!r}, ignored: "
                     f"{noid[:8]}{' ...' if len(noid) > 8 else ''}")
    if dupes:
        u = sorted(set(dupes))
        notes.append(f"{idf} {u[:8]}{' ...' if len(u) > 8 else ''} appears on more than "
                     f"one record")
    for slot in sorted(conflicts):
        # Same rule as a repeated case_id in a CSV: which value was submitted is
        # genuinely unknown, so the pair fails rather than being resolved by position.
        sub[slot] = None
        notes.append(f"record {slot[1]} gives conflicting values for {slot[0]!r}")
    if stray:
        notes.append(f"record field(s) {sorted(stray)[:8]} are not graded outputs, ignored")
    return sub


def read_submission(spec):
    """Return ({(output, case_id): raw_value}, [note, ...]).

    `output` is None for every format that keys by case_id alone, so a lookup is the
    same operation in all five shapes.  Raises Unparseable when the submission cannot
    be read at all.
    """
    out = spec["output"]
    path, fmt = out["path"], out["format"]
    notes = []
    if not os.path.exists(path):
        raise Unparseable(f"no submission at {path}")
    if fmt == "csv":
        case_col, val_col = out["case_column"], out["value_column"]
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
            rows = list(csv.DictReader(fh))
        if not rows:
            raise Unparseable(f"{path} has a header but no rows")
        fields = rows[0].keys()
        if case_col not in fields or val_col not in fields:
            raise Unparseable(
                f"{path} header is {sorted(f for f in fields if f)!r}, "
                f"expected columns {case_col!r} and {val_col!r}")
        sub, dupes = {}, set()
        for r in rows:
            cid = (r.get(case_col) or "").strip()
            if not cid:
                continue
            v = r.get(val_col)
            if (None, cid) in sub and str(sub[(None, cid)]).strip() != str(v).strip():
                dupes.add(cid)
            sub[(None, cid)] = v
        for cid in sorted(dupes):
            sub[(None, cid)] = None
            notes.append(f"case {cid} appears more than once with conflicting values")
        return sub, notes
    if fmt in ("json_map", "json_nested", "json_by_output", "json_records"):
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            try:
                doc = json.load(fh)
            except json.JSONDecodeError as e:
                raise Unparseable(f"{path} is not valid JSON: {e}")
        if fmt == "json_records":
            return _read_records(doc, out, path, notes), notes
        if fmt != "json_by_output":
            flat = _walk_to_map(doc, out.get("value_key") if fmt == "json_nested" else None)
            return {(None, k): v for k, v in flat.items()}, notes
        if not isinstance(doc, dict):
            raise Unparseable(f"top level is {type(doc).__name__}, expected an object")
        sub = {}
        for okey in out["output_keys"]:
            block = doc.get(okey)
            if block is None:
                # Not fatal for the other output: its cases are graded normally and
                # this one's are reported absent, which is what actually happened.
                notes.append(f"no {okey!r} object at the top level of {path}")
                continue
            if not isinstance(block, dict):
                notes.append(f"{okey!r} is {type(block).__name__}, "
                             f"expected an object of case_id -> value")
                continue
            for cid, v in block.items():
                sub[(okey, cid)] = v
        for extra in sorted(k for k in doc if k not in out["output_keys"]):
            notes.append(f"top-level key {extra!r} is not a graded output, ignored")
        return sub, notes
    raise Unparseable(f"unknown output format {fmt!r} in expected_values.json")


def grade(spec):
    """Return (results, notes). results = [(test_id, case_id, output, ok, detail)]."""
    fmt = spec["output"]["format"]
    cases = spec["cases"]

    def ident(case):
        return (case.get("test_id") or case["case_id"], case["case_id"], case.get("output"))

    notes = []
    try:
        sub, notes = read_submission(spec)
    except Unparseable as e:
        # Every case fails, and the reason is recorded once against each of them so
        # the XML explains itself without a reader having to find this file.
        return ([ident(c) + (False, f"submission unreadable: {e}") for c in cases],
                [f"submission unreadable: {e}"])

    graded = {_slot(c, fmt) for c in cases}
    extra = sorted(_label(s) for s in set(sub) - graded)
    if extra:
        notes.append(f"{len(extra)} key(s) not in the answer key, ignored: "
                     f"{extra[:8]}{' ...' if len(extra) > 8 else ''}")

    results = []
    for case in cases:
        slot = _slot(case, fmt)
        golden = case["golden"]
        if slot not in sub:
            results.append(ident(case) + (False, "absent from the submission"))
            continue
        if case["match"] == "exact":
            try:
                got = normalise_text(sub[slot], case.get("normalize") or [])
            except Unparseable as e:
                results.append(ident(case) + (False, f"unparseable ({e})"))
                continue
            results.append(ident(case) + (got == golden,
                                          f"submitted={got!r} golden={golden!r} (exact match)"))
            continue
        golden, tol = float(golden), float(case["tolerance_abs"])
        try:
            got = parse_number(sub[slot])
        except Unparseable as e:
            results.append(ident(case) + (False, f"unparseable ({e})"))
            continue
        delta = abs(got - golden)
        ok = delta <= tol
        results.append(ident(case) + (ok, f"submitted={got!r} golden={golden!r} "
                                          f"|delta|={delta:.6g} tolerance_abs={tol:.6g} "
                                          f"({delta / tol:.3f}x tolerance)" if tol else
                                          f"submitted={got!r} golden={golden!r} |delta|={delta:.6g}"))
    return results, notes


def write_junit(results, spec, notes):
    suite = ET.Element("testsuite", {
        "name": f"outcome:{spec.get('task_slug', 'task')}",
        "tests": str(len(results)),
        "failures": str(sum(0 if r[3] else 1 for r in results)),
        "errors": "0",
        "skipped": "0",
    })
    props = ET.SubElement(suite, "properties")
    for k, v in (("answer_key_sha256", spec.get("source_answer_key_sha256", "")),
                 ("output_path", spec["output"]["path"]),
                 ("output_format", spec["output"]["format"])):
        ET.SubElement(props, "property", {"name": k, "value": str(v)})
    for i, note in enumerate(notes):
        ET.SubElement(props, "property", {"name": f"note_{i}", "value": note})
    for tid, _cid, _out, ok, detail in results:
        tc = ET.SubElement(suite, "testcase", {
            "classname": f"outcome.{spec.get('task_slug', 'task')}",
            "name": f"case_{tid}",
        })
        if not ok:
            f = ET.SubElement(tc, "failure", {"message": detail[:400], "type": "OutcomeMismatch"})
            f.text = detail
        else:
            ET.SubElement(tc, "system-out").text = detail
    os.makedirs(LOGDIR, exist_ok=True)
    ET.ElementTree(suite).write(XML_PATH, encoding="utf-8", xml_declaration=True)


def write_reason(passed, total, results, notes):
    """Emit /logs/verifier/reason.json on any non-perfect score.

    Required by the Harbor delivery gate G-DEL-REWARD, which checks that a verifier writes
    /logs/verifier/reward.txt AND emits a reason on the zero-score path. The field names below
    match the migrated Harbor bundles so one reader parses both.

    ATTRIBUTION IS NOT HARD-CODED. The Harbor example writes "verifier_failed" because a pytest
    non-zero exit genuinely cannot distinguish a wrong answer from a broken checker. This
    scorer can: it knows whether the submission was absent, unreadable, or simply wrong. Saying
    "verifier_failed" when the agent produced 0 of 29 correct answers would blame the
    instrument for the run's failure, and every triage built on it would start in the wrong
    place. Emitted on any reward < 1.0, not only at exactly 0, because a partial score needs
    the same explanation.
    """
    if passed == total:
        return
    # results rows are (test_id, case_id, output, ok, detail) - five fields since the scorer
    # learned multi-output bundles, where (output, case_id) rather than case_id addresses a case.
    failed = [(cid if out is None else f"{cid}::{out}", d)
              for _tid, cid, out, ok, d in results if not ok]
    # A case that was never submitted and a case that was submitted wrongly are different
    # failures, and Gate 2 triages them differently: a wrong answer counts, a run that
    # produced no answer is re-run or excluded. Reporting "present but outside tolerance"
    # for cases that were absent would send that triage to the wrong place, so the
    # attribution is derived from what actually happened rather than from passed == 0.
    absent = sum(1 for _c, d in failed if "absent from the submission" in d)
    if any("submission unreadable" in d for _c, d in failed):
        attribution, detail = "no_submission", failed[0][1]
    elif absent == len(failed):
        attribution = "no_graded_values"
        detail = (f"The submission was readable but carried none of the {total} graded case "
                  "ids, so no value was ever compared. This is a missing answer, not a wrong "
                  "one.")
    elif passed == 0:
        attribution = "all_cases_wrong"
        detail = ("No graded case landed within tolerance. This is a wrong answer, "
                  "not a verifier fault: an oracle-perfect submission scores exactly 1.0 on this "
                  "same code path, proven before any pilot ran.")
        if absent:
            detail += f" {absent} of {total} case(s) were absent from the submission entirely."
    else:
        attribution = "some_cases_wrong"
        detail = f"{len(failed)} of {total} graded cases outside tolerance."
        if absent:
            detail += f" {absent} of those were absent from the submission entirely."
    reason = {
        "reward": round(passed / total, 12),
        "attribution": attribution,
        "cases_passed": passed,
        "cases_total": total,
        "verifier_entry": "/tests/test.sh",
        "checker_module": "/tests/from_answer_key.py",
        "reward_contract_path": "/logs/verifier/reward.txt",
        "junit_report": "/logs/verifier/results.xml",
        "detail": detail,
        "failures": [{"case_id": c, "detail": d} for c, d in failed[:20]],
        "notes": notes,
    }
    os.makedirs(LOGDIR, exist_ok=True)
    with open(os.path.join(LOGDIR, "reason.json"), "w") as f:
        json.dump(reason, f, indent=2, sort_keys=True)
        f.write("\n")


def count_from_junit():
    """Re-read the report we just wrote. Returns (passed, total) or None."""
    try:
        root = ET.parse(XML_PATH).getroot()
    except Exception:
        return None
    passed, seen = 0, set()
    for tc in root.iter("testcase"):
        key = (tc.get("classname", ""), tc.get("name", ""))
        if key in seen:                      # never count a case twice
            continue
        seen.add(key)
        if not any(tc.find(t) is not None for t in ("failure", "error", "skipped")):
            passed += 1
    return passed, len(seen)


def main() -> int:
    os.makedirs(LOGDIR, exist_ok=True)
    if not os.path.exists(SPEC_PATH):
        print(f"VERIFIER-BROKEN: no expected_values.json at {SPEC_PATH}")
        open(REWARD_PATH, "w").write("0.0\n")
        return 2
    spec = json.load(open(SPEC_PATH))
    cases = spec.get("cases") or []
    if not cases:
        print("VERIFIER-BROKEN: expected_values.json grades no cases")
        open(REWARD_PATH, "w").write("0.0\n")
        return 2
    problems = check_spec(spec)
    if problems:
        print("VERIFIER-BROKEN: expected_values.json cannot be graded by this verifier")
        for p in problems[:20]:
            print(f"  - {p}")
        open(REWARD_PATH, "w").write("0.0\n")
        return 2

    results, notes = grade(spec)
    write_junit(results, spec, notes)

    mem_passed, total = sum(1 for r in results if r[3]), len(results)
    xml = count_from_junit()
    if xml is None:
        print("VERIFIER-BROKEN: the JUnit report we just wrote is unparseable")
        open(REWARD_PATH, "w").write("0.0\n")
        return 2
    if xml != (mem_passed, total):
        # Defence in depth: the two counts are produced by different code paths over
        # the same verdicts. They can only disagree if this verifier is broken, and a
        # broken verifier must not emit a number that reads like a measurement.
        print(f"VERIFIER-BROKEN: JUnit says {xml}, computed comparison says "
              f"{(mem_passed, total)} - refusing to score")
        open(REWARD_PATH, "w").write("0.0\n")
        return 2

    write_reason(mem_passed, total, results, notes)
    reward = mem_passed / total
    # 12 dp, not 6: passed/total is an exact fraction and rounding it makes the reward
    # disagree with passed/total for case counts that are not powers of ten (50/51 ->
    # 0.980392 differs from the fraction by 1.5e-7). Nothing downstream needs the extra
    # digits, but a reward that is not exactly the count it claims to be invites a
    # reader to reconcile two numbers that cannot be reconciled.
    open(REWARD_PATH, "w").write(f"{reward:.12f}\n")
    json.dump({
        "task_slug": spec.get("task_slug"),
        "reward": round(reward, 6),
        "continuous": round(reward, 6),
        "passed": mem_passed,
        "total": total,
        "answer_key_sha256": spec.get("source_answer_key_sha256"),
        "output_path": spec["output"]["path"],
        "notes": notes,
        "failures": [{"case_id": cid, "output": out, "detail": d}
                     for _t, cid, out, ok, d in results if not ok],
    }, open(REPORT_PATH, "w"), indent=2)

    for tid, _cid, _out, ok, detail in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {tid}: {detail}")
    for note in notes:
        print(f"  note: {note}")
    print(f"\noutcome cases passed : {mem_passed}/{total}")
    print(f"CONTINUOUS (reward)  : {reward:.6f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
