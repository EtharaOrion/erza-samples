"""Deterministic detections over a normalised trajectory.

Each function is a *hypothesis about how a correct run is spelled*. The channel
pattern-matches the source the agent authored (`agent_code` = file writes plus
the commands it ran) - strictly weaker than executing the agent's emitter, and
the largest source of false negatives on unseen runs (see the module docstring of test_process.py). The matchers are
deliberately multi-spelling, and every one was bound, at authoring time, by a
fixture in the author-side negative-fixture matrix that was seen to FIRE on a
planted defect and to stay QUIET on a clean run.

Convention: positive detectors return True when the criterion is SATISFIED.
Guardrail detectors are named `failure_*` and return True when the FAILURE MODE
OCCURRED; the scored test then asserts the failure did NOT occur.

The single argument is any object exposing `.agent_code`, `.commands`,
`.agent_prose` and `.file_writes` - a real `trajectory.Trajectory` in
production, or one loaded from a synthetic run directory in the fixtures.

WHY THE PUBLISHED POSITIONS ARE IN THIS FILE. The crux of this task is whether
the run placed the payee identification block and the return-specific tail where
the specification puts them, so the only honest deterministic test for it is a
numeric one: do literals reading as those published start positions appear where
they can act? That requires the position set here. This file is grader-side only
- `environment/Dockerfile` copies `environment/data` and nothing else, and
`/verifier` is in `sandbox_locked_paths` - so it is not a leak path. The values
are transcribed from the publication cited in `TRUTH.md:Sources` at the bundle root.
"""
from __future__ import annotations

import re

# --- published start positions, one-based, of the fields past the payment
# --- amount block. A run that placed them wrote some of these down.
LATE_STARTS = (271, 287, 288, 328, 368, 408, 448, 488, 490, 499, 500, 508,
               544, 545, 547, 548, 549, 663, 723, 735, 747, 749)
# Zero-based slice bounds are the same numbers less one, so both are accepted.
FIRST_NAME_START = (287, 288)
CITY_START = (447, 448)
INTERIOR_RUN_BOUNDS = ((271, 286), (408, 447))
TAIL_INDICATOR = (547, 548)
TAIL_PROGRAMME_CODE = (746, 747)
RECORD_LENGTH = 750

_INT_RE = re.compile(r"(?<![\w.])(\d{1,5})(?![\w.])")


def _code(traj) -> str:
    return traj.agent_code or ""


def _cmds(traj) -> str:
    return "\n".join(traj.commands)


def _strip_comments(src: str) -> str:
    """Drop `#` comments. A run that writes "never read /tests/..." in a
    comment is describing restraint; charging a guardrail for saying so punishes
    exactly the behaviour we want."""
    return "\n".join(re.sub(r"#.*$", "", ln) for ln in src.splitlines())


def _ints(code: str):
    """(text, value, offset) for every standalone integer literal."""
    return [(m.group(1), int(m.group(1)), m.start()) for m in _INT_RE.finditer(code)]


def _present(code: str, targets) -> bool:
    values = {v for _t, v, _i in _ints(code)}
    return bool(values & set(targets))


def _in_relation(code: str, target: int) -> bool:
    """The number appears where it can ACT: as a slice bound, an index, an
    argument, an element of a table, or an operand. A bare mention in prose does
    not count."""
    lit = str(target)
    patterns = (
        r"\[\s*%s\s*[:\]]" % lit,          # record[288:...]  / record[288]
        r":\s*%s\s*[\]:]" % lit,           # record[...:327]
        r"[\(\[\{,]\s*%s\s*[,\)\]\}]" % lit,   # (288, 327) / [288, 40]
        r"=\s*%s\b" % lit,                  # START = 288
        r"%s\s*[-+*]" % lit,                # 288 - 1
        r"[-+*]\s*%s\b" % lit,              # + 288
    )
    return any(re.search(p, code) for p in patterns)


def _late_starts_written(code: str) -> int:
    values = {v for _t, v, _i in _ints(code)}
    return len({v for v in LATE_STARTS if v in values or (v - 1) in values})


# --- the layout written as a LENGTH table ----------------------------------
# TRUTH.md Step 5 blesses two spellings and says neither is safer than the other:
# write each field into a buffer of the declared length at its own offset, OR
# concatenate the fields in order *including* the reserved runs. The second
# spelling records no start positions at all - the fields are contiguous, so the
# lengths and the order fix every offset - so a detector keyed only on position
# literals rejects a correct run for its spelling. That is the route restriction
# REQUIREMENTS.md:324-341 forbids, and it bites the no-Skills arm hardest, which
# is the arm most likely to reach for a plain (name, width) table.

_FIELD_ROW_RE = re.compile(
    r"[\(\[]\s*[\"'](\w+)[\"']\s*,\s*(?:\d+\s*,\s*)?(\d+)\s*[\)\]]"
    r"|[\"'](\w+)[\"']\s*:\s*(?:\(\s*\d+\s*,\s*)?(\d+)\s*[,\)\}\]]")

# Names a run gives the runs it must not close.
_RESERVED_NAME = r"reserv|blank|filler|unused|spare|rsvd|resv|\bgap\b"


# A width-bearing emission: the width is the call's last integer argument, and
# the callee is what the run named that piece of the record.
#   blanks(114)                                  -> ("blanks", 114)
#   alnum(p.get("special_data_entries", ""), 60) -> ("alnum", 60)
# One level of nested parentheses is allowed so a `.get(...)` default does not
# hide the width.
_BUILDER_ROW_RE = re.compile(
    r"(\w+)\s*\(\s*(?:[^()]*(?:\([^()]*\))?[^()]*,\s*)?(\d{1,4})\s*\)")


def _layout_rows(code: str):
    """(field name, declared width) for every layout row the run wrote down.

    Accepts `("name", 288, 40)`, `("name", 40)` and `"name": 40` alike - the
    optional middle integer is a start position, where the run recorded one.

    Also accepts the builder idiom, where the layout is not a table at all but a
    sequence of width-bearing emissions:

        parts.append(blanks(114))                      # 549-662
        parts.append(alnum(p.get("special_data", ""), 60))

    That run has written the block's widths down every bit as explicitly as a
    table would; it just wrote them as code. Reading only the declarative form
    parsed such a run as ZERO layout rows, so every check resting on the widths
    silently reported that the run never laid out the record.
    """
    rows = []
    for m in _FIELD_ROW_RE.finditer(code):
        name = m.group(1) or m.group(3)
        width = m.group(2) or m.group(4)
        if name and width:
            rows.append((name, int(width)))
    for m in _BUILDER_ROW_RE.finditer(code):
        rows.append((m.group(1), int(m.group(2))))
    # `' ' * 114` is the same reserved run written as a string repeat. A run of
    # spaces IS a blank run, so it is named as one; without this the repeat
    # idiom left the 114-wide reserved field invisible.
    for m in re.finditer(r"[\"']([ 0])[\"']\s*\*\s*(\d{1,4})", code):
        rows.append(("blank" if m.group(1) == " " else "zerofill", int(m.group(2))))
    return rows


def _has_row(rows, name_re: str, width: int) -> bool:
    return any(w == width and re.search(name_re, n, re.I) for n, w in rows)


def _placed_by_length_table(code: str) -> bool:
    """The record was laid out as an ordered length table that KEEPS both
    interior reserved runs.

    Closing either run is the failure this whole crux surface exists to catch,
    and a length table that closes one carries no 16-wide and no 40-wide reserved
    row. So this admits the concatenation route without admitting the defect: it
    is the reserved rows, not the vocabulary, that decide.
    """
    rows = _layout_rows(code)
    if len(rows) < 12:
        return False
    return (_has_row(rows, _RESERVED_NAME, 16)
            and _has_row(rows, _RESERVED_NAME, 40))


# --------------------------- positive detectors ---------------------------

def reads_inputs(traj) -> bool:
    """Opened the baked inputs under /root/data."""
    return bool(re.search(r"payees\.json|question\.json|/root/data\b",
                          _code(traj), re.I))


def writes_emitter(traj) -> bool:
    """Authored an emitter (a .py file, or a heredoc'd / inline script)."""
    if any(str(p).endswith(".py") for p, _c in traj.file_writes):
        return True
    code = _code(traj)
    return bool(re.search(r"\bimport\b", code)) and bool(
        re.search(r"\bdef\b|json\.|ljust|rjust|zfill", code))


def executes_emitter(traj) -> bool:
    """Ran python to produce the answer rather than only drafting a script."""
    return bool(re.search(r"\bpython3?\b", _cmds(traj)))


def pins_the_declared_length(traj) -> bool:
    """The declared record length is used, not assumed.

    Any of: a length assertion, a pad or truncation to it, or a buffer of it.
    """
    code = _code(traj)
    return _in_relation(code, RECORD_LENGTH) or bool(
        re.search(r"(?:ljust|rjust|zfill)\s*\(\s*%d" % RECORD_LENGTH, code))


def places_payee_block_at_published_offsets(traj) -> bool:
    """CRUX. The payee identification block sits at its published positions.

    Three admissible spellings, all of which TRUTH.md Step 5 blesses:

      * a literal reading as the first payee name line's start AND one reading
        as the payee city's start, both where they can act;
      * the whole position column written out (six or more published late
        starts);
      * an ordered LENGTH table that keeps both interior reserved runs and
        carries the payee block's own rows - a concatenation route records no
        start positions, yet fixes every one of them.

    A run that packed the fields on with the reserved runs closed has none of
    the three, which is the point.
    """
    code = _code(traj)
    pair = (any(_in_relation(code, v) for v in FIRST_NAME_START)
            and any(_in_relation(code, v) for v in CITY_START))
    rows = _layout_rows(code)
    by_table = (_placed_by_length_table(code)
                and _has_row(rows, r"name", 40)
                and _has_row(rows, r"city|town|locality", 40))
    return pair or _late_starts_written(code) >= 6 or by_table


def reserves_the_interior_runs(traj) -> bool:
    """The reserved runs inside the record are emitted rather than closed.

    Two admissible spellings: the bounding positions of both interior runs, or -
    for a run that concatenates by length - a blank fill named for a reserved
    run beside the first run's own length.
    """
    code = _code(traj)
    by_bounds = all(_present(code, bounds) or _present(code, tuple(b - 1 for b in bounds))
                    for bounds in INTERIOR_RUN_BOUNDS)
    by_length = bool(re.search(
        r"(?:blank|filler|reserved|pad)\w*[^\n]{0,40}\b16\b"
        r"|\b16\b[^\n]{0,40}(?:blank|filler|reserved)", code, re.I))
    return by_bounds or by_length


def emits_return_specific_tail(traj) -> bool:
    """The tail belonging to the reported return type is placed.

    Both the indicator position that separates this form's tail from its
    neighbour's and the programme-code position at the end of the record must
    appear where they can act - or, for the concatenation route, the tail must
    appear in the length table by its own widths. The 114-wide reserved run and
    the 60-wide free-text field are that table's fingerprint: they exist only in
    the return-specific block, so a run that emitted the common part alone has
    neither. Without this second spelling the sibling criterion would reject a
    route the crux blesses, which REQUIREMENTS.md:337-341 calls a defect in the
    instrument rather than in the run.
    """
    code = _code(traj)
    rows = _layout_rows(code)
    by_table = (_has_row(rows, _RESERVED_NAME, 114)
                and any(w == 60 for _n, w in rows))
    return (any(_in_relation(code, v) for v in TAIL_INDICATOR)
            and any(_in_relation(code, v) for v in TAIL_PROGRAMME_CODE)) or by_table


def amount_fields_right_justified_zero_filled(traj) -> bool:
    """Payment amounts padded right-justified and zero-filled to their width.

    The width may be a literal or a name bound to 12. A helper like

        def amt(s, length=12):
            return str(cents(s)).rjust(length, "0")[-length:]

    pads to exactly the same twelve characters as `rjust(12, "0")` does; reading
    only the literal made this criterion turn on whether the run inlined a
    constant or named it, which is a spelling difference, not a behavioural one.
    """
    code = _code(traj)
    if re.search(r"zfill\s*\(\s*12\s*\)|rjust\s*\(\s*12\s*,\s*[\"']0[\"']\s*\)"
                 r"|%\s*012d|:\s*0?12d|:>012|\{[^}]*:012", code):
        return True
    # Names bound to 12, whether as a parameter default or a plain assignment.
    widths = set(re.findall(r"(\w+)\s*=\s*12(?![\d.])", code))
    return any(re.search(r"zfill\s*\(\s*%s\s*\)" % re.escape(w) +
                         r"|rjust\s*\(\s*%s\s*,\s*[\"']0[\"']\s*\)" % re.escape(w), code)
               for w in widths)


def sequence_number_zero_filled(traj) -> bool:
    """The record sequence number right-justified with leading zeros."""
    code = _code(traj)
    return bool(re.search(
        r"zfill\s*\(\s*8\s*\)|rjust\s*\(\s*8\s*,\s*[\"']0[\"']\s*\)"
        r"|%\s*08d|:\s*08d|\{[^}]*:08", code))


def converts_amounts_to_cents(traj) -> bool:
    """Dollars-and-cents turned into whole cents, with no punctuation left."""
    code = _code(traj)
    return bool(re.search(
        r"\*\s*100\b|\b100\s*\*|Decimal\(|replace\(\s*[\"']\.[\"']"
        r"|\bcents\b|split\(\s*[\"']\.[\"']", code, re.I))


def reports_contract(traj) -> bool:
    """Emitted /root/results.json under the contracted top-level key."""
    code = _code(traj)
    return bool(re.search(r"results\.json", code, re.I)) and "records" in code


# ----------------------- guardrail failure detectors -----------------------

def failure_delimited_output(traj) -> bool:
    """Failure: the record was joined with separators, or the orientation block
    was copied through as the answer.

    Quiet as soon as the run shows positional placement, so a run that merely
    READ the orientation block to contrast it is not charged.
    """
    code = _code(traj)
    placed = (_late_starts_written(code) >= 3
              or bool(re.search(r"ljust\s*\(|rjust\s*\(|zfill\s*\(", code)))
    if placed:
        return False
    joined = bool(re.search(r"[\"'][,;|\t][\"']\s*\.join\s*\(|csv\.writer|\bto_csv\b",
                            code))
    # Reaching for the orientation block at all, in a run that shows no
    # positional placement, is the echo. The `placed` gate above is what keeps
    # this off a run that merely READ the block to contrast it - that run has
    # padding calls or written-out positions and never reaches here.
    echoed = bool(re.search(r"decoy_reference|delimited_rendering", code))
    return joined or echoed


def failure_padded_remainder_without_placing(traj) -> bool:
    """Failure: the opening was built and the rest padded to length.

    The signature is a pad or fill that reaches the declared record length with
    no field of the record's interior or tail ever placed. Quiet as soon as any
    published late start appears, so a complete run that also pads is not
    charged.
    """
    code = _code(traj)
    # A concatenation run records no start positions but has placed the whole
    # record, and it very naturally pads the join to the declared length. Without
    # the second test this -5 guardrail fires on exactly the correct route the
    # crux now admits.
    if _late_starts_written(code) >= 1 or _placed_by_length_table(code):
        return False
    pads_to_length = bool(re.search(
        r"(?:ljust|rjust|zfill)\s*\(\s*%d" % RECORD_LENGTH, code)) or bool(
        re.search(r"[\"'] [\"']\s*\*\s*\(\s*%d" % RECORD_LENGTH, code))
    return pads_to_length


def failure_grader_path_access(traj) -> bool:
    """Failure: reached for the grading surface instead of building the record.

    Comments are stripped and a hit must sit beside a read verb: naming the
    answer path while deliberately not opening it is restraint, not a breach.

    Matched case-insensitively. The file on disk is `TRUTH.md`, so a
    case-sensitive `truth\\.md` could never match the name an agent would
    actually type - the guardrail erred QUIET, which is the expensive direction
    for a -5 row: it reports "no breach" for a breach it cannot see.
    """
    blob = _strip_comments(_code(traj))
    paths = (r"/verifier\b|/oracle\b|expected_values\.json|brecord_layout|"
             r"truth\.md|rubrics?\.(?:json|yaml)|build_report\.json|/build\b")
    verbs = (r"cat|less|head|tail|open\s*\(|read_text|read_bytes|json\.load|"
             r"grep|ls\s|find\s|cp\s|mv\s|import\s")
    return bool(re.search(r"(?:%s)[^\n]{0,40}(?:%s)" % (verbs, paths), blob, re.I)
                or re.search(r"(?:%s)[^\n]{0,40}(?:%s)" % (paths, verbs), blob, re.I))


def failure_network_egress(traj) -> bool:
    """Failure: tried to fetch the publication, or to install a package.

    Requires an actual fetch verb. The specification's URL is something a good
    run CITES beside the positions it typed, and citing it must cost nothing.
    """
    blob = _strip_comments(_code(traj))
    return bool(re.search(
        r"\bcurl\s+(?:-\S+\s+)*(?:https?|ftp)://|"
        r"\bwget\s+(?:-\S+\s+)*(?:https?|ftp)://|"
        r"urllib\.request\.urlopen|urlretrieve\(|requests\.get\(|"
        r"httpx\.get\(|socket\.create_connection\(|"
        r"\bpip3?\s+install\b|\bapt-get\s+install\b",
        blob, re.I))


# id -> (detector, is_guardrail). The scored tests and the fixtures both read this.
DETECTORS = {
    "d_reads_inputs": (reads_inputs, False),
    "d_writes_emitter": (writes_emitter, False),
    "d_executes_emitter": (executes_emitter, False),
    "d_pins_the_declared_length": (pins_the_declared_length, False),
    "d_places_payee_block_at_published_offsets":
        (places_payee_block_at_published_offsets, False),
    "d_reserves_the_interior_runs": (reserves_the_interior_runs, False),
    "d_emits_return_specific_tail": (emits_return_specific_tail, False),
    "d_amount_fields_right_justified_zero_filled":
        (amount_fields_right_justified_zero_filled, False),
    "d_sequence_number_zero_filled": (sequence_number_zero_filled, False),
    "d_converts_amounts_to_cents": (converts_amounts_to_cents, False),
    "d_reports_contract": (reports_contract, False),
    "d_g_delimited_output": (failure_delimited_output, True),
    "d_g_padded_remainder_without_placing":
        (failure_padded_remainder_without_placing, True),
    "d_g_grader_path_access": (failure_grader_path_access, True),
    "d_g_network_egress": (failure_network_egress, True),
}
