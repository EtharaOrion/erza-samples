"""Deterministic detections over a normalised trajectory.

Each function is a *hypothesis about how a correct run is spelled*. The channel
pattern-matches the source the agent authored (`agent_code` = file writes plus
the commands it ran) - strictly weaker than executing the agent's solver, and the
largest source of false negatives on unseen runs (see the module docstring of test_output.py). The matchers are
deliberately multi-spelling, and every one was bound, at authoring time, by a
fixture in the author-side negative-fixture matrix that was seen to FIRE on a
planted defect and to stay QUIET on a clean run.

Convention: positive detectors return True when the criterion is SATISFIED.
Guardrail detectors are named `failure_*` and return True when the FAILURE MODE
OCCURRED; the scored test then asserts the failure did NOT occur.

The single argument is any object exposing `.agent_code`, `.commands`,
`.agent_prose` and `.file_writes` - a real `trajectory.Trajectory` in production,
or one loaded from a synthetic run directory in the fixtures.

WHY THE PUBLISHED CELLS ARE IN THIS FILE. The crux of this task is whether the
run held the published duty-period matrix at all, so the only honest
deterministic test for it is a numeric one: do enough literals that read as
published cells, at any of the spellings a solver actually uses, appear beside an
index on both axes? That requires the cell set here. This file is grader-side
only - `environment/Dockerfile` copies `environment/data` and nothing else, and
`/verifier` is in `sandbox_locked_paths` - so it is not a leak path. The values
are the ones parsed from the source cited in `TRUTH.md:Sources` at the bundle root.
"""
from __future__ import annotations

import re

# --- published cells, in minutes -------------------------------------------
# Unaugmented matrix, every distinct value.
TABLE_B_CELLS = (540, 600, 630, 660, 690, 720, 750, 780, 840)
# Augmented matrix, every distinct value.
TABLE_C_CELLS = (780, 810, 840, 870, 900, 930, 960, 990, 1020, 1080, 1110, 1140)
# The two values that occur in NEITHER matrix as a whole hour and so are the
# strongest single signal that a real cell was written down rather than guessed.
HALF_HOUR_CELLS = (630, 690, 750, 810, 870, 930, 990, 1050, 1110)

FLAT_CEILING = 840          # the fourteen-hour figure the flat route reaches for
EXTENSION = 120             # the relief for unforeseen circumstances

LIMIT_CODES = (
    "flight_duty_period", "flight_time", "rest_before_duty",
    "free_period_168h", "cumulative_fdp_168h", "cumulative_fdp_672h",
    "cumulative_flight_672h",
)


def _code(traj) -> str:
    return traj.agent_code or ""


def _cmds(traj) -> str:
    return "\n".join(traj.commands)


def _prose(traj) -> str:
    return traj.agent_prose or ""


def _strip_comments(src: str) -> str:
    """Drop `#` comments. A run that writes "never read /tests/..." in a
    comment is describing restraint; charging a guardrail for saying so punishes
    exactly the behaviour we want."""
    return "\n".join(re.sub(r"#.*$", "", ln) for ln in src.splitlines())


def _minutes_written(src: str) -> set[int]:
    """Every duration in the source, in minutes, whatever spelling it used.

    Four spellings are seen in the wild and all four count:
      * whole minutes            690
      * an h:mm string           "11:30"
      * arithmetic               11.5 * 60, 11 * 60 + 30
      * a bare decimal hour      11.5   (in a table converted at lookup)

    The last one was missing and cost a CRUX. A run that stores the matrix in
    decimal hours and converts once at lookup --

        TABLE_B = [..., [12, 12, 12, 12, 11.5, 11, 10.5], ...]
        return int(round(row[col] * 60))

    -- has written every half-hour cell down, but no literal here is adjacent to
    a `* 60`, and the integer pattern deliberately refuses digits touching a dot,
    so `11.5` matched nothing at all. The check then read a complete, correctly
    indexed matrix as an absent one.

    Broadening this cannot manufacture a pass: every caller intersects the result
    with the published cell constants, so a number only counts if the run wrote a
    value that IS a published cell.
    """
    found: set[int] = set()
    for m in re.finditer(r"(?<![\w.])(\d{1,4})(?![\w.])", src):
        found.add(int(m.group(1)))
    for m in re.finditer(r"(\d{1,2}):([0-5]\d)", src):
        found.add(int(m.group(1)) * 60 + int(m.group(2)))
    for m in re.finditer(r"(\d{1,2}(?:\.\d+)?)\s*\*\s*60", src):
        found.add(int(round(float(m.group(1)) * 60)))
    for m in re.finditer(r"(\d{1,2})\s*\*\s*60\s*\+\s*(\d{1,2})", src):
        found.add(int(m.group(1)) * 60 + int(m.group(2)))
    for m in re.finditer(r"(?<![\w.])(\d{1,2}\.\d+)(?![\w.])", src):
        found.add(int(round(float(m.group(1)) * 60)))
    return found


def _distinct_published_cells(src: str) -> int:
    written = _minutes_written(src)
    return len(written & (set(TABLE_B_CELLS) | set(TABLE_C_CELLS)))


def _half_hour_cells(src: str) -> int:
    return len(_minutes_written(src) & set(HALF_HOUR_CELLS))


# --------------------------- positive detectors ---------------------------

def reads_roster(traj) -> bool:
    blob = _code(traj) + "\n" + _cmds(traj)
    return bool(re.search(r"/root/data|pairings\.csv|question\.json", blob))


def writes_solver(traj) -> bool:
    for path, content in traj.file_writes:
        if path.endswith(".py") and re.search(r"\bdef\b|\bfor\b", content):
            return True
    return bool(re.search(r"<<\s*['\"]?\w*EOF|python3?\s+-\s*<<", _cmds(traj)))


def executes_solver(traj) -> bool:
    return bool(re.search(r"\bpython3?\b[^\n]*\.py|\bpython3?\b\s*-\s*<<|"
                          r"\bpython3?\s+-c\b", _cmds(traj)))


def normalises_to_one_clock(traj) -> bool:
    """TRUTH.md Step 1: every clock time and duration reduced to whole minutes,
    with the overnight wrap handled.

    Two halves, and both are required, because either alone is satisfied by a run
    that got the other wrong:

      * durations parsed out of `h:mm` into a number, rather than compared as
        strings ("Nothing downstream should ever compare a string");
      * a release earlier on the clock than its report treated as the next day.

    Route-open on both: the wrap may be a modulo, a conditional `+= 1440`, a
    `timedelta(days=1)`, or a date increment, and the day may be spelled 1440,
    24*60, 86400 or 24. No spelling is privileged.
    """
    src = _strip_comments(_code(traj))
    parsed = bool(re.search(
        r"split\s*\(\s*[\"']:[\"']|strptime|fromisoformat|"
        r"int\s*\(\s*\w+\s*\[\s*:?\s*2\s*\]|"
        r"\*\s*60\s*\+|"
        r"\bhours?\b[^\n]{0,20}\*\s*60|to_?min\w*|"
        r"(?:mins?|minutes)\s*\(", src, re.I))
    wrapped = bool(re.search(
        r"%\s*(?:1440|24\s*\*\s*60|86400|\(\s*24\s*\*\s*60\s*\))"
        r"|\+=\s*(?:1440|24\s*\*\s*60|86400)"
        r"|\+\s*(?:1440|24\s*\*\s*60|86400)\b"
        r"|timedelta\s*\(\s*days\s*=\s*1"
        r"|\bnext[_ ]?day\b|\bovernight\b|\bcrosses[_ ]midnight\b"
        r"|%\s*24\b", src, re.I))
    return parsed and wrapped


def splits_augmented_regime(traj) -> bool:
    """Routed the augmented pairings to their own matrix."""
    src = _strip_comments(_code(traj))
    crew = re.search(r"pilots_assigned\b[^\n]{0,40}(?:==|!=|>|<|>=|<=|in\b)"
                     r"|\bpilots\b[^\n]{0,20}(?:==|>|>=|in\b)\s*[234]", src)
    facility = re.search(r"onboard_rest_facility|rest_facility|class_[123]|"
                         r"facility_class", src)
    return bool(crew and facility)


def indexes_matrix_on_both_axes(traj) -> bool:
    """CRUX. Enough published cells written down, indexed on both axes."""
    src = _strip_comments(_code(traj))
    if _distinct_published_cells(src) < 6:
        return False
    if _half_hour_cells(src) < 2:
        return False
    segment_axis = re.search(
        r"\bsegments?\b|\bseg\b|\bn_?seg\w*|\bnum_?segments\b", src)
    time_axis = re.search(
        r"report_local|report_time|report_min\w*|band|row|0?[0-9]{3,4}\s*-\s*[0-9]{4}"
        r"|start_time", src)
    return bool(segment_axis and time_axis)


def applies_acclimation_reduction(traj) -> bool:
    src = _strip_comments(_code(traj))
    if not re.search(r"acclimat", src, re.I):
        return False
    return bool(re.search(r"(?<![\w.])30(?![\w.])|0:30|\bhalf[_ ]?hour\b", src))


def tests_split_duty_conditions(traj) -> bool:
    """At least three of the published conditions on the accommodation rest."""
    src = _strip_comments(_code(traj))
    conditions = 0
    if re.search(r"22:00|1320|22\s*\*\s*60", src) and \
            re.search(r"05:00|\b300\b|5\s*\*\s*60", src):
        conditions += 1
    if re.search(r"(?<![\w.])180(?![\w.])|3:00|3\s*\*\s*60", src):
        conditions += 1
    if re.search(r"suitable", src, re.I):
        conditions += 1
    if re.search(r"after_first_segment|first[_ ]segment", src, re.I):
        conditions += 1
    if re.search(r"(?<![\w.])840(?![\w.])|14:00|14\s*\*\s*60", src):
        conditions += 1
    return conditions >= 3


def enumerates_all_limits(traj) -> bool:
    """All seven published limits are actually EVALUATED, not merely named.

    Both directions of the old test were wrong, and in opposite ways.

    It asked only whether each of the seven code strings appeared anywhere in the
    authored source. So a run that echoed the prompt's vocabulary - pasted the
    contract into a comment, or shelled `cat /root/data/question.json` into the
    transcript - PASSED without computing a single margin. And a run that read the
    same seven codes out of the shipped question.json, which ships `limit_codes`
    precisely so they need not be retyped, FAILED for not retyping them. That is
    the constant-appearing-inline case REQUIREMENTS.md:324-341 names outright: a
    criterion must not bind to a value appearing inline where the same value may
    legitimately be loaded from a shipped file.

    Now: the codes must reach a position where each one carries a margin - as
    mapping keys being assigned, or as an iteration over the codes read from the
    input that computes a margin per code. Comments are stripped first, so a
    quoted contract earns nothing.
    """
    src = _strip_comments(_code(traj))

    # (1) each code written down where it BINDS a value - a mapping entry, a
    #     subscripted assignment, or an element of an enumerated sequence.
    bound = 0
    for code in LIMIT_CODES:
        q = r"[\"']" + re.escape(code) + r"[\"']"
        if re.search(q + r"\s*:", src) or re.search(q + r"\s*\]\s*=", src) \
                or re.search(r"[\[\(,]\s*" + q, src):
            bound += 1
    if bound >= len(LIMIT_CODES):
        return True

    # (2) the codes were taken from the shipped input and every one evaluated.
    #     This is the better route, not a lesser one: it cannot drift from the
    #     contract, whereas a retyped list can.
    loaded = re.search(
        r"[\"'](?:limit_codes|limits)[\"']\s*\]"
        r"|\b(?:limit_codes|limits|codes)\s*=\s*[^\n]{0,80}"
        r"(?:question|q\b|data|spec|payload|contract|json\.load)", src, re.I)
    per_code = re.search(
        r"\bfor\s+\w+\s+in\s+[^\n]{0,60}\b(?:limit_codes|limits|codes)\b", src, re.I) \
        or re.search(r"\b(?:limit_codes|limits|codes)\b[^\n]{0,60}"
                     r"(?:margin|slack|remaining|compute|evaluate)", src, re.I) \
        or re.search(r"(?:margin|slack|remaining)\w*\s*(?:\[|\.get\s*\()\s*"
                     r"[^\]\)\n]{0,30}\b(?:code|c|limit|k)\b", src, re.I)
    return bool(loaded and per_code)


# The pairing's own contribution, however the run named it. `\b(fdp|duty|flight)\w*`
# cannot match `net_fdp` or `sched_flt` -- `_` is a word character, so there is no
# boundary before `fdp` -- and those are the names runs actually choose.
#
# This is used ONLY immediately after an arithmetic operator. It must not be used
# in the reverse direction: the dict KEY on these lines is itself called
# `cumulative_fdp_168h`, so a pattern this broad searching backwards matches the
# label and the criterion becomes unfailable. The negative fixture for this
# criterion catches exactly that, and did.
_ADDED_TERM = r"\w*(?:fdp|duty|flight|flt)\w*"
# Narrow form, safe to search backwards: cannot match inside `cumulative_fdp_168h`.
_DUTY_TERM = r"\b(?:fdp|duty|flight)\w*"


def includes_pairing_in_rolling_totals(traj) -> bool:
    """The pairing's own duty and flight time enter the rolling totals.

    The history column may be added directly, or -- more usually, and more
    readably -- bound to a local first and the arithmetic done on that:

        prior_fdp_7 = hm(r["prior_fdp_rolling_7d"])
        ...
        "cumulative_fdp_168h": 60*60 - (prior_fdp_7 + net_fdp)

    Matching only the raw column name next to the operator read that as the
    pairing never entering the total, which is the opposite of what it does. So
    each history column's aliases are resolved first and counted the same way.
    """
    src = _strip_comments(_code(traj))
    hits = 0
    for hist in (r"prior_fdp_rolling_7d", r"prior_fdp_rolling_28d",
                 r"prior_flight_rolling_28d"):
        names = [hist]
        # `X = ...<hist>...` binds X to this history column.
        names += re.findall(r"(?m)^\s*(\w+)\s*=\s*[^\n]*" + hist, src)
        found = False
        for name in names:
            pat = re.escape(name) if name != hist else hist
            # Forward: the history term, then an operator, then the pairing's own
            # quantity as the very next token. Anchoring the term to the operator
            # is what keeps a nearby dict key from standing in for a real addend.
            if re.search(pat + r"[^\n]{0,80}?[-+]\s*\(?\s*" + _ADDED_TERM, src) or \
               re.search(_DUTY_TERM + r"[^\n]{0,60}" + pat, src):
                found = True
                break
        hits += 1 if found else 0
    return hits >= 2


_MARGIN_WORD = r"(?:margin|binding|slack|remaining|limit_codes|\bcodes\b)"
# What a run calls the running minimum it is carrying. Deliberately excludes bare
# `min` and any `*_min` suffix: `if a <= report_min <= b` is a band test, not a
# selection, and admitting it would make this criterion unfailable.
_BEST_NAME = (r"(?:best|smallest|lowest|tightest|tight|worst|binding|critical|"
              r"winner|chosen|min_\w+)")


def takes_minimum_margin(traj) -> bool:
    """The binding limit is the one with the smallest margin.

    Selecting a minimum by a hand-rolled scan is the same selection as calling
    `min`. Requiring `min` / `sorted` / `argmin` / `nsmallest` failed a run that
    kept a running best - `if best is None or margins[code] < margins[best]:
    best = code` - which is a correct argmin written out, and it is what a run
    reaches for when it also wants the published tie-break order. Binding a
    criterion to a builtin's name is the named-library restriction of
    REQUIREMENTS.md:324-341 in miniature.
    """
    src = _strip_comments(_code(traj))
    # a library or comprehension minimum over the margins
    if re.search(r"\b(?:min|sorted|argmin|nsmallest|idxmin)\s*\(\s*[^\n]{0,120}?"
                 + _MARGIN_WORD, src, re.I):
        return True
    if re.search(_MARGIN_WORD + r"[^\n]{0,120}?\.(?:idxmin|argmin|nsmallest)\b",
                 src, re.I):
        return True
    # a hand-rolled scan: a running best, replaced on a smaller comparison. All
    # three signals must sit on ONE line - the comparison, the running-best name
    # and the margin being compared - so that a band test or an unrelated
    # inequality elsewhere in the solver cannot satisfy it.
    for line in src.splitlines():
        if "<" in line and re.search(r"\b" + _BEST_NAME + r"\b", line, re.I) \
                and re.search(_MARGIN_WORD, line, re.I):
            return True
    return False


def reports_contract(traj) -> bool:
    blob = _code(traj) + "\n" + _cmds(traj)
    if "/root/results.json" not in blob:
        return False
    return all(f in blob for f in ("fdp_margin_min", "binding_limit",
                                   "binding_margin_min"))


# --------------------------- guardrail detectors --------------------------

def failure_flat_duty_ceiling(traj) -> bool:
    """A single flat ceiling in place of the matrix."""
    src = _strip_comments(_code(traj))
    if _distinct_published_cells(src) >= 6:
        return False
    return bool(re.search(r"(?<![\w.])840(?![\w.])|14:00|14\s*\*\s*60|"
                          r"(?<![\w.])960(?![\w.])|16:00", src))


def failure_extension_applied_to_schedule(traj) -> bool:
    """The unforeseen-circumstances relief added to a scheduled ceiling."""
    src = _strip_comments(_code(traj))
    added = re.search(r"[+]\s*(?:120|2\s*\*\s*60)(?![\w.])"
                      r"|[+]\s*\w*(?:extension|extend)\w*"
                      r"|(?:extension|extend)\w*\s*=\s*(?:120|2\s*\*\s*60)(?![\w.])",
                      src, re.I)
    named = re.search(r"extension|extend\w*|unforeseen", src, re.I)
    return bool(added and named)


def failure_grader_path_access(traj) -> bool:
    blob = _strip_comments(_code(traj) + "\n" + _cmds(traj))
    return bool(re.search(
        r"/verifier\b|/oracle\b|expected_values|part117\.xml|reg_reparse|"
        r"truth\.md|rubric\.yaml|(?:^|\s)build/|part117_tables", blob, re.I | re.M))


def failure_network_egress(traj) -> bool:
    blob = _strip_comments(_code(traj) + "\n" + _cmds(traj))
    return bool(re.search(
        r"\bcurl\b|\bwget\b|requests\.(?:get|post)\(|urllib\.request|"
        r"pip\s+install|apt-get\s+install|httpx\.(?:get|post)\(", blob))


# --------------------------- registry -------------------------------------
# cid -> (detector, is_guardrail). The fixture matrix iterates this, so a
# detector that is not registered is not exercised.
DETECTORS = {
    "d_reads_roster": (reads_roster, False),
    "d_writes_solver": (writes_solver, False),
    "d_executes_solver": (executes_solver, False),
    "d_normalises_to_one_clock": (normalises_to_one_clock, False),
    "d_splits_augmented_regime": (splits_augmented_regime, False),
    "d_indexes_matrix_on_both_axes": (indexes_matrix_on_both_axes, False),
    "d_applies_acclimation_reduction": (applies_acclimation_reduction, False),
    "d_tests_split_duty_conditions": (tests_split_duty_conditions, False),
    "d_enumerates_all_limits": (enumerates_all_limits, False),
    "d_includes_pairing_in_rolling_totals": (includes_pairing_in_rolling_totals,
                                             False),
    "d_takes_minimum_margin": (takes_minimum_margin, False),
    "d_reports_contract": (reports_contract, False),
    "d_g_flat_duty_ceiling": (failure_flat_duty_ceiling, True),
    "d_g_extension_applied_to_schedule": (failure_extension_applied_to_schedule,
                                          True),
    "d_g_grader_path_access": (failure_grader_path_access, True),
    "d_g_network_egress": (failure_network_egress, True),
}
