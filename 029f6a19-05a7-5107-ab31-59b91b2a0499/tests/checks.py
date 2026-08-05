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

WHY THE PUBLISHED COEFFICIENTS ARE IN THIS FILE. The crux of this task is whether
the run evaluated the publisher's fitted equations, so the only honest
deterministic test for it is a numeric one: do literals that read as those
coefficients, at any sane rounding, appear somewhere they can act? That requires
the constants here. This file is grader-side only - `environment/Dockerfile`
copies `environment/data` and nothing else, and `/verifier` is in
`sandbox_locked_paths` - so it is not a leak path. This is TRANSCRIPTION 4 of 4; the
author-side rederivation matrix asserted it equals the slice cut from the
published PDF.

Source: Ingram DD, Parker JD, Schenker N, Weed JA, Hamilton B, Arias E,
Madans JH. United States Census 2000 population with bridged race categories.
National Center for Health Statistics. Vital Health Stat 2(135). 2003,
Tables 7 and 8.
"""
from __future__ import annotations

import re

# Table 7, column-major: one list per fitted column, in the published row order
# (age, Hispanic, sex, NE, MW, S, large suburban, medium/small metro, nonmetro,
# percent AIAN, percent API, percent Black, percent multiple, constant). Cells the
# published table marks "not in model" are omitted rather than written as zero.
TABLE7 = {
    ("AIAN_BLACK", "BLACK"): [-0.05461, -1.92602, -0.12359, -0.88349, -1.70126,
                              -0.97935, -0.44211, 0.88281, -0.38427, -0.43045,
                              0.0000258, -0.16934, 3.08086],
    ("AIAN_WHITE", "AIAN"): [-0.08968, 0.88834, 0.00972, 0.21233, 0.09144,
                             -0.28494, -0.22069, -0.44238, -0.13978, 0.51235,
                             -0.07906, -0.70527],
    ("API_BLACK", "BLACK"): [0.05669, -0.10458, 0.33642, -0.45997, -3.92403,
                             -1.48264, 1.46590, 1.67953, 0.13301, -0.13245,
                             0.02078, 0.31250, 0.45883],
    ("API_WHITE", "API"): [0.09568, 0.19303, 0.01393, -0.05520, -0.06453,
                           0.12694, 0.50556, 0.07443, -0.62956, 0.00735,
                           0.09791, -1.18887],
    ("BLACK_WHITE", "BLACK"): [0.05532, -0.52253, 0.11948, -0.25363, 0.17140,
                               -0.64386, -0.07649, 0.28938, 0.57636, 0.00079,
                               0.31679, -0.17533],
    ("AIAN_BLACK_WHITE", "AIAN"): [0.26212, 0.35986, -0.43898, -4.53976,
                                   -3.82328, -5.73385, 2.78910, 2.27176,
                                   4.17804, 0.54579, 0.11100, -0.23972,
                                   -0.64594],
    ("AIAN_BLACK_WHITE", "BLACK"): [0.36140, -0.83526, 0.50777, -3.45593,
                                    -3.79144, -2.27313, 2.31011, 0.75477,
                                    1.64725, 0.39101, 0.04985, -0.02919,
                                    0.77004],
}
# Table 8, column-major: AIAN, API, BLACK. The three indicators come first, with
# the constrained-to-zero entry omitted.
TABLE8 = {
    "AIAN": [2.83058, 0.97010, -0.03967, 0.84013, 0.01914, 0.59649, 0.43237,
             -0.22255, 0.15744, -0.17318, 0.25013, 0.56512, 0.04203, 0.03921,
             -0.09723, -5.29417],
    "API": [2.78725, 1.61570, 0.01946, 0.21507, 0.01283, -0.13221, -0.15172,
            -0.24854, 0.46028, -0.09493, -0.15342, 0.06996, 0.03741, 0.03590,
            0.06402, -5.73987],
    "BLACK": [2.19772, 3.06153, -0.01691, -0.58721, -0.08093, 0.40115, 0.20136,
              -0.29365, 0.12070, -0.11129, -0.12077, -0.00347, 0.05396,
              0.05893, -0.03953, -5.21431],
}
# The published country-wide averages the input ships as an orientation block.
# A run that reports these has taken the nearest real competitor.
ORIENTATION = {
    ("AIAN_API", "AIAN"): 0.404, ("AIAN_API", "API"): 0.596,
    ("AIAN_BLACK", "AIAN"): 0.186, ("AIAN_BLACK", "BLACK"): 0.814,
    ("AIAN_WHITE", "AIAN"): 0.205, ("AIAN_WHITE", "WHITE"): 0.795,
    ("API_BLACK", "API"): 0.370, ("API_BLACK", "BLACK"): 0.630,
    ("API_WHITE", "API"): 0.327, ("API_WHITE", "WHITE"): 0.673,
    ("BLACK_WHITE", "BLACK"): 0.621, ("BLACK_WHITE", "WHITE"): 0.379,
}

TABLE7_VALUES = tuple(v for series in TABLE7.values() for v in series)
TABLE8_VALUES = tuple(v for series in TABLE8.values() for v in series)
ALL_PUBLISHED = TABLE7_VALUES + TABLE8_VALUES

_NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")


def _code(traj) -> str:
    return traj.agent_code or ""


def _cmds(traj) -> str:
    return "\n".join(traj.commands)


def _strip_comments(src: str) -> str:
    """Drop `#` comments. A run that writes "never read /tests/..." in a
    comment is describing restraint; charging a guardrail for saying so punishes
    exactly the behaviour we want."""
    return "\n".join(re.sub(r"#.*$", "", ln) for ln in src.splitlines())


def _literals(code: str):
    out = []
    for m in _NUM_RE.finditer(code):
        try:
            out.append((m.group(0), float(m.group(0)), m.start()))
        except ValueError:
            continue
    return out


def _matches(code: str, target: float, rel: float = 1e-4):
    """Literals that read as `target` at any sane rounding (4 dp and up)."""
    tol = max(abs(target) * rel, 5e-7)
    return [t for t in _literals(code) if abs(t[1] - target) <= tol]


def _in_relation(code: str, target: float) -> bool:
    """The constant appears where it can ACT, however the run chose to spell it.

    "Where it can act" is a claim about position, not about vocabulary, so the
    accepted forms are the structural ones - operator adjacency, membership of a
    container or mapping literal, and BINDING BY NAME (`const = 3.08086`,
    `dict(notAPI=2.83058, ...)`, `beta["const"] = 3.08086`). Binding by name was
    missing and is the commonest way to write a coefficient table by hand; its
    absence failed a run that earned outcome reward 1.0000 while the detector
    itself found all 88 Table-7 and all 48 Table-8 coefficients present
    (REQUIREMENTS.md:324-341, the route-restriction ban).

    A bare mention in prose still does not count: a number sitting between words,
    or laid out in a markdown table, matches none of these.
    """
    for lit, _v, i in _matches(code, target):
        # Judge the literal WHERE IT WAS FOUND. Re-searching the whole file for the
        # digit string, as this did before, matched substrings of other numbers -
        # `-0.11129` contains `0.111`, and its leading minus then read as operator
        # adjacency, so a coefficient that never acted anywhere could be certified
        # as acting by an unrelated neighbour. Positional context cannot do that.
        before = code[max(0, i - 24):i]
        after = code[i + len(lit):i + len(lit) + 24]

        # multiplied, divided, added into an expression
        if re.search(r"[*/+\-]\s*$", before) or re.match(r"\s*[*/+\-]", after):
            return True
        # an element of a sequence, or the value of a mapping entry
        if re.search(r"[\(\[\{,:]\s*$", before) and re.match(r"\s*[,\)\]\}]", after):
            return True
        # bound to a name: assignment or keyword argument. `==`/`!=`/`<=`/`>=` are
        # comparisons, not bindings, and are excluded.
        if re.search(r"(?<![=!<>*/+\-])=\s*$", before) and \
                re.match(r"\s*(?:[,\)\]\}:;]|$)", after):
            return True
    return False


def _hits(code: str, values) -> int:
    return sum(1 for v in values if _matches(code, v))


# --------------------------- positive detectors ---------------------------

def reads_input(traj) -> bool:
    """Opened the baked input under /root/data."""
    return bool(re.search(r"response_records\.csv|area_profile\.csv|"
                          r"question\.json|/root/data\b", _code(traj), re.I))


def writes_solver(traj) -> bool:
    """Authored a solver (a .py file, or a heredoc'd / inline script)."""
    if any(str(p).endswith(".py") for p, _c in traj.file_writes):
        return True
    code = _code(traj)
    return bool(re.search(r"\bimport\b", code)) and bool(
        re.search(r"\bdef\b|json\.|csv\.|numpy|np\.|pandas|pd\.|math\.", code))


def executes_solver(traj) -> bool:
    """Ran python to produce the results rather than only drafting a script."""
    return bool(re.search(r"\bpython3?\b", _cmds(traj)))


def applies_published_coefficients(traj) -> bool:
    """CRUX. The publisher's fitted constants appear where they can act.

    Satisfied only when at least eight distinct coefficients from EACH published
    table appear, and at least one from each appears in a relation. An arithmetic
    split fails; the orientation block fails; one table alone fails, because five
    of the eleven response groups are governed by the other one.
    """
    code = _code(traj)
    if _hits(code, TABLE7_VALUES) < 8 or _hits(code, TABLE8_VALUES) < 8:
        return False
    if not any(_in_relation(code, v) for v in TABLE7_VALUES):
        return False
    return any(_in_relation(code, v) for v in TABLE8_VALUES)


# The record's response group, however the run bound it. `rec["response_group"]`
# is included so a run that dispatches straight off the read, without ever binding
# a variable, is not excluded on a naming convention.
_GROUP_EXPR = (r"(?:\w*\[\s*[\"']response_group[\"']\s*\]|"
               r"\bresponse_group\b|\bresp_group\b|\brespgroup\b|"
               r"\bgroups?\b|\bgrp\b|\bg\b|\bcombo\b|\bcombination\b)")

# A name that reads as an equation family, or as the set of response groups one
# family governs: an ALL-CAPS constant, or a word naming the published tables.
_FAMILY_NAME = (r"(?:[A-Z][A-Z0-9_]{2,}|"
                r"\w*(?:composite|separate|table_?[78]|own_?model|"
                r"famil(?:y|ies))\w*)")

# A response-group name as the publisher spells it: two or more categories joined.
_GROUP_LITERAL = (r"[\"'](?:AIAN|API|BLACK|WHITE)"
                  r"(?:[_+ ](?:AIAN|API|BLACK|WHITE))+[\"']")


def selects_model_family_per_group(traj) -> bool:
    """The response group decides which equation family is used.

    Corroborated two ways: the composite groups are separated from the groups with
    their own equations, AND the run actually DISPATCHES on the group.

    The dispatch test grades the decision, not its spelling. Requiring the index
    variable to be literally named `group|grp|g|response_group|key` failed three
    with-skill runs that each earned outcome reward 1.0000 and each dispatched
    correctly - `if grp in COMPOSITE:`, `if grp == 'AIAN+BLACK': ... elif ...`,
    and `if g=='AIAN+API': ... elif g in (...)`. Every one of those is the same
    decision in different words, which is precisely what §9's route-restriction
    ban protects (REQUIREMENTS.md:324-341).

    What is NOT accepted, and what keeps the check discriminating: merely reading
    `row["response_group"]` to split it into its categories. Every run does that,
    including the ones that then stretch a single equation family over all eleven
    groups. The group has to reach a conditional or an index that CHOOSES.
    """
    code = _code(traj)
    keyed = bool(re.search(r"response_group|RESPONSE_GROUP|\bgroup\b", code))
    composite = bool(re.search(
        r"AIAN[_+ ]?API(?![_+ ]?BLACK[_+ ]?WHITE)|COMPOSITE|composite", code))
    separate = bool(re.search(r"BLACK[_+ ]?WHITE|AIAN[_+ ]?WHITE|API[_+ ]?WHITE",
                              code))
    branch = bool(
        # the group is tested for membership of a family / group set
        re.search(_GROUP_EXPR + r"\s*(?:not\s+)?in\s+" + _FAMILY_NAME, code)
        # the group is compared against a published group name in a conditional
        or re.search(r"\b(?:if|elif|case|when)\b[^\n]{0,80}" + _GROUP_EXPR
                     + r"\s*(?:==|!=|\bin\b)\s*[^\n]{0,40}"
                     + r"(?:" + _GROUP_LITERAL + r"|\(|\[|\{)", code)
        # an equation-family container is indexed or .get() by the group
        or re.search(_FAMILY_NAME + r"\s*\[\s*" + _GROUP_EXPR + r"\s*\]", code)
        or re.search(_FAMILY_NAME + r"\s*\.get\s*\(\s*" + _GROUP_EXPR, code)
        # a family is chosen by a conditional expression on the group
        or re.search(_FAMILY_NAME + r"[^\n]{0,60}\bif\b[^\n]{0,60}" + _GROUP_EXPR,
                     code)
        # the original spellings, kept
        or re.search(r"\[\s*(?:group|grp|g|response_group|key)\s*\]|"
                     r"\.get\(\s*(?:group|grp|g|response_group|key)\b|"
                     r"\bif\b[^\n]{0,60}(?:group|GROUP)[^\n]{0,60}\bin\b", code))
    return keyed and composite and separate and branch


def applies_footnoted_transforms(traj) -> bool:
    """The logarithm of one area percentage and the square of another appear.

    Both footnotes have to be there: a run that takes the logarithm but not the
    square has read half the table's small print.
    """
    code = _code(traj)
    log = bool(re.search(r"math\.log\s*\(|np\.log\s*\(|numpy\.log\s*\(|"
                         r"\blog\s*\(", code))
    # `x ** 2` and `x * x` are the same square. Binding the check to the exponent
    # operator failed a run that earned outcome reward 1.0000 and wrote `pB*pB`
    # - a spelling difference, not a method difference (REQUIREMENTS.md:324-341).
    # Case-insensitive for the same reason: `pB` and `pb` are one variable.
    square = bool(re.search(r"\*\*\s*2\b|\*\*2\b|np\.square|numpy\.square|"
                            r"\bpow\s*\([^,]+,\s*2", code)) or bool(re.search(
        r"\b(\w*(?:pct_black|percent_black|black_pct|black|pb|blk)\w*)"
        r"\s*\*\s*\1\b", code, re.I))
    return log and square


def rescales_composite_over_named_categories(traj) -> bool:
    """The composite output is renormalised over the categories the group named.

    Two halves, and BOTH are required. A normalisation alone is not evidence:
    the three-category model with its own equations divides by a sum too. What
    distinguishes the rescale is that the set of outcomes taking part is
    RESTRICTED to the categories the response group named, before the division.
    """
    code = _code(traj)
    normalises = bool(re.search(
        r"/\s*sum\s*\(|/\s*(?:total|tot|denom|denominator|z)\b|"
        r"\bnormali[sz]e\b", code, re.I))
    restricts = bool(re.search(
        r"\bin\s+named\b|\bnot\s+in\s+named\b|"
        r"\bin\s+(?:group|groups|applicable|categories|cats|members|parts)\b|"
        r"\bsplit\s*\(\s*[\"']\+[\"']\s*\)|"
        r"\bin\s+row\s*\[\s*[\"']response_group[\"']\s*\]", code))
    return normalises and restricts


def caps_age_at_69(traj) -> bool:
    """The age variable is capped before it enters the equations."""
    code = _code(traj)
    return bool(re.search(r"\bmin\s*\([^\n]{0,60}\b69\b|"
                          r"\b69\b[^\n]{0,30}\bmin\b|"
                          r"\bif\b[^\n]{0,40}>\s*69\b|"
                          r"\bage\w*\b[^\n]{0,20}>=?\s*70\b|"
                          r"\bclip\s*\([^\n]{0,60}\b69\b",
                          code))


def reports_contract(traj) -> bool:
    """Emitted /root/results.json under the contracted top-level key."""
    code = _code(traj)
    return bool(re.search(r"results\.json", code, re.I)) and \
        "assignment_share" in code


# ----------------------- guardrail failure detectors -----------------------

def failure_arithmetic_split(traj) -> bool:
    """Failure: no fitted constant enters the run at all.

    Quiet as soon as three or more published coefficients appear anywhere, so a
    correct run that used terse names is not charged.
    """
    code = _code(traj)
    if _hits(code, ALL_PUBLISHED) >= 3:
        return False
    return True


def failure_single_model_for_every_group(traj) -> bool:
    """Failure: one equation family stretched over all eleven response groups.

    Fires when constants from exactly one of the two published tables are
    present. A run holding both tables is not charged, whatever it named them.
    """
    code = _code(traj)
    seven = _hits(code, TABLE7_VALUES)
    eight = _hits(code, TABLE8_VALUES)
    if seven + eight < 3:
        return False                      # that is failure_arithmetic_split's job
    return (seven >= 3) != (eight >= 3)


def failure_orientation_block_echoed(traj) -> bool:
    """Failure: the orientation block was copied through as the answer.

    The block's own key name embeds the contract key, so both names are collapsed
    to a token before matching - otherwise merely READING the orientation figure
    to compare against it would read as echoing it.
    """
    code = _code(traj)
    norm = re.sub(r"orientation_flat_shares|orientation\w*|\bflat_shares\b|"
                  r"\bflat\b", "ORIENT", code)
    return bool(
        re.search(r"assignment_share[\"'\]\s]*[:=][^\n]{0,80}ORIENT", norm)
        or re.search(r"ORIENT[^\n]{0,80}[\"']?results\.json", norm)
        or re.search(r"\]\s*=\s*ORIENT\b", norm)
        or re.search(r"results\w*\s*\[[^\]]*\]\s*=\s*ORIENT", norm))


def failure_grader_path_access(traj) -> bool:
    """Failure: reached for the grading surface instead of computing.

    Comments are stripped and a hit must sit beside a read verb: naming the
    answer path while deliberately not opening it is restraint, not a breach.
    """
    blob = _strip_comments(_code(traj))
    paths = (r"/verifier\b|/oracle\b|expected_values\.json|anchor_table9|"
             r"cell_universe|independent_bridging|bridging_models|truth\.md|"
             r"rubrics?\.json|build_report\.json|/build\b")
    verbs = (r"cat|less|head|tail|open\s*\(|read_text|read_bytes|json\.load|"
             r"np\.load|grep|ls\s|find\s|cp\s|mv\s|import\s")
    return bool(re.search(r"(?:%s)[^\n]{0,40}(?:%s)" % (verbs, paths), blob)
                or re.search(r"(?:%s)[^\n]{0,40}(?:%s)" % (paths, verbs), blob))


def failure_network_egress(traj) -> bool:
    """Failure: tried to fetch the published report or to install a package.

    Requires an actual fetch verb. The report's citation and URL are something a
    good run CITES beside the numbers it typed, and citing it must cost nothing.
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
    "d_reads_input": (reads_input, False),
    "d_writes_solver": (writes_solver, False),
    "d_executes_solver": (executes_solver, False),
    "d_applies_published_coefficients": (applies_published_coefficients, False),
    "d_selects_model_family_per_group": (selects_model_family_per_group, False),
    "d_applies_footnoted_transforms": (applies_footnoted_transforms, False),
    "d_rescales_composite_over_named_categories":
        (rescales_composite_over_named_categories, False),
    "d_caps_age_at_69": (caps_age_at_69, False),
    "d_reports_contract": (reports_contract, False),
    "d_g_arithmetic_split": (failure_arithmetic_split, True),
    "d_g_single_model_for_every_group": (failure_single_model_for_every_group, True),
    "d_g_orientation_block_echoed": (failure_orientation_block_echoed, True),
    "d_g_grader_path_access": (failure_grader_path_access, True),
    "d_g_network_egress": (failure_network_egress, True),
}
