"""Deterministic detections over a normalised trajectory.

Each function is a *hypothesis about how a correct run is spelled*. The channel is
pattern-matching over the source the agent authored, the commands it ran and the
tool inputs it issued - weaker than executing the agent's solver, and the largest
source of false negatives on unseen runs (see README). The matchers are
deliberately multi-spelling, and every spelling here was mined from the ten
recorded runs of this task; every detector is bound by a fixture in
`the grader self-audit fixtures` that has been *seen to fire*.

Convention: positive detectors return True when the criterion is SATISFIED.
Guardrail detectors are named `failure_*` and return True when the FAILURE MODE
OCCURRED; the scored test then asserts the failure did NOT occur.

The single argument is any object exposing `.agent_code`, `.commands`,
`.agent_prose`, `.file_writes`, `.tool_surface` and `.transcript` - a real
`trajectory.Trajectory` in production, or one loaded from a synthetic run
directory in the fixtures.

THE TRAP THIS FILE IS BUILT AROUND
----------------------------------
All five no-skill runs hunt the container for a harmonic-constant table with
commands like

    grep -rilE 'constituent|amplitude|greenwich phase|nodal|M2|S2|K1|O1' / ...
    grep -rlaE 'amplitude_m|phase_deg|speed_deg_per_hr|constituents"|"M2"' / ...

Those grep PATTERNS land in `agent_code`, because `agent_code` is file writes plus
commands. A crux detector that greps for `constituent`, `amplitude`, `harmonic` or
a constituent name therefore passes all five runs that never performed a synthesis
at all - and the previous version of this verifier did exactly that. Every detector
below that could be fooled this way requires a MECHANISM (a cosine accumulation, a
numeric method coefficient, a dot product) and not a vocabulary.

TWO THINGS THIS FILE DELIBERATELY DOES NOT CHARGE
-------------------------------------------------
The measured control ledger (see `rubrics.json: weight_evidence_source`) shows two
choices that do NOT break the outcome on this instance:

  * nodal corrections omitted entirely (f=1, u=0): 0.93x tolerance, 0/12 cases out
  * constituent set truncated to the ten largest:  0.92x tolerance, 0/12 cases out

`R9` is therefore weight 1 rather than 3, and the truncation
guardrail fires only on a whitelist of NINE OR FEWER constituent names - the
measured curve crosses the tolerance between N=9 (1.26x, 1 case out) and N=10.
"""
from __future__ import annotations

import json
import os
import ast
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
_BUNDLE = os.path.normpath(os.path.join(_HERE, "..", ".."))
_QUESTION = os.path.join(_BUNDLE, "environment", "data", "question.json")

# The shipped orientation values and target instants, read from the task's own input
# rather than hardcoded so they cannot drift. These are INPUTS, not answers - the
# guardrail below needs them to tell "emitted the observation" from "computed a
# height". The fallback keeps the detector usable if the bundle is not beside it.
_FALLBACK_DECOY = ["0.614", "0.595", "2.323"]
_FALLBACK_TIMES = ["2025-02-10T05:00:00Z", "2025-05-18T16:00:00Z",
                   "2025-08-22T09:00:00Z", "2025-11-14T21:00:00Z"]


def _shipped():
    try:
        with open(_QUESTION) as f:
            q = json.load(f)
        decoy = [f"{v:g}" for v in
                 q["decoy_reference"]["recent_observed_water_level_m"].values()]
        return decoy, list(q["target_times_utc"])
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return _FALLBACK_DECOY, _FALLBACK_TIMES


DECOY_VALUES, TARGET_TIMES = _shipped()

# Constituent names the gauge tables use, and the node-factor GROUP labels the
# Schureman table is keyed by. The two sets overlap, and telling them apart is what
# stops the truncation guardrail charging every correct run - see
# `failure_truncated_constituent_set`.
CONSTITUENT_NAMES = {
    "M2", "S2", "N2", "K1", "M4", "O1", "M6", "MK3", "MN4", "NU2", "MU2", "2N2",
    "OO1", "LAM2", "S1", "M1", "J1", "SSA", "SA", "MSF", "RHO", "Q1", "T2", "R2",
    "2Q1", "P1", "2SM2", "M3", "L2", "2MK3", "K2", "M8", "MS4",
}
NODE_FACTOR_GROUPS = {
    "M2", "K1", "O1", "K2", "J1", "OO1", "MF", "MM", "SOL",
    "M2^2", "M2^3", "M2^4", "MS4", "MK3", "2MK3", "M3",
}


def _strip_comments(src: str) -> str:
    """Blank out `#` comments AND docstrings, keeping line geometry.

    A regex over `#` alone leaves docstrings standing, so a run that DOCUMENTS
    its restraint - "the verifier deliberately does NOT import
    verifier/independent_energy.py" - trips the very guardrail that restraint
    satisfies, and a run that merely explains a convention in a docstring is
    credited for prose. Docstrings are bare string-expression statements:
    prose by construction, never operands.

    String literals used as VALUES are deliberately left alone.
    `open("/verifier/golden.json")` is access, not commentary, and must stay
    visible to the guardrails; `"observations.csv"` is the input the run read.

    Parsed with `ast` when the blob parses (`agent_code` concatenates every
    authored file, so it often does not); otherwise a triple-quoted block that
    OPENS a logical line is treated as prose - what a docstring looks like
    without a parser.
    """
    src = _strip_docstrings(src)
    return "\n".join(re.sub(r"#.*$", "", ln) for ln in src.splitlines())


_TRIPLE_OPEN = re.compile("[rRuUbBfF]{0,2}(\"\"\"|''')")


def _blank_prose_blocks(src: str) -> str:
    """Fallback docstring blanking for source the parser cannot read.

    This path is the one that RUNS: `agent_code` concatenates every authored
    file with every command, so it essentially never parses whole (measured: 0
    of 54 recorded runs), and the fallback's precision is what decides every
    criterion read off `code`.

    The previous fallback was one regex applied with `sub`: it matched from ANY
    triple quote that OPENED a line to the next one that CLOSED a line. The
    closing delimiter of a multi-line data literal sits at column 0, so a run
    that embeds a table, a heredoc body or any block constant as a
    triple-quoted literal had everything between that closing quote and the
    next function docstring DELETED from the graded view - real code, silently
    missing from every criterion. Measured across this dataset's runs, that
    removed up to 27% of the non-whitespace source. Carrying reference data as
    a literal is ordinary practice - this bundle's constituent tables are
    exactly that - so the bug fell hardest on the route the data invites.

    Delimiters are now PAIRED in source order, so an opening quote is matched
    with its own closing quote, and a pair counts as prose only when its
    opening delimiter starts a logical line - a literal assigned to a name is
    left standing, as this module's contract promises. Line geometry is
    preserved.
    """
    marks = list(_TRIPLE_OPEN.finditer(src))
    spans, k = [], 0
    while k + 1 < len(marks):
        opener, closer = marks[k], marks[k + 1]
        if opener.group(1) != closer.group(1):
            k += 1                       # unpaired style: resynchronise
            continue
        line_start = src.rfind("\n", 0, opener.start()) + 1
        if not src[line_start:opener.start()].strip():
            spans.append((opener.start(), closer.end()))
        k += 2
    if not spans:
        return src
    out = list(src)
    for lo, hi in spans:
        for i in range(lo, hi):
            if out[i] != "\n":
                out[i] = " "
    return "".join(out)


def _strip_docstrings(src: str) -> str:
    spans = _docstring_spans(src)
    if spans is None:
        return _blank_prose_blocks(src)
    out = src.splitlines(True)
    for lo, hi in spans:                      # 1-based, inclusive
        for i in range(lo - 1, min(hi, len(out))):
            out[i] = "\n" if out[i].endswith("\n") else ""
    return "".join(out)


def _docstring_spans(src):
    """[(first_line, last_line)] for every bare string-expression statement, or
    None when the blob does not parse as Python."""
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return None
    spans = []
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            block = getattr(node, field, None)
            # `Lambda.body` and `IfExp.body` are EXPRESSIONS, not statement
            # lists; iterating them raises TypeError on perfectly ordinary
            # source. Only statement blocks can hold a docstring.
            if not isinstance(block, list):
                continue
            for stmt in block:
                if (isinstance(stmt, ast.Expr)
                        and isinstance(getattr(stmt, "value", None), ast.Constant)
                        and isinstance(stmt.value.value, str)):
                    spans.append((stmt.lineno,
                                  getattr(stmt, "end_lineno", None) or stmt.lineno))
    return spans


def _code(traj) -> str:
    return _strip_comments(traj.agent_code or "")


def _cmds(traj) -> str:
    return "\n".join(traj.commands)


def _surface(traj) -> str:
    """Code + commands + every tool input, including read-only calls.

    A read-only tool call carries a `file_path` and no `content`, so it appears in
    neither `file_writes` nor `commands`. Any detector asking "did the run open /
    reference this path?" must consult this, or it reports a false negative on
    every run that used the read tool. See `trajectory.Trajectory.tool_surface`.
    """
    return "\n".join([
        traj.agent_code or "",
        _cmds(traj),
        getattr(traj, "tool_surface", "") or "",
    ])


_ASSIGN = re.compile(r"^\s*([A-Za-z_]\w*)\s*=\s*(.+)$")


def _bound_names(code: str, seed: re.Pattern, hops: int = 4) -> set[str]:
    """Every local name transitively bound to an expression matching `seed`.

    Real runs bind a field to a short name and then use the name, so a detector
    anchored on the field spelling alone reports a false negative. Two examples
    from the recorded runs, one per direction:

      * with-skill run_2: `dood = cd["doodson"]` then
        `V = sum(dood[i]*a[i] for i in range(6)) + semi` - the dot product never
        mentions `doodson` at all;
      * no-skill run_2: `decoy = q['decoy_reference'][...]` then
        `est = round(float(decoy[sid]), 3)` then `{t: est for t in times}` - two
        hops before the value reaches the emitted answer.
    """
    bound: set[str] = set()
    for _ in range(hops):                    # fixed point, small by construction
        grew = False
        for line in code.splitlines():
            m = _ASSIGN.match(line)
            if not m:
                continue
            name, rhs = m.group(1), m.group(2)
            if name in bound:
                continue
            if seed.search(rhs) or any(
                    re.search(rf"\b{re.escape(b)}\b", rhs) for b in bound):
                bound.add(name)
                grew = True
        if not grew:
            break
    return bound


def _harmonic_sum(code: str) -> bool:
    """A cosine (or complex-exponential) accumulation - the mechanism, not the word.

    All five with-skill runs spell it `math.cos(2*math.pi*V + ...)`. The exponential
    alternatives are accepted because they are genuinely equivalent routes to the
    same sum, not because any recorded run used one.
    """
    return bool(re.search(r"\bcos\s*\(|\bcosd?\s*\(|np\.cos|math\.cos"
                          r"|exp\s*\(\s*1j|cmath\.exp|\bphasor\b", code, re.I))


# --------------------------- positive detectors ---------------------------

def reads_inputs(traj) -> bool:
    """Opened the shipped station list / question file rather than working from the
    prose task statement alone.

    Consults the whole tool surface, not just `agent_code`: a run that opens an
    input with a read-only tool leaves no trace in either `file_writes` or
    `commands`.
    """
    return bool(re.search(r"stations\.csv|question\.json|/root/data\b",
                          _surface(traj), re.I))


def writes_solver(traj) -> bool:
    """Authored solver source: a `.py` file write, a heredoc, or `python -c`.

    Both spellings occur here and a detector accepting only one would fail five
    runs: all five with-skill runs write `tide.py` / `predict.py` with a write tool,
    all five no-skill runs author theirs as `python3 - <<'PY'` or `python3 -c`.
    """
    if any(str(p).endswith(".py") for p, _ in traj.file_writes):
        return True
    return any(
        re.search(r"\bpython3?\b", c) and re.search(r"<<|\s-c\b", c)
        for c in traj.commands
    )


def executes_solver(traj) -> bool:
    """Ran python to produce the result."""
    return bool(re.search(r"\bpython3?\b", _cmds(traj)))


def uses_station_constants(traj) -> bool:
    """THE CRUX: synthesised the tide from the gauge's own harmonic constants.

    Three things must be present together, and the conjunction is the point:

      1. the per-gauge constant table, by its field names or its filename;
      2. an accumulation through a cosine (or an equivalent complex exponential);
      3. that accumulation running over the gauge's CONSTITUENT LIST, not over one
         value.

    Requirement (2) and (3) are what stop the no-skill runs passing. Four of the
    five spell `amplitude_m` / `constituents` / `harmonic_constants` inside a
    filesystem-wide `grep` pattern while hunting for a table they never found - one
    of them (no-skill run_4) greps for the literal string `amplitude_m` - so a
    vocabulary match alone scores all five as having synthesised the tide. None of
    them writes a cosine.
    """
    code = _code(traj)
    table = bool(re.search(
        r"amplitude_m\b|phase_gmt|phase_gmt_deg|harmonic_constants"
        r"|msl_minus_mllw|\bamplitude\b[^\n]{0,40}\bphase\b"
        r"|\bphase\b[^\n]{0,40}\bamplitude\b",
        code, re.I))
    over_constituents = bool(re.search(
        r"for\s+\w+\s+in\s+[^\n]{0,80}constituent"
        r"|constituents[^\n]{0,40}\.items\s*\("
        r"|for\s+\w+\s*,\s*\w+\s+in\s+[^\n]{0,80}constituent",
        code, re.I))
    return table and _harmonic_sum(code) and over_constituents


_NUM_RE = re.compile(r"\d+(?:\.\d+)?")
# `s = 270.434164 + 13.1763965268*d` - the SHAPE of a mean-longitude
# polynomial, independent of which publication's coefficients fill it in.
_POLY_ASSIGN = re.compile(
    r"\b\w+\s*=\s*[-+]?\s*\d{1,3}\.\d+\s*[-+]\s*\d+\.\d+\s*\*")


def _numeric_hit(code: str, targets, rel: float = 2e-4) -> bool:
    """Any literal in `code` reading as one of `targets`, at ANY truncation.

    Matching decimal STRINGS binds the criterion to one publication's number of
    printed digits: `270.434164`, `270.4342` and `270.434` are the same
    constant, and a run that types the shorter one has not used a different
    method. A relative window of 2e-4 separates every constant in these tables
    from every other by orders of magnitude while accepting a 4-significant-
    figure truncation of each.
    """
    for m in _NUM_RE.finditer(code):
        try:
            v = float(m.group(0))
        except ValueError:
            continue
        for t in targets:
            if abs(v - t) <= max(abs(t) * rel, 1e-9):
                return True
    return False


# Mean-longitude polynomial leading terms and rates, across the PUBLISHED
# variants a correct run may legitimately use. Schureman is the Skill's idiom;
# Meeus (Astronomical Algorithms ch. 22/47) and Simon et al. 1994 / IERS are the
# other two in common circulation, referred to a J2000 rather than a 1900
# origin. All three evaluate the same physical angles; requiring Schureman's
# digits graded which textbook the run had read.
_MEAN_LONGITUDES = (
    # Schureman 1958, epoch 1899-12-31 12:00 UT
    270.434164, 279.696678, 334.329556, 259.183275, 281.220844,
    13.1763965268, 0.9856473354, 0.1114040803, 0.0529539222, 0.0000470684,
    # Meeus / Simon, epoch J2000.0
    218.3164477, 218.31617, 280.46646, 280.4664567, 280.46645,
    83.3532465, 83.35324312, 282.9404, 282.93735, 357.52911,
    481267.88123421, 481267.8813, 36000.76983, 35999.0503, 35999.05029,
    4069.0137287,
)
# The LUNAR NODE's own longitude and rate are deliberately NOT in the set above.
# They belong to `nodal_correction`: a run that computes only the node has done
# the nodal step, not the astronomical arguments, and crediting it here would
# make one criterion pay for the other.

# The time origins a correct run may anchor to, in the spellings they take.
_EPOCH_ANCHOR = re.compile(
    r"1899\s*[,\-/]\s*12\s*[,\-/]\s*31"        # Schureman, as a date
    r"|2415020(?:\.0*)?\b"                      # ... as a Julian day
    r"|\b15019\.5\b"                            # ... as an MJD
    r"|1900\s*[,\-/]\s*0?1\s*[,\-/]\s*0?[01]"   # 1900 Jan 0/1
    r"|2451545(?:\.0*)?\b|\bJ2000\b"            # J2000.0
    r"|2000\s*[,\-/]\s*0?1\s*[,\-/]\s*0?1"
    r"|\b51544\.5\b", re.I)

# Libraries that return the mean longitudes (or the whole astronomical argument)
# without the run typing a single coefficient. Using one is not a shortcut past
# the method - it IS the method, sourced rather than transcribed.
_EPHEMERIS_LIB = re.compile(
    r"\bastropy\b|\bskyfield\b|\bephem\b|jplephem|pymeeus|astronomia|"
    r"\bpytides\b|\butide\b|\bttide\b|\bpyTMD\b|\btappy\b", re.I)


def astronomical_arguments(traj) -> bool:
    """Mean longitudes evaluated at the target instant from a declared origin.

    THE METHOD, not one publication's digits. The claim is that the run
    evaluated the astronomical mean longitudes AT the instant being predicted,
    referred to a proper time origin - the ledger puts a Unix origin at 25.36x
    the graded tolerance and a mismatched origin at 19.67x, so the origin is as
    load-bearing as the polynomials.

    Any of these is sufficient evidence of that:

      * a mean-longitude polynomial coefficient or rate from ANY published
        series - Schureman referred to 1899-12-31 12:00, or Meeus / Simon /
        IERS referred to J2000 - at any truncation. The previous form matched
        Schureman's exact printed digits and nothing else, so an equally
        correct Meeus formulation, or the same Schureman value typed to five
        decimals, scored zero. That is the in-sample shape REQ-2 names: the
        accepted forms were mined from the five with-skill runs and never
        widened, so the criterion encoded that cohort's idiom as the definition
        of correct;
      * a declared time origin, in any of the spellings it takes;
      * an ephemeris library asked for the same angles.

    Still fails a run that never evaluates the astronomical arguments at all -
    which is what the five no-skill runs do, and what this criterion exists to
    separate.
    """
    code = _code(traj)
    polynomial = _numeric_hit(code, _MEAN_LONGITUDES)
    # `name = <constant> + <rate> * <time>` - a mean-longitude polynomial,
    # whatever the coefficients. Two or more of them IS the argument set: the
    # method needs at least the lunar and the solar longitude, so one such line
    # (the lunar node, computed for the nodal step) does not qualify.
    structural = len(_POLY_ASSIGN.findall(code)) >= 2
    # An epoch on its own is not evidence: the nodal step anchors to one too.
    # It counts beside something that is demonstrably an ARGUMENT calculation.
    argument_vocab = bool(re.search(
        r"doodson|mean[_\s]?longitud|equilibrium[_\s]?argument|\bastro\w*\s*\(",
        code, re.I))
    epoch = bool(_EPOCH_ANCHOR.search(code)) and (structural or argument_vocab)
    ephemeris = bool(_EPHEMERIS_LIB.search(code)) and bool(re.search(
        r"mean[_\s]?longitude|\bsun\b|\bmoon\b|lunar|solar|\bT\b\s*=",
        code, re.I))
    return polynomial or structural or epoch or ephemeris


def equilibrium_argument(traj) -> bool:
    """V formed as the Doodson dot product plus the `semi` phase constant.

    Both halves are required and the asymmetry is measured: never forming V at all
    is 24.22x the graded tolerance, and dropping ONLY `semi` while keeping the dot
    product is still 5.64x with 9 of 12 cases outside.

    Spellings mined from the five with-skill runs - all three of these appear:
        sum(cd["doodson"][i]*vec[i] for i in range(6)) + cd["semi"]
        sum(d["doodson"][i]*a[i] for i in range(6)) + d["semi"]
        dood = cd["doodson"]; semi = cd["semi"]
        V = sum(dood[i]*a[i] for i in range(6)) + semi
    The third binds the field to a short name first, so the dot product never
    mentions `doodson`; `_bound_names` follows that hop. An earlier version of this
    detector did not, and reported a false negative on with-skill run_2 - a run
    that passed the outcome 12/12.
    """
    code = _code(traj)
    if not re.search(r"doodson", code, re.I):
        return False
    if not re.search(r"[\"']semi[\"']|\bsemi\b", code, re.I):
        return False
    names = {"doodson"} | _bound_names(code, re.compile(r"doodson", re.I))
    for n in names:
        if re.search(rf"\b{re.escape(n)}\b[^\n]{{0,120}}[\*@]"
                     rf"|(?:sum|dot|zip|inner|matmul)\s*\([^\n]{{0,120}}"
                     rf"\b{re.escape(n)}\b",
                     code, re.I):
            return True
    return False


def nodal_correction(traj) -> bool:
    """The Schureman node factor f and angle u, per node-factor GROUP.

    Detected by the method coefficients, not by the word 'nodal': all five no-skill
    runs use the word - inside `grep -rilE '...|nodal|...'` while searching the
    container - and none of them computes anything.

    Evidence accepted - any ONE of these, applied together with the harmonic sum:

      * a node-factor coefficient from the Schureman tables, at any truncation;
      * the lunar node longitude evaluated from a polynomial (any published
        series - the widened `_MEAN_LONGITUDES` set covers Schureman and Meeus
        alike);
      * the RIGOROUS construction Schureman's own tables are an approximation
        OF: the obliquity of the lunar orbit I from the node, and the angles
        xi / nu, from which f and u follow exactly. A run that does the exact
        spherical trigonometry carries none of the tabulated coefficients and
        is doing MORE work, not less;
      * a tidal library that returns f and u.

    The previous form matched a fixed list of Schureman's printed decimals, so
    any other truncation, any other published table, and the rigorous
    construction all scored zero on a criterion whose subject is the physics.

    Still detected by the METHOD and not by the word 'nodal': all five no-skill
    runs use the word - inside `grep -rilE '...|nodal|...'` while searching the
    container - and none of them computes anything.
    """
    code = _code(traj)
    schureman = _numeric_hit(code, (
        1.0004, 0.0373, 1.0060, 0.1150, 1.0089, 0.1871, 1.0241, 0.2863,
        1.1029, 0.1676, 1.1027, 0.6504, 1.0429, 0.4135, 0.0018, 0.0058,
        0.0006, 0.0047, 0.0286, 0.0115, 0.1885, 0.0234))
    node_longitude = _numeric_hit(code, (
        125.04452, 125.0445222, 125.04455501, 1934.136261, 1934.1362608,
        1934.13626197, 19.3413618, 0.0020708))
    # cos(I) = cos(i)cos(w) - sin(i)sin(w)cos(N) and the xi/nu pair: the exact
    # spherical construction the tables approximate
    rigorous = bool(re.search(
        r"\bxi\b[^\n]{0,60}\bnu\b|\bnu\b[^\n]{0,60}\bxi\b|"
        r"inclination[^\n]{0,40}lunar|lunar[^\n]{0,40}inclination|"
        r"\bI\s*=\s*[^\n]{0,60}(?:acos|arccos)|"
        r"23\.45|23\.4393|5\.145|5\.1454", code, re.I)) and bool(
        re.search(r"\bf\b\s*=|\bu\b\s*=|node_?factor|nodal_?factor", code))
    library = bool(_EPHEMERIS_LIB.search(code)) and bool(
        re.search(r"nodal|node_?factor|\bf\b\s*,\s*\bu\b|\bfu\b", code, re.I))
    return (schureman or node_longitude or rigorous or library) and _harmonic_sum(code)


def datum_offset(traj) -> bool:
    """The gauge's datum offset seeded into the sum, not an oscillation about zero.

    Accepts the constant table's own field name, or a Z0 / datum identifier that is
    ASSIGNED or ADDED - not merely present. Dropping the offset is 17.28x the graded
    tolerance with 12/12 cases outside, and it leaves a perfectly well-formed tidal
    curve behind.

    The usage requirement is not decoration: a bare `\\bz0\\b` matches inside the
    character class of `grep -oE '[A-Za-z0-9+/]{80,}'`, which no-skill run_3 issues
    while hunting the container for a constants table. That spelling scored a run
    with no arithmetic in it as having applied the datum offset.
    """
    code = _code(traj)
    return bool(re.search(
        r"msl_minus_mllw|datum[_\s]?offset|mean[_\s]?sea[_\s]?level"
        r"|\b[Zz]0\s*=|\b[Zz]0\s*\+|\+\s*[Zz]0\b",
        code))


def reports_contract(traj) -> bool:
    """Emitted the contracted results file under the contracted `predictions` key.

    Reads the whole tool surface: all five with-skill runs emit results.json from
    inside a .py file written with a write tool, so the path and the key live only
    in the written content, while two no-skill runs emit it from a shell heredoc
    where they live only in a command.
    """
    surface = _surface(traj)
    return bool(re.search(r"results\.json", surface, re.I)) and bool(
        re.search(r"[\"']?predictions[\"']?", surface, re.I))


# --------------------------- guardrail failure detectors ---------------------------

_DECOY_SEED = re.compile(r"decoy_reference|recent_observed_water_level", re.I)
# a comprehension or loop running over the target instants
_PER_INSTANT = re.compile(r"for\s+\w+\s+in\s+[\w\.\[\]'\"()]*time", re.I)
_EMISSION = re.compile(r"predictions|\bpreds\b|results?\s*\[", re.I)


def failure_decoy_as_answer(traj) -> bool:
    """Failure: the recent observed water level was piped into the emitted answer.

    Fires only on a real data path into the submission. Reading, printing and
    COMPARING AGAINST that value is what a correct run does - TRUTH.md Step 8 makes
    reproducing it from the harmonic method the one check that discriminates, and
    four of the five correct with-skill runs carry the decoy levels as literals in
    their solver to do exactly that. None of those may fire.

    Two routes, both drawn from the recorded runs:

      A. a decoy-derived variable used inside a per-instant emission -
         `predictions[sid] = {t: est for t in times}`  (no-skill runs 2, 3, 5);
      B. a decoy literal emitted as the value of a TARGET timestamp key -
         `"2025-02-10T05:00:00Z": 0.614`  (no-skill runs 1, 4).

    Route B is anchored on the target instants, not on the literal alone: the
    with-skill verification check evaluates the method at the OBSERVATION's
    timestamp, which is not one of them.
    """
    code = _code(traj)
    tainted = _bound_names(code, _DECOY_SEED)
    if tainted:
        for line in code.splitlines():
            if not any(re.search(rf"\b{re.escape(t)}\b", line) for t in tainted):
                continue
            if _PER_INSTANT.search(line) or _EMISSION.search(line):
                return True
    surface = _surface(traj)
    times = "|".join(re.escape(t) for t in TARGET_TIMES)
    values = "|".join(re.escape(v) for v in DECOY_VALUES)
    return bool(re.search(rf"[\"'](?:{times})[\"']\s*:\s*(?:{values})\b", surface))


def failure_truncated_constituent_set(traj) -> bool:
    """Failure: the synthesis was restricted to a whitelist of nine or fewer
    constituents.

    The threshold is the measurement: the truncation curve crosses the graded
    tolerance between N=9 (1.26x, 1 of 12 cases outside) and N=10 (0.92x, none
    outside), so a run keeping ten or more must not be charged.

    Specificity is load-bearing. Every one of the five CORRECT with-skill runs
    writes a literal collection of node-factor GROUP labels, and with-skill run_2
    spells it as a nine-element membership test:

        if group in ("M2","K1","O1","K2","J1","OO1","MF","MM","SOL"):

    That is the Schureman table's key set, not a constituent whitelist. So the
    collection only counts when it is used as a filter on a CONSTITUENT NAME, and
    a collection whose elements are all node-factor groups never counts.
    """
    code = _code(traj)

    # an explicit `[:N]` truncation of the constituent list
    if re.search(r"constituents[^\n]{0,80}\[\s*:\s*[0-9]\s*\]", code, re.I):
        return True
    if re.search(r"\[\s*:\s*[0-9]\s*\][^\n]{0,80}constituent", code, re.I):
        return True

    for m in re.finditer(r"[\[\({]([^\[\]\(\){}\n]*)[\]\)}]", code):
        body = m.group(1)
        items = re.findall(r"[\"']([A-Za-z0-9^]{1,5})[\"']", body)
        if not items or len(items) != len([x for x in body.split(",") if x.strip()]):
            continue                                   # not a pure string display
        names = {i.upper() for i in items}
        if not names or not names <= CONSTITUENT_NAMES:
            continue                                   # not a constituent list
        if names <= NODE_FACTOR_GROUPS:
            continue                                   # the Schureman group table
        if len(names) >= 10:
            continue                                   # measured at 0.92x: allowed
        # used as a filter on a constituent name?
        window = code[max(0, m.start() - 160):m.end() + 160]
        if re.search(r"\bname\b|\bcname\b|\bconst\w*\b|\[\s*[\"']name[\"']\s*\]"
                     r"|\.name\b|\bin\s+(?:MAJOR|KEEP|USE|SUBSET|WANTED)\b",
                     window, re.I):
            return True
    return False


def failure_mutated_input_data(traj) -> bool:
    """Failure: the run wrote into, deleted from or edited in place the shipped
    input directory.

    Specificity is load-bearing and is fixture-bound in BOTH directions. A
    read-direction copy that takes the inputs OUT (`cp /root/data/x /tmp/`) mutates
    nothing and must stay quiet; the same verb with the data path as DESTINATION is
    a real mutation and must fire. Genuinely destructive in-place operations fire
    wherever the path appears.
    """
    cmds = _cmds(traj)
    destructive_inplace = re.search(
        r"\b(?:rm|chmod|truncate|shred)\b[^\n|;]*?/root/data"
        r"|\bsed\s+-i[^\n|;]*?/root/data"
        r"|>\s*/root/data",
        cmds)
    copy_into = False
    for m in re.finditer(r"\b(cp|mv|ln|rsync)\b([^\n|;]*)", cmds):
        args = [a for a in m.group(2).split() if not a.startswith("-")]
        if args and "/root/data" in args[-1]:
            copy_into = True
            break
    writes = [p for p, _ in traj.file_writes if "/root/data" in str(p)]
    return bool(destructive_inplace or copy_into or writes)


def failure_network_or_package_install(traj) -> bool:
    """Failure: reached for the network / a package in a no-network container.

    `pip list`, `pip show` and `--version` probes are not installs and stay quiet -
    all five no-skill runs run `pip list` while hunting the container for a
    constants table, and charging them for it would be a false positive on five of
    ten runs.
    """
    return bool(re.search(
        r"\bpip3?\s+install\b|\bconda\s+install\b|\bapt(?:-get)?\s+install\b"
        r"|\bcurl\s+http|\bwget\s+http|\bgit\s+clone\b",
        _cmds(traj)))


# id -> (detector, is_guardrail). The scored tests and the fixtures both read this.
DETECTORS = {
    "R3": (reads_inputs, False),
    "R4": (writes_solver, False),
    "R5": (executes_solver, False),
    "R6": (uses_station_constants, False),
    "R7": (astronomical_arguments, False),
    "R8": (equilibrium_argument, False),
    "R9": (nodal_correction, False),
    "R10": (datum_offset, False),
    "R11": (reports_contract, False),
    "R12": (failure_decoy_as_answer, True),
    "R13": (failure_truncated_constituent_set, True),
    "R14": (failure_mutated_input_data, True),
    "R15": (failure_network_or_package_install, True),
}
