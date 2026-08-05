"""All pytest for this task: outcome, process, and grader self-checks.

Consolidated from the v1 layout, which split them across
`tests/test_output.py` (outcome, in-container) and
the `process`-marked tests in this same file (post-hoc), with
`checks.py`, `trajectory.py` and `conftest.py` beside them.

THE TWO CONTEXTS. Outcome and self-check tests run INSIDE the container at
grade time and read the answer artifact. Process tests run OUTSIDE, post-hoc,
over a recorded trajectory. One file serves both through markers plus
environment-driven fixtures:

    pytest test_output.py -m "outcome or selfcheck"   # in-container, by test.sh
    pytest test_output.py -m process                  # post-hoc, by the harness

NAMING IS THE CONTRACT.
    test_score_*     scored by test.sh; these ARE the score
    test_o_* / test_d_*   one per rubric criterion id, joined by name
    test_selfcheck_*  unscored grader audit; a failure trips the kill-switch

There is no conftest.py: the `traj` fixture is defined here and `ERZA_RUN_DIR`
replaces the old `--run-dir` option, so the bundle carries no pytest plugin.

GUARDRAIL CONVENTION, unchanged: a guardrail test PASSES when the bad thing did
NOT happen. The scorer reads a FAILING guardrail as "the failure mode occurred".
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_TESTS = os.path.dirname(os.path.abspath(__file__))
_LIB = _TESTS
if os.path.isdir(_LIB) and _LIB not in sys.path:
    sys.path.insert(0, _LIB)


# ==========================================================================
# THE `traj` FIXTURE
# ==========================================================================

@pytest.fixture(scope="session")
def traj():
    """The recorded run, for the process channel.

    ERZA_RUN_DIR replaces the old --run-dir option, which is the only
    thing that required a conftest.py. A process run without it is a
    selection error, not a result, so this skips rather than failing:
    test.sh never selects the process channel.
    """
    run_dir = os.environ.get("ERZA_RUN_DIR", "")
    if not run_dir:
        pytest.skip("ERZA_RUN_DIR unset: process channel not selected")
    if not os.path.isdir(run_dir):
        pytest.fail(f"run dir does not exist: {run_dir}")
    import trajectory as _traj
    return _traj.load(run_dir)


# ==========================================================================
# PROCESS CHANNEL
# ==========================================================================

"""Deterministic channel: the process questions a machine can decide.

Each test is one criterion from `rubrics.json`; the test name is `test_` + the
criterion id. These read the *trajectory* - the code the agent authored and the
commands it ran - not just the final artifact.

GUARDRAIL CONVENTION (differs from WildClawBench, deliberately):
a guardrail test PASSES when the bad thing did NOT happen. The scorer treats a
FAILING guardrail as "the failure mode occurred" and subtracts. WCB's shipped
`_compute_reward` subtracts on a *passing* negative test while its own
NOMENCLATURE.md says the penalty applies when the guardrail "FIRED" - the two
disagree. We use the reading that matches how the assertion actually reads.
"""

import ast
import re

import pytest


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
    a literal is ordinary practice, so the bug fell hardest on exactly the
    route the shipped reference data invites.

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


@pytest.fixture(scope="session")
def code(traj):
    return _strip_comments(traj.agent_code)


@pytest.fixture(scope="session")
def everything(traj):
    """Code AND prose, DELIBERATELY UNSTRIPPED.

    Only narration-tier criteria read this - `R7` asks whether the
    run identified the quantity the standard calls three different things, not
    whether it computed anything. Narration lives in comments as legitimately as
    in prose, so stripping here would reject the criterion's own declared
    alternative forms (measured: 6 of 6) and pin the route. Criteria that grade
    BEHAVIOUR read `code`, which is stripped.
    """
    return traj.agent_code + "\n" + traj.agent_prose


# --------------------------------------------------------------------------- #
# positive criteria                                                            #
# --------------------------------------------------------------------------- #

@pytest.mark.process
def test_R3(traj):
    """The agent went to the shipped header rather than only the prose task."""
    blob = traj.agent_code + " " + " ".join(traj.commands)
    assert "image.hdr" in blob, "never referenced /root/data/image.hdr"


@pytest.mark.process
def test_R4(traj):
    """The write must look like SOURCE. A run that hand-writes results.json with
    asserted coordinates is the exact behaviour this criterion exists to catch,
    and an earlier version counted any file write - including that one."""
    src_writes = [
        (p, c) for p, c in traj.file_writes
        if "results.json" not in p
        and (p.endswith(".py") or re.search(r"^\s*(import|def)\s", c, re.M))
    ]
    heredoc = any("<<" in c and "python" in c.lower() for c in traj.commands)
    assert src_writes or heredoc, "no solver source authored (file write or heredoc)"


@pytest.mark.process
def test_R5(traj):
    """Execution must be tied to running code, not any `python` token - an
    earlier version passed on `python3 --version` alone."""
    joined = "\n".join(traj.commands)
    ran = re.search(r"\bpython3?\s+(\S+\.py\b|-c\s|-\s|<<)", joined)
    heredoc = any("<<" in c and "python" in c.lower() for c in traj.commands)
    assert ran or heredoc, "solver was never executed"


# --------------------------------------------------------------------------- #
# The routes the weight-5 gate blesses. REQ-2 (VERIFIER_PIPELINE Stage 4, "A    #
# criterion may not narrow the route to the reward"): whenever a criterion      #
# ENUMERATES accepted forms, every sibling criterion must accept each of those  #
# forms too. The gate below accepts "a tangent-plane or vector construction     #
# whose basis already encodes the orientation" - and such a construction never  #
# contains an `atan2(x, -y)`, because it never forms the native longitude at    #
# all. Two siblings used to require that literal, so the gate blessed a route   #
# its neighbours auto-failed. They are defined once, here, and consulted by     #
# every criterion that would otherwise demand the spelling.                     #
# --------------------------------------------------------------------------- #

def _tangent_plane_route(code: str):
    """Gnomonic deprojection via the angular distance rho: an east-north
    tangent-plane basis carries phi_p = 180 implicitly, and the standard
    `dec = asin(cos c sin dec0 + y sin c cos dec0 / rho)` /
    `ra = ra0 + atan2(x sin c, rho cos dec0 cos c - y sin dec0 sin c)` pair
    never writes a native longitude down."""
    return re.search(r"\brho\b", code) and re.search(
        r"\barctan\w*\(\s*rho|\bc\s*=\s*(np\.)?arctan|\bsin\w*\(\s*c\b|"
        r"\bcos\w*\(\s*c\b", code)


def _vector_basis_route(code: str):
    """Direction-cosine route: build the pixel offset in an east-north basis,
    rotate the unit vector, read the celestial angles off the result. The
    orientation lives in the basis vectors, so there is no phi to order."""
    return re.search(r"east|north", code, re.I) and re.search(
        r"cross|dot|\bnp\.array\(\[|matmul|\bR\s*@|@\s*\bvec", code)


def _orientation_carrying_construction(code: str):
    return bool(_tangent_plane_route(code) or _vector_basis_route(code))


@pytest.mark.process
def test_R6(code):
    """THE fork. phi_p must enter the native->celestial rotation.

    Accepts every equivalent spelling seen in the measured runs: a named
    phi_p/lonpole variable, a literal 180-degree or pi-radian offset, a `dphi`
    intermediate, or a tangent-plane / vector construction whose basis already
    encodes the orientation.
    """
    # NOTE: an earlier version accepted a bare `dphi` identifier as evidence.
    # That was a false negative in the suite's most important test - a run that
    # merely *names* a variable dphi while computing `dphi = phi` (i.e. with
    # phi_p dropped) passed. A synthetic no_lonpole fixture caught it. The
    # subtraction itself must now appear; `dphi` only counts when it is bound
    # to one.
    explicit = re.search(
        r"(phi|lon)\w*\s*-\s*(phi_?p\b|lonpole|180(\.\d+)?\b|np\.pi\b|math\.pi\b|\bpi\b)"
        r"|\bd_?phi\s*=\s*[^\n=]*\bphi\w*\s*-\s*\S"
        r"|phi\s*\+\s*(180(\.\d+)?|np\.pi|math\.pi)\b",
        code,
        re.I,
    )
    tangent_plane = _tangent_plane_route(code)
    vector_basis = _vector_basis_route(code)
    assert explicit or tangent_plane or vector_basis, (
        "native->celestial rotation has no phi_p term and no equivalent "
        "orientation-carrying construction: the LONPOLE default was dropped"
    )


@pytest.mark.process
def test_R7(everything):
    """The agent names the quantity, in any of the names the standard gives it.

    FITS WCS Paper II calls one thing three ways: the keyword `LONPOLE`, the
    symbol `phi_p` (its own notation for the same quantity), and the phrase
    "native longitude of the celestial pole", which is what the keyword
    abbreviates. A run that writes `phi_p = 180 for TAN (Paper II)` has named
    it as precisely as one that writes `LONPOLE`; failing it graded which of
    the standard's own synonyms the run happened to pick, not whether the
    quantity was identified. A recorded reward-1.0 run was failed on exactly
    that.

    A bare `phi_p` variable is NOT enough on its own - a solver can carry that
    name having copied it without knowing what it is, which is the failure mode
    this weight-1 preference records. It counts when the run also points at the
    convention the symbol comes from (the standard, the projection, or the fact
    that 180 is its DEFAULT), so the run has demonstrably identified the
    quantity and not merely inherited a variable name.
    """
    named_outright = re.search(r"lonpole", everything, re.I)
    standard_phrase = re.search(
        r"native\s+longitude\s+of\s+the\s+(?:celestial|north)\s+pole|"
        r"native\s+longitude[^\n]{0,40}\bpole\b", everything, re.I)
    symbol_with_provenance = re.search(
        r"(?:\bphi_?p\b|φ_?p|ϕ_?p)[^\n]{0,80}"
        r"(?:paper\s*ii|\bwcs\b|\bfits\b|\bTAN\b|default|convention|standard)|"
        r"(?:paper\s*ii|\bwcs\b|\bfits\b|\bTAN\b|default|convention|standard)"
        r"[^\n]{0,80}(?:\bphi_?p\b|φ_?p|ϕ_?p)",
        everything, re.I)
    assert named_outright or standard_phrase or symbol_with_provenance, (
        "LONPOLE never named, and its symbol phi_p never tied to the "
        "convention it comes from")


@pytest.mark.process
def test_R8(code):
    """The native longitude carries the WCS argument order, however it is built.

    `phi = atan2(x, -y)` is the spelling WCS Paper II prints, but it is not the
    only correct one. Its exact algebraic equals is `atan2(y, x) + 90 deg`
    (equivalently `+ pi/2`), because (x, -y) is (y, x) turned a quarter turn.
    And a run on the tangent-plane or vector-basis route - the route the
    weight-5 gate `R6` EXPLICITLY blesses - never forms
    a native longitude at all: the orientation lives in the east-north basis.
    Requiring the literal made this criterion auto-fail a route its own gate
    was written to reward.

    Known limit, unchanged: the shape is matched anywhere in the source, not
    provably in the phi computation. It stays a spelling hypothesis, which is
    why its weight is 3 and not 5.
    """
    literal = re.search(
        r"a(?:rc)?tan2\(\s*[-\w.\[\]()* ]+\s*,\s*-\s*[\w.]+", code)
    # the quarter turn may sit outside a degrees()/rad2deg() wrapper, so allow
    # the closing parens of any conversion between the atan2 and the offset
    quarter_turn = re.search(
        r"a(?:rc)?tan2\([^)\n]*\)[\s)]*\+\s*(?:90(?:\.\d+)?\b|"
        r"(?:np\.|math\.)?pi\s*/\s*2|0\.5\s*\*\s*(?:np\.|math\.)?pi)",
        code, re.I)
    assert literal or quarter_turn or _orientation_carrying_construction(code), (
        "native longitude is neither of the form atan2(x, -y) nor an "
        "equivalent quarter-turn form, and no orientation-carrying "
        "tangent-plane/vector construction is present")


@pytest.mark.process
def test_R9(code):
    """Native latitude in a form that stays finite as R -> 0.

    The two-argument `atan2(180/pi, R)` is the WCS spelling. The complement
    form `pi/2 - arctan(R)` (in radians) or `90 - degrees(arctan(R))` is
    exactly equal and finite everywhere by construction, so it is the same
    method with the singularity removed a different way. And the tangent-plane
    and vector routes the weight-5 gate blesses never form a native latitude at
    all: they read the declination straight off the rotated unit vector.

    Deliberately NOT accepted: the one-argument `arctan(1/R)` (or
    `arctan(180/(pi*R))`), which is what this criterion exists to catch - it
    divides by R and is undefined at the reference point. A bare `arcsin`/
    `arccos` is not accepted either: every solver on this task has one
    somewhere, so accepting it would accept everything.
    """
    two_arg = re.search(
        r"a(?:rc)?tan2\(\s*(180(\.\d+)?\s*/\s*(np\.|math\.)?pi"
        r"|1(\.0)?"
        r"|r2d|rad2deg|RAD2DEG|_?DEG2?|todeg)\s*,",
        code, re.I)
    complement = re.search(
        r"(?:np\.|math\.)?pi\s*/\s*2(?:\.0)?\s*-\s*(?:np\.|math\.)?a(?:rc)?tan\s*\(|"
        r"90(?:\.\d+)?\s*-\s*(?:(?:np|math)\.(?:degrees|rad2deg)\s*\(\s*)?"
        r"(?:np\.|math\.)?a(?:rc)?tan\s*\(", code, re.I)
    assert two_arg or complement or _orientation_carrying_construction(code), (
        "native latitude not written in a form that stays finite as R -> 0")


@pytest.mark.process
def test_R10(code):
    """Right ascension delivered inside [0, 360).

    A modulo is one spelling of a wrap, not the definition of one. `np.mod`,
    `math.fmod` with a negative fix-up, `x + 360 if x < 0 else x`,
    `np.where(ra < 0, ra + 360, ra)`, a radian wrap `% (2*pi)` applied before
    conversion, and astropy's `Angle(...).wrap_at(360*u.deg)` or a `SkyCoord`
    whose `.ra` is normalised by construction all deliver the same interval.
    Requiring the literal `% 360` graded the idiom, not the interval.
    """
    assert re.search(
        r"%\s*360|"                                    # the literal
        r"%\s*\(?\s*2\s*\*\s*(?:np\.|math\.)?pi|"      # radian wrap
        r"(?:np|math)\.(?:mod|fmod|remainder)\s*\(|"    # library modulo
        r"\+\s*360(?:\.\d+)?\b[^\n]{0,40}\bif\b|"       # x + 360 if x < 0
        # the guarded fix-up, whether inline or spread over an if-block
        r"\bif\b[^\n]{0,60}<\s*0[\s\S]{0,80}\+\s*360|"
        r"np\.where\([^\n]{0,60}\+\s*360|"              # vectorised fix-up
        r"wrap_at|\bSkyCoord\b|\bAngle\s*\(",           # astropy normalises
        code, re.I), "RA never wrapped into [0, 360)"


@pytest.mark.process
def test_R11(code):
    """No rounding applied to the *emitted* coordinates.

    Scoped to expressions that name a coordinate. Rounding inside a diagnostic
    print of a residual is not an output-precision defect, and an earlier
    version of this test wrongly failed a passing run for exactly that.
    """
    bad = re.search(
        r"round\s*\(\s*[^)]*\b(ra|dec|alpha|delta)\w*\b[^)]*,\s*[0-5]\s*\)"
        r"|\b(ra|dec)\w*\s*[:=]\s*[^\n]*:\.[0-5]f"
        r"|%\.[0-5]f[^\n]*%\s*\(?\s*(ra|dec)",
        code,
        re.I,
    )
    assert not bad, f"coordinates truncated before serialisation: {bad.group(0)!r}"


@pytest.mark.process
def test_R12(traj):
    """Judge what the run EMITTED, not what it saw. An earlier version searched
    the whole transcript, so a run that merely `cat sources.csv` passed even if
    its own output dropped ids - tool results made the test unfalsifiable."""
    res_writes = "\n".join(c for p, c in traj.file_writes if "results.json" in p)
    if res_writes and all(f"S{i:02d}" in res_writes for i in range(1, 17)):
        return  # the emitted file itself carries every id
    # otherwise judge the authored code. (An incomplete literal write is NOT
    # proof of missing ids - file_writes cannot distinguish a full write from
    # a partial edit - so the code check decides.)
    blob = traj.agent_code
    missing = [f"S{i:02d}" for i in range(1, 17) if f"S{i:02d}" not in blob]
    # ids may be produced by iteration rather than enumeration; accept any
    # programmatic read of the catalogue (DictReader, csv.reader, or a plain
    # open(...sources.csv) with manual splitting - two correct runs use the
    # latter). `cat sources.csv` in a shell command is NOT iteration evidence.
    iterated = re.search(
        r"source_id|DictReader|csv\.reader|open\([^)\n]*sources\.csv", blob
    )
    assert not missing or iterated, f"ids absent and not iterated: {missing}"


# --------------------------------------------------------------------------- #
# guardrails - these PASS when the failure mode did NOT occur                   #
# --------------------------------------------------------------------------- #

def _crpix_literals():
    """The shipped header's CRPIX values, as they would be spelled in source.
    Reading the *input* file grader-side is not answer leakage - CRPIX is given
    to the agent; it lets the rebase guardrail catch transcribed-constant runs."""
    import os

    hdr = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "environment", "data", "image.hdr",
    )
    vals = []
    with open(hdr) as fh:
        for line in fh:
            if line.split("=")[0].strip() in ("CRPIX1", "CRPIX2"):
                v = float(line.split("=", 1)[1].split("/")[0])
                vals.append(re.escape(f"{v:g}"))
    return vals


@pytest.mark.process
def test_R13(code):
    # identifier form: `(px - 1) - crpix...`. Known limit: a run that rebases
    # BOTH sides consistently (correct) would also match; none of 32 runs did.
    pats = [r"\(\s*\w+\s*-\s*1(\.0)?\s*\)\s*-\s*crpix",
            r"\w+\s*-\s*1(\.0)?\s*-\s*crpix"]
    # transcribed-constant form: `(px - 1) - 512.5` - an earlier version only
    # matched the crpix identifier, so transcription (which the rubric permits)
    # put the failure out of the guardrail's reach
    for lit in _crpix_literals():
        pats.append(r"\(\s*\w+\s*-\s*1(\.0)?\s*\)\s*-\s*" + lit)
        pats.append(r"\w+\s*-\s*1(\.0)?\s*-\s*" + lit)
    hit = re.search("|".join(pats), code, re.I)
    assert not hit, f"pixel rebased to 0 against a 1-based CRPIX: {hit.group(0)!r}"


@pytest.mark.process
def test_R14(traj):
    joined = "\n".join(traj.commands)
    # curl must tolerate flags between the command and the URL (`curl -sO http…`)
    hit = re.search(
        r"\bpip3?\s+install\b|\bapt(-get)?\s+install\b"
        r"|\bcurl\b[^\n|;]*https?://|\bwget\b",
        joined,
    )
    assert not hit, f"network/package attempt in a no-network container: {hit.group(0)!r}"


@pytest.mark.process
def test_R15(traj):
    """Fires only on commands that can CHANGE /root/data. `cp` is directional:
    copying data OUT to work on is a read and must not fire (an earlier version
    fired on any `cp … /root/data`, punishing a harmless read)."""
    dangerous = []
    for c in traj.commands:
        for line in re.split(r"[\n;|&]+", c):
            if re.search(
                r"\b(rm|mv|truncate|chmod|ln\s+-s)\s+[^\n]*?/root/data", line
            ) or re.search(r"\bsed\s+[^\n]*-i[^\n]*?/root/data", line) or re.search(
                r">\s*/root/data/", line
            ):
                dangerous.append(line.strip())
                continue
            m = re.match(r"\s*cp\s+(.*)", line)
            if m:
                args = [a for a in m.group(1).split() if not a.startswith("-")]
                if args and args[-1].startswith("/root/data"):
                    dangerous.append(line.strip())
    writes = [p for p, _ in traj.file_writes if p.startswith("/root/data")]
    assert not dangerous and not writes, (
        f"input data mutated: {dangerous or writes}"
    )


_ITERATION = re.compile(
    r"fsolve|scipy\.optimize|newton_?raphson|brentq|while\s+.*(tol|converg|eps)",
    re.I)
# vocabulary of a CHECK rather than of the chain itself
_VERIFICATION_CONTEXT = re.compile(
    r"verif\w*|\bcheck\w*|validat\w*|round.?trip|invert|inverse|sanity|"
    r"cross.?check|residual|assert|\btest\w*|confirm|independent", re.I)


@pytest.mark.process
def test_R16(code):
    """GUARDRAIL: the closed-form chain was solved numerically.

    Scoped to the chain. `R22` (weight 3) REWARDS
    a run that confirms its answer by a second, independent construction, and
    the natural second construction here is a forward round-trip driven to
    convergence. Firing on any `scipy.optimize` or `while ... tol` anywhere in
    the source made the two criteria contradict each other: a run could earn
    the rubric and trip the guardrail with the same lines. The guardrail now
    ignores an iteration whose own line, or whose enclosing statement block,
    reads as a check - and still fires on iteration in the derivation itself,
    which is the failure mode it exists to catch.
    """
    lines = code.splitlines()
    for i, line in enumerate(lines):
        hit = _ITERATION.search(line)
        if not hit:
            continue
        window = "\n".join(lines[max(0, i - 6):i + 4])
        if _VERIFICATION_CONTEXT.search(window):
            continue
        # a bare import is not an iteration either
        if re.match(r"\s*(?:from|import)\s", line):
            continue
        raise AssertionError(
            f"numerical iteration in a closed-form chain: {hit.group(0)!r}")


# =========================================================================== #
# OUTCOME CHANNEL (o_*) - VERIFIER_PIPELINE Stage 4, "the outcome channel:     #
# probe re-execution grades the answer itself".                               #
#                                                                             #
# These two tests make the process instrument STANDALONE: they re-derive the   #
# run's final answer from the run's OWN trajectory instead of trusting a       #
# reward file that some harness may or may not have written.                   #
#                                                                             #
#   1. reconstruct every file the run authored - full writes first, then its   #
#      EDITS REPLAYED IN ORDER (a write-then-edit sequence must resolve to the #
#      edited file; the grep views' draft-superset is deliberately wrong here) #
#   2. pick the solver: the authored python that names the output artifact     #
#   3. rewrite its hardcoded /root/... paths into a temp sandbox holding the   #
#      SHIPPED inputs, so the probe can never touch the real bundle           #
#   4. execute it (interpreter fallback: the grading venv may lack the run's   #
#      imports), newest candidate first                                        #
#   5. fall back to the literal answer file the run wrote when no solver runs  #
#   6. grade the produced answer against the frozen truth                      #
#                                                                             #
# Nothing here reads score.md or the outcome verifier's                        #
# report. The route that decided each run (probe / literal / none) is put in   #
# the assertion message so it is recorded per run.                             #
# =========================================================================== #

import json as _json
import math as _math
import os as _os
import re as _re
import shutil as _shutil
import subprocess as _subprocess
import sys as _sys
import tempfile as _tempfile
import time as _time

import pytest  # noqa: F401  (already imported by most channels; harmless twice)

# Bounds on the probe. Grading must not hang: a reconstructed solver may block on
# stdin, spin, or simply be slow, and the instrument tries several candidates.
_PROBE_TIMEOUT_S = 30          # per execution attempt
_PROBE_BUDGET_S = 60           # total across EVERY attempt and candidate, per run
_PROBE_MAX_CANDIDATES = 4
_O_DEADLINE = [0.0]            # set once per run in _o_answer


def _o_interpreters():
    """Distinct interpreters to try, in order.

    The grading venv may lack the run's imports (numpy, obspy), so a second
    interpreter is a real fallback and not belt-and-braces - it is the limit that a
    run found, not one that was foreseen. Deduplicated by resolved path so the same
    binary is never run twice.
    """
    import shutil as _sh
    out, seen = [], set()
    for cand in (_sys.executable, "python3", "python"):
        if not cand:
            continue
        real = _sh.which(cand) or cand
        try:
            real = _os.path.realpath(real)
        except OSError:
            pass
        if real in seen:
            continue
        seen.add(real)
        out.append(cand)
    return out


_O_IMAGE = []                  # docker availability, probed once per process


def _o_box_root():
    """Where the sandbox is created: `/tmp` when usable, else the default.

    The box has to be bind-mountable into the task image or the docker engine
    cannot run at all, and Docker Desktop shares only a fixed set of host
    directories with its VM. `/tmp` is in that set on every default install;
    the platform temp dir is not guaranteed to be (on macOS it is
    `/var/folders/...`). Falling back to the default keeps hosts without `/tmp`
    working exactly as before.
    """
    if _os.path.isdir("/tmp") and _os.access("/tmp", _os.W_OK):
        return "/tmp"
    return None


def _o_docker_image():
    """This bundle's own task image, if docker can run it, else None.

    The grading host is not the environment the run executed in, and the
    difference is not cosmetic: `numpy.trapz` is gone from current numpy, the
    task's pinned dependency set is absent, and `/root` - where every recorded
    run worked - does not even exist. Re-executing inside the image the task
    ships measures the RUN rather than the grader's site-packages; without it
    the probe abstained on correct runs and capped them through the outcome
    gate. Probed ONCE: `docker image inspect` per candidate would cost more
    than the executions it guards. When docker or the image is unavailable the
    host interpreters are used exactly as before, so a docker-less grader is
    unaffected.
    """
    if not _O_IMAGE:
        image = "erza-ta-%s:latest" % _os.path.basename(_BUNDLE)[:8]
        try:
            ok = _subprocess.run(
                ["docker", "image", "inspect", image], timeout=20,
                stdin=_subprocess.DEVNULL, stdout=_subprocess.DEVNULL,
                stderr=_subprocess.DEVNULL).returncode == 0
        except (OSError, _subprocess.TimeoutExpired):
            ok = False
        _O_IMAGE.append(image if ok else None)
    return _O_IMAGE[0]


def _o_docker_kill(name):
    """Best-effort removal of a probe container. Killing the `docker run`
    client does NOT stop the container, so a timed-out probe would otherwise
    leave a solver running on the grading host forever."""
    try:
        _subprocess.run(["docker", "rm", "-f", name], timeout=20,
                        stdin=_subprocess.DEVNULL, stdout=_subprocess.DEVNULL,
                        stderr=_subprocess.DEVNULL)
    except (OSError, _subprocess.TimeoutExpired):
        pass


def _o_engines(box, work, script):
    """Ways to execute one reconstructed solver: (label, argv, cwd, container).

    The task image comes first, because it is the only engine that reproduces
    the environment the run actually had; the host interpreters follow
    unchanged, so nothing regresses where docker is absent.

    The box is bind-mounted TWICE. At its own absolute path, so every path the
    rewrite pointed into the sandbox resolves identically in-container. And at
    `/root`, because a solver that takes its destination from the task's own
    `output_path` field writes the literal `/root/results.json` that no rewrite
    of the SOURCE can reach: mounting the box there keeps that write inside the
    sandbox and findable. Without it the container exits 0 having written into
    its own ephemeral layer, which the probe reads as "the solver ran and
    produced nothing" - grading a correct run 0 instead of abstaining, which is
    worse than the abstention this change exists to remove.
    """
    out = []
    image = _o_docker_image()
    if image:
        container = "o_probe_%d_%s" % (_os.getpid(), _os.path.basename(box))
        out.append((
            "docker %s" % image,
            ["docker", "run", "--rm", "--network", "none", "--name", container,
             "-v", "%s:%s" % (box, box), "-v", "%s:/root" % box,
             "-w", work, image, "python3", script],
            box, container))
    for interp in _o_interpreters():
        out.append(("host %s" % interp, [interp, script], work, ""))
    return out

# <bundle>/tests/test_output.py -> <bundle>
_BUNDLE = _os.path.normpath(
    _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
_SHIPPED_DATA = _os.path.join(_BUNDLE, "environment", "data")
_FROZEN_TRUTH = _os.path.join(_BUNDLE, "tests", "expected_values.json")


def _o_num(v):
    """float(v) if v is a real finite number, else None."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    v = float(v)
    return v if _math.isfinite(v) else None


def _o_dig(obj, *keys):
    for k in keys:
        if not isinstance(obj, dict) or k not in obj:
            return None
        obj = obj[k]
    return obj


def _o_first(node, spellings):
    if not isinstance(node, dict):
        return None
    for s in spellings:
        if s in node:
            return node[s]
    return None


def _o_authored_files(traj):
    """path -> final content, with write/edit tool calls replayed IN ORDER.

    A file written and then edited must resolve to the EDITED text. Taking the
    union of every write (what the grep views do) reconstructs a draft superset
    that does not correspond to any file that ever existed on disk, and real
    solvers reconstructed that way crash.
    """
    files, order = {}, []

    def _put(path, content):
        files[path] = content
        if path not in order:
            order.append(path)

    for t in traj.turns:
        if t.type != "tool_use":
            continue
        inp = t.tool_input or {}
        if not isinstance(inp, dict):
            continue
        path = inp.get("file_path") or inp.get("path") or ""
        if path:
            path = str(path)
            body = inp.get("content", inp.get("file_text"))
            if body is not None:
                _put(path, str(body))
                continue
            new = inp.get("new_string", inp.get("new_str"))
            if new is not None:
                old = str(inp.get("old_string", inp.get("old_str") or ""))
                new = str(new)
                cur = files.get(path)
                if cur is None:
                    _put(path, new)          # edit with no recorded write
                elif old and old in cur:
                    _put(path, cur.replace(old, new, 1))
                elif old == "":
                    _put(path, cur + new)
                # an edit whose anchor is absent is unresolvable: leave the file
                continue

    # heredocs: `cat > f.py <<'EOF' ... EOF` and inline `python3 <<'PY' ... PY`,
    # plus shell in-place edits, replayed in command order.
    for i, cmd in enumerate(traj.commands):
        # `cp <shipped> <dst>` is a STAGING read: the run places a file the
        # environment ships (data/ or a skill's tree) where its solver expects
        # it. Replaying it here gives the reconstructed solver the same bytes -
        # note this feeds ONLY the probe's reconstruction, never the graded
        # `file_writes` view, so provenance guardrails still see a read, not an
        # authorship. Sources already reconstructed (an authored file copied to
        # a second path) are honoured too, in command order.
        for m in _re.finditer(
                r"\bcp\s+(?:-[a-zA-Z]+\s+)*([^\s;|&]+)\s+([^\s;|&]+)", cmd):
            src, dst = m.group(1), m.group(2)
            content = files.get(src)
            if content is None:
                for pref, base in (("/root/data/", ("environment", "data")),
                                   ("/root/.claude/skills/", ("environment", "skills")),
                                   ("/home/agent/.claude/skills/", ("environment", "skills")),
                                   ("~/.claude/skills/", ("environment", "skills"))):
                    if src.startswith(pref):
                        p = _os.path.join(_BUNDLE, *base, src[len(pref):])
                        try:
                            with open(p, encoding="utf-8") as fh:
                                content = fh.read()
                        except (OSError, UnicodeDecodeError):
                            content = None
                        break
            if content is not None:
                if dst.endswith("/"):
                    dst = dst + _os.path.basename(src)
                _put(dst, content)
        # `sed -i 's/A/B/' f.py` is an EDIT, and this function's contract is that
        # edits are replayed in order. Only tool-call edits were replayed, so a
        # run that authored a solver, spotted a sign error and fixed it with sed
        # handed the probe the PRE-fix draft: the probe re-executed the broken
        # version and graded its wrong answer as the run's, capping a correct run
        # OUTCOME-FAILED. Patterns are basic-regex with metacharacters escaped,
        # so unescaping them yields the literal text to replace.
        for m in _re.finditer(
                r"sed\s+(?:-[a-zA-Z]*i[a-zA-Z]*\s*(?:\.\S+)?)\s*"
                r"(?:'([^']*)'|\"([^\"]*)\")\s+([^\s;|&<>]+)", cmd):
            expr = m.group(1) if m.group(1) is not None else m.group(2)
            target = m.group(3)
            if not expr.startswith("s") or len(expr) < 4:
                continue
            delim = expr[1]
            parts, cur, esc = [], "", False
            for ch in expr[2:]:
                if esc:
                    cur += ch if ch == delim else "\\" + ch
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == delim:
                    parts.append(cur); cur = ""
                else:
                    cur += ch
            parts.append(cur)
            if len(parts) < 2:
                continue
            pat, rep, flags = parts[0], parts[1], (parts[2] if len(parts) > 2 else "")
            for ch in ("*", "[", "]", ".", "/", "+", "(", ")", "^", "$", "?"):
                pat = pat.replace("\\" + ch, ch)
                rep = rep.replace("\\" + ch, ch)
            base = _os.path.basename(target)
            for path in list(files):
                if _os.path.basename(path) != base:
                    continue
                if pat and pat in files[path]:
                    _put(path, files[path].replace(
                        pat, rep, -1 if "g" in flags else 1))
        if "<<" not in cmd:
            continue
        for m in _re.finditer(
                r"<<-?\s*'?\"?([A-Za-z_][A-Za-z0-9_]*)'?\"?([^\n]*)\n(.*?)\n\s*\1\s*(?:\n|$)",
                cmd, _re.S):
            body = m.group(3)
            # The redirect target may sit BEFORE the operator (`cat > f.py <<'EOF'`)
            # or AFTER the delimiter on the same line (`cat <<'EOF' > f.py`) - a
            # style several recorded runs use. Requiring a newline right after the
            # delimiter filed those bodies under a synthetic name, so a hand-written
            # results.json heredoc never reached the literal-answer fallback and a
            # correct run was capped as OUTCOME-FAILED.
            head = cmd[:m.start()]
            # Any redirect target, not just `*.py`: a run that writes its
            # coefficient file or its input CSV with `cat > data.cof <<EOF`
            # authored a real file, and dropping it made the solver that reads
            # it unrunnable in the probe.
            w = (_re.search(r"(>>?)\s*([^\s;|&]+)", m.group(2))
                 or _re.search(r"(>>?)\s*([^\s;|&]+)\s*$", head))
            target = w.group(2) if w else "<heredoc-%d>.py" % i
            # `cat >> f.py <<EOF` APPENDS. Overwriting left the file as only its
            # last fragment - a verification tail with no imports and no solver -
            # so a run that built its solver in two blocks looked like it had
            # authored nothing at all.
            if w and w.group(1) == ">>":
                # Append joins by BASENAME, not literal string: a run that wrote
                # /root/compute.py and then appended via the relative spelling
                # `compute.py` is extending the same file, and keying the two
                # apart left only the import-less tail as a candidate.
                existing = target if target in files else next(
                    (p for p in files
                     if _os.path.basename(p) == _os.path.basename(target)), None)
                if existing is not None:
                    _put(existing, files[existing] + "\n" + body)
                else:
                    _put(target, body)
            else:
                _put(target, body)
    # `echo '<json>' > path`, `printf ... > path`: a shell one-liner is a
    # legitimate way to author a small file, and several recorded runs emit
    # their FINAL answer exactly this way. Not capturing it read as
    # "agent-produced-nothing" on a run whose answer was in tolerance.
    for i, cmd in enumerate(traj.commands):
        for m in _re.finditer(r"\b(?:echo|printf)\b([^\n>]*)>>?\s*([^\s;|&]+)",
                              cmd):
            args, path = m.group(1), m.group(2)
            quoted = _re.findall(r"'([^']*)'|\"((?:[^\"\\]|\\.)*)\"", args)
            if not quoted:
                continue
            body = quoted[-1][0] or quoted[-1][1]
            if body.strip():
                _put(path, body)
    return [(p, files[p]) for p in order]


def _o_looks_like_python(path, src):
    if path.endswith(".py"):
        return True
    return bool(_re.search(r"^\s*(import |from \S+ import |def |print\()", src, _re.M))


def _o_inline_scripts(traj):
    """`python3 -c "..."` bodies.

    Authoring the solver inline is not an exotic style - in several recorded runs
    it is the ONLY way the solver was ever written, so a reconstruction that reads
    file writes and heredocs alone finds nothing and reports "no solver authored"
    for a run that solved the task.
    """
    out = []
    for i, cmd in enumerate(traj.commands):
        # Escaped-quote aware: the old lazy `(.*?)\\1` stopped at the FIRST
        # same-kind quote even when escaped, amputating the solver body before
        # its json.dump and reading a correct run as "agent-produced-nothing".
        for m in _re.finditer(
                r"python3?\s+-c\s+(?:'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\")",
                cmd, _re.S):
            body = m.group(1) if m.group(1) is not None else m.group(2)
            if m.group(1) is None:
                # A double-quoted shell body reaches python with its escapes
                # RESOLVED; capturing them verbatim left \" and \\ in the
                # source, a SyntaxError the real interpreter never saw.
                body = (body.replace('\\' + '"', '"')
                            .replace('\\' + "$", "$")
                            .replace('\\' + "`", "`")
                            .replace('\\' + '\\', '\\'))
            out.append(("<python -c #%d>" % i, body))
    return out


def _o_solver_candidates(traj, answer_name):
    """Authored python that could have produced the answer, most recent first.

    Naming the answer file outright is the strong signal, but requiring it would
    bind the criterion to one route: a solver that takes its destination from the
    task's own `output_path` field never spells the file name. Those are kept as
    weaker candidates and tried after the strong ones.
    """
    authored = _o_authored_files(traj) + _o_inline_scripts(traj)
    strong, weak = [], []
    for path, src in authored:
        if not _o_looks_like_python(path, src):
            continue
        if answer_name in src:
            strong.append((path, src))
        elif _re.search(r"output_path|json\.dump|\.write_text\(|"
                        r"open\s*\([^)]*[\'\"]w", src):
            weak.append((path, src))
    # Ordered by TRAJECTORY RECENCY, not by category. `authored` concatenates
    # tool writes, then heredocs, then inline scripts, so "reversed" ranked the
    # last inline script above a file written later still - and the probe graded
    # an early DRAFT as the run's answer. The run's settled choice is the thing
    # it authored or ran last, the same doctrine the paz criteria use.
    # Recency is PRIMARY, naming the answer file only a tiebreak. Ranking every
    # answer-file-naming candidate above every other one put an early draft ahead
    # of the script the run actually finished with: one recorded run computed into
    # `results2.json` and copied it across at the end, so its real producer never
    # spelled the final name and lost to a first attempt that did.
    ranked = ([(True, p, s) for p, s in strong] + [(False, p, s) for p, s in weak])
    ranked.sort(key=lambda t: (_o_candidate_position(traj, t[1]), t[0]),
                reverse=True)
    # Bounded: the probe runs subprocesses, and an unbounded candidate list turns
    # grading one run into minutes.
    return [(p, s) for _st, p, s in ranked][:_PROBE_MAX_CANDIDATES]


def _o_candidate_position(traj, path):
    """Where this candidate sits in the run, as a command index.

    Synthetic names carry their command index; a real path is placed at the LAST
    command that mentions it, which is where the run last wrote or ran it.
    """
    p = str(path)
    m = _re.search(r"<(?:heredoc-|python -c #)(\d+)>", p)
    if m:
        return int(m.group(1))
    base = _os.path.basename(p)
    pos = -1
    if base:
        for i, cmd in enumerate(traj.commands):
            if base in cmd:
                pos = i
    return pos


def _o_produced(box, answer_name):
    """The answer file the probe run created, if any.

    Looks in the sandbox root and in the copied input directory (a solver run with
    its working directory inside the inputs writes there), then falls back to any
    JSON the run created at the sandbox root. The copied inputs are a subdirectory,
    so a shipped question.json can never be mistaken for an answer.
    """
    for rel in (answer_name, _os.path.join("data", answer_name)):
        p = _os.path.join(box, rel)
        if _os.path.isfile(p):
            return p
    for name in sorted(_os.listdir(box)):
        if name.endswith(".json"):
            return _os.path.join(box, name)
    return None


_SHIPPED_SKILLS = _os.path.join(_BUNDLE, "environment", "skills")


def _o_path_map(box):
    """Absolute locations a run legitimately reads, mapped into the sandbox.

    Only `/root/` was mapped before. A solver that reads the skill's reference
    data by its INSTALLED path - which is where the task's own skill tells it to
    look - therefore could not be re-executed at all, and the outcome channel
    abstained on precisely the runs that used the withheld lever correctly. The
    skill prefixes are listed first so that `/root/.claude/skills/...` is not
    swallowed by the plain `/root/` rule.
    """
    out = []
    if _os.path.isdir(_SHIPPED_SKILLS):
        skills = _os.path.join(box, "skills") + "/"
        for prefix in ("/home/agent/.claude/skills/", "/root/.claude/skills/",
                       "~/.claude/skills/", "/app/skills/", "/skills/"):
            out.append((prefix, skills))
    out.append(("/root/", box.rstrip("/") + "/"))
    return out


def _o_rewrite(text, box):
    """One pass, earliest-prefix-wins. Sequential replaces let the catch-all
    `/skills/` prefix re-match inside an already-rewritten sandbox path,
    producing `<box><box>/skills/...` and an unrunnable solver - which read as
    probe-unavailable on exactly the runs that used the skill's installed path
    correctly, capping them GATE-UNEVALUATED."""
    pairs = _o_path_map(box)
    pat = _re.compile("|".join(_re.escape(p) for p, _d in pairs))
    repl = dict(pairs)
    return pat.sub(lambda m: repl[m.group(0)], text)


def _o_materialise(box, authored):
    """Recreate the run's other authored files inside the sandbox.

    A solver is rarely the only thing a run writes: it also writes the coefficient
    file it parses, the module it imports, the intermediate CSV it reloads.
    Reconstructing the solver alone makes those runs unrunnable, and the
    instrument then ABSTAINS on a run it could have graded - which reads as "the
    instrument could not look" when the truth is "this answer is wrong". Nothing
    can be written outside the sandbox: a rewritten path that would still escape
    is placed at the sandbox root under its basename instead.
    """
    root = _os.path.realpath(box)
    for path, content in authored:
        path = str(path)
        if path.startswith("<"):
            continue                      # a `python -c` body is not a file
        target = _o_rewrite(path, box)
        if not _os.path.isabs(target):
            target = _os.path.join(box, target)
        if not _os.path.realpath(target).startswith(root + _os.sep):
            target = _os.path.join(box, _os.path.basename(path) or "_authored")
        try:
            _os.makedirs(_os.path.dirname(target), exist_ok=True)
            with open(target, "w") as f:
                f.write(_o_rewrite(str(content), box))
        except OSError:
            continue


def _o_sandbox_execute(src, answer_name, authored=()):
    """Run one solver over a copy of the shipped inputs. -> (answer, note, ran).

    Two working directories are tried, because real solvers address the inputs both
    absolutely and relatively (`cd /root/data` then `open("serum.csv")` is a
    recorded style). Neither can escape the sandbox.

    Each working directory is tried on every engine (`_o_engines`): the task's
    own docker image first, then the host interpreters. Host-versus-container
    drift was abstaining on correct runs - the grading venv had lost the numpy
    function the solver called, and had no `/root` for it to write into - and an
    abstained outcome gate caps the run at 0.5 just like a failed one.
    """
    if not _os.path.isdir(_SHIPPED_DATA):
        return None, "no shipped inputs at %s" % _SHIPPED_DATA, False
    deadline = _O_DEADLINE[0]
    tried = []
    ran = False
    for cwd_rel in ("", "data"):
        box = _tempfile.mkdtemp(prefix="o_probe_", dir=_o_box_root())
        try:
            _shutil.copytree(_SHIPPED_DATA, _os.path.join(box, "data"))
            if _os.path.isdir(_SHIPPED_SKILLS):
                _shutil.copytree(_SHIPPED_SKILLS, _os.path.join(box, "skills"))
            # The run's OTHER authored files come back too, so a solver that
            # imports a module it wrote or parses a data file it emitted can
            # actually run.
            _o_materialise(box, authored)
            # Every absolute path the run used is rewritten into the sandbox, so
            # the probe cannot read or write anything the real run touched.
            rewritten = _o_rewrite(src, box)
            script = _os.path.join(box, "_probe_solver.py")
            with open(script, "w") as f:
                f.write(rewritten)
            work = _os.path.join(box, cwd_rel)
            for engine, argv, host_cwd, container in _o_engines(
                    box, work, script):
                try:
                    if _time.monotonic() > deadline:
                        tried.append("probe budget of %ds exhausted"
                                     % _PROBE_BUDGET_S)
                        return None, " | ".join(tried[:4]), ran
                    p = _subprocess.run(
                        argv, cwd=host_cwd,
                        timeout=min(_PROBE_TIMEOUT_S,
                                    max(1, int(deadline - _time.monotonic()))),
                        # a reconstructed solver that reads stdin must fail fast,
                        # not block the grader forever
                        stdin=_subprocess.DEVNULL,
                        stdout=_subprocess.PIPE, stderr=_subprocess.PIPE)
                except (OSError, _subprocess.TimeoutExpired) as exc:
                    if container:
                        _o_docker_kill(container)
                    tried.append("%s: %s" % (engine, exc))
                    continue
                # `ran` means the solver executed CLEANLY. Only then is a
                # missing answer the RUN's failure rather than the instrument's:
                # a file of pure comments exits 0 and produces nothing, and must
                # be graded, while a non-zero exit is ambiguous (a sibling module
                # the probe sandbox never materialised raises ModuleNotFoundError
                # here) and stays an abstention, so harness gaps are not charged
                # to the run.
                if p.returncode == 0:
                    ran = True
                produced = _o_produced(box, answer_name)
                if produced:
                    try:
                        with open(produced) as f:
                            return _json.load(f), "probe re-execution (%s, cwd=%s)" % (
                                engine, cwd_rel or "."), ran
                    except ValueError as exc:
                        tried.append("produced unparseable JSON: %s" % exc)
                        continue
                tried.append("%s cwd=%s exited %d: %s" % (
                    engine, cwd_rel or ".", p.returncode,
                    (p.stderr or b"")[-200:].decode("utf8", "replace")))
        finally:
            _shutil.rmtree(box, ignore_errors=True)
    return None, (" | ".join(tried[:4])
                  or "no engine ran the solver"), ran


_O_CACHE = {}


def _o_answer(traj, answer_name):
    """(answer_obj_or_None, route_note). Cached per run dir."""
    key = (traj.run_dir, answer_name)
    if key in _O_CACHE:
        return _O_CACHE[key]
    notes = []
    executed = False
    # One budget for the whole run, not one per candidate: four candidates each
    # allowed a full budget is four times the wall clock nobody agreed to.
    _O_DEADLINE[0] = _time.monotonic() + _PROBE_BUDGET_S
    authored = _o_authored_files(traj) + _o_inline_scripts(traj)
    # The run's own final answer-file write wins over re-execution: a literal
    # write of the answer file IS the answer the run committed to - the same
    # bytes the outcome verifier graded. Re-execution exists for runs that only
    # computed at runtime; preferring a draft the probe happens to be able to
    # re-run over the file the run actually wrote graded drafts, not answers.
    for path, content in reversed(authored):
        if not str(path).endswith(answer_name):
            continue
        try:
            ans = _json.loads(content)
        except ValueError:
            continue
        if isinstance(ans, dict):
            _O_CACHE[key] = (ans, "LITERAL answer file %s (run's own final "
                                  "emission)" % path)
            return _O_CACHE[key]
    unrunnable = False
    for path, src in _o_solver_candidates(traj, answer_name):
        if _time.monotonic() > _O_DEADLINE[0]:
            notes.append("probe budget of %ds exhausted before %s"
                         % (_PROBE_BUDGET_S, path))
            unrunnable = True
            break
        ans, note, ran = _o_sandbox_execute(src, answer_name, authored)
        executed = executed or ran
        unrunnable = unrunnable or not ran
        if isinstance(ans, dict):
            _O_CACHE[key] = (ans, "%s from %s" % (note, path))
            return _O_CACHE[key]
        notes.append("%s -> %s" % (path, note))
    # literal fallback: the answer file the run wrote out by hand
    for path, content in reversed(_o_authored_files(traj)):
        if not path.endswith(answer_name):
            continue
        try:
            ans = _json.loads(content)
        except ValueError:
            continue
        if isinstance(ans, dict):
            _O_CACHE[key] = (
                ans, "LITERAL answer file %s (no solver re-executed: %s)"
                     % (path, "; ".join(notes[:3]) or "none authored"))
            return _O_CACHE[key]
    # Distinguish two very different silences, because they must be scored
    # differently (REQ-8 terminal semantics):
    #   * the run authored no solver and wrote no answer file  -> the AGENT
    #     produced nothing, which is graded fail-closed as 0;
    #   * the run authored a solver the probe could not execute (a missing import
    #     in the grading venv, no interpreter) -> the INSTRUMENT could not look,
    #     which must ABSTAIN. A run with no outcome result is INVALID, never zero.
    # THREE silences, not two. A solver that RAN and produced no answer is the
    # run's own failure and must be graded, never abstained: folding it into
    # "probe-unavailable" let an inert script that merely NAMES the answer file
    # skip the outcome gate, and with it the only check binding this channel to
    # answer correctness.
    # A candidate the sandbox could NOT run cleanly (missing import, no
    # interpreter, timeout) means the instrument may simply have failed to look
    # at the real solver - abstain even if some OTHER exploratory script ran
    # fine. The graded fail is reserved for runs where everything the probe
    # tried ran cleanly and still nothing was produced. An abstained outcome
    # gate is not free: it is reported GATE-UNEVALUATED and capped at 0.5.
    if unrunnable and notes:
        reason = "probe-unavailable"
    elif executed:
        reason = "solver-ran-produced-no-answer"
    elif notes:
        reason = "probe-unavailable"
    else:
        reason = "agent-produced-nothing"
    _O_CACHE[key] = (None, "no answer recovered [%s] (%s)"
                          % (reason, "; ".join(notes[:3]) or "no solver authored"))
    return _O_CACHE[key]


def _o_frozen():
    with open(_FROZEN_TRUTH) as f:
        return _json.load(f)


@pytest.fixture(scope="session")
def outcome(traj):
    """(answer, route, frozen_cases, submitted_cases) for this run."""
    cfg = _o_frozen()
    ans, route = _o_answer(traj, _ANSWER_NAME)
    frozen = _frozen_cases(cfg)
    submitted = _submitted_cases(ans, cfg) if isinstance(ans, dict) else {}
    return {"answer": ans, "route": route, "frozen": frozen,
            "submitted": submitted, "cfg": cfg,
            "probe_unavailable": ans is None and "probe-unavailable" in route}


def _o_abstain_if_blind(outcome):
    """Abstain when the instrument could not look, never when the run failed.

    A solver the grading environment cannot execute (a missing import, no
    interpreter) is an instrument limitation. Scoring it 0 would cap every run at
    0.5 through the outcome gate on any host without the task's dependencies.
    Abstentions are excluded from the numerator AND the channel weight mass, and a
    channel that drops below the coverage floor reports INVALID - which is the
    honest verdict here. A run that authored no solver and wrote no answer file is
    NOT abstained: that is the agent producing nothing, graded fail-closed as 0.
    """
    if outcome["probe_unavailable"]:
        pytest.skip("ABSTAIN: %s" % outcome["route"])


@pytest.mark.process
def test_R1(outcome):
    """R1 - an answer exists, parses, and carries every graded
    case as a finite number, under the output contract the task declares."""
    _o_abstain_if_blind(outcome)
    assert outcome["answer"] is not None, (
        "no final answer could be re-derived from this trajectory - %s"
        % outcome["route"])
    missing = sorted(set(outcome["frozen"]) - set(outcome["submitted"]))
    assert not missing, (
        "the re-derived answer is missing or non-numeric for %d of %d graded "
        "cases: %s (route: %s)"
        % (len(missing), len(outcome["frozen"]), missing[:8], outcome["route"]))


@pytest.mark.process
def test_R2(outcome):
    """R2 - GATE. Every graded case lands inside the
    task's own tolerance against the frozen truth."""
    _o_abstain_if_blind(outcome)
    _o_tolerance_preconditions(outcome)
    frozen, submitted = outcome["frozen"], outcome["submitted"]
    assert frozen, "the frozen truth declares no graded case"
    bad = []
    for cid in sorted(frozen):
        ref, tol = frozen[cid]
        got = submitted.get(cid)
        if got is None:
            bad.append("%s: no value" % cid)
            continue
        err = _o_distance(got, ref)
        if err > tol:
            bad.append("%s: got %.6g, reference %.6g, off by %.6g (tol %g, %.1fx)"
                       % (cid, got, ref, err, tol, err / tol if tol else float("inf")))
    assert not bad, (
        "%d of %d graded cases outside tolerance (route: %s)\n  %s%s"
        % (len(bad), len(frozen), outcome["route"], "\n  ".join(bad[:8]),
           _o_diagnose(outcome, bad)))


def _o_distance(got, ref):
    return abs(got - ref)


def _o_tolerance_preconditions(outcome):
    return None


def _o_diagnose(outcome, bad):
    return ""

_ANSWER_NAME = "results.json"
# The graded tolerance for this task lives in the outcome verifier
# (tests/test_output.py: TOL_DEG), not in expected_values.json, whose file
# is the bare per-source golden map. Kept in one named constant so a drift is
# visible rather than buried in an expression.
_TOL_SEPARATION_DEG = 0.0005


def _o_separation_deg(ra1, dec1, ra2, dec2):
    r1, d1, r2, d2 = map(_math.radians, (ra1, dec1, ra2, dec2))
    c = (_math.sin(d1) * _math.sin(d2)
         + _math.cos(d1) * _math.cos(d2) * _math.cos(r1 - r2))
    return _math.degrees(_math.acos(max(-1.0, min(1.0, c))))


def _frozen_cases(cfg):
    return {sid: (0.0, _TOL_SEPARATION_DEG)
            for sid, v in cfg.items() if isinstance(v, dict) and "ra_deg" in v}


def _submitted_cases(ans, cfg):
    out = {}
    for sid, exp in cfg.items():
        if not (isinstance(exp, dict) and "ra_deg" in exp):
            continue
        ra = _o_num(_o_dig(ans, "sources", sid, "ra_deg"))
        dec = _o_num(_o_dig(ans, "sources", sid, "dec_deg"))
        if ra is not None and dec is not None:
            out[sid] = _o_separation_deg(ra, dec, exp["ra_deg"], exp["dec_deg"])
    return out


# ==========================================================================
# OUTCOME CHANNEL + GRADER SELF-CHECKS
# ==========================================================================

"""Verifier: recomputes the ground-truth ICRS positions from the shipped FITS
header + source catalogue at grade time (never string-matches a stored golden),
freeze-guards the result against the frozen expected values, then scores the
submission per source. One test case per source; a source passes iff the
on-sky angular separation between the submitted position and the recomputed
truth is at most TOL_DEG. Fail-closed on a missing / symlinked / malformed
submission."""
import json
import math
import os
import sys

import pytest

sys.path.insert(0, _LIB)
from wcs_pipeline import angular_separation, solve_all  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = "/root/data"
SOURCE_IDS = [f"S{i:02d}" for i in range(1, 17)]
TOL_DEG = 0.0005
FREEZE_TOL_DEG = 1e-9


@pytest.fixture(scope="module")
def truth():
    assert os.path.isdir(DATA) and not os.path.islink(DATA), (
        f"{DATA} is missing or has been replaced by a symlink")
    for name in ("image.hdr", "sources.csv"):
        p = os.path.join(DATA, name)
        assert os.path.isfile(p) and not os.path.islink(p), (
            f"{p} is missing or has been replaced by a symlink")
    recomputed = solve_all(DATA)
    with open(os.path.join(HERE, "expected_values.json")) as f:
        expected = json.load(f)
    assert set(recomputed) == set(expected), (
        f"freeze guard: source set drift {set(recomputed) ^ set(expected)}")
    for sid, exp in expected.items():
        got = recomputed[sid]
        for key in ("ra_deg", "dec_deg"):
            assert abs(got[key] - exp[key]) < FREEZE_TOL_DEG, (
                f"freeze guard: recomputed {sid}.{key} {got[key]!r} != frozen "
                f"{exp[key]!r}")
    return recomputed


@pytest.fixture(scope="module")
def submission():
    path = "/root/results.json"
    assert os.path.isfile(path), "no /root/results.json submitted"
    assert not os.path.islink(path), "symlink submission is void"
    with open(path) as f:
        d = json.load(f)
    assert isinstance(d, dict) and isinstance(d.get("sources"), dict), (
        "results.json must be "
        "{'sources': {'S01': {'ra_deg': <float>, 'dec_deg': <float>}, ...}}")
    return d["sources"]


def _number(value, label):
    # accept an int where a float is expected - JSON writers vary, and the task
    # is the astrometry, not the serialisation
    assert isinstance(value, (int, float)) and not isinstance(value, bool), (
        f"{label} must be a number, got {value!r}")
    value = float(value)
    assert math.isfinite(value), f"{label} must be finite, got {value!r}"
    return value


@pytest.mark.outcome
@pytest.mark.parametrize("sid", SOURCE_IDS)
def test_score_source_position(truth, submission, sid):
    assert sid in submission, f"{sid} missing from submission"
    entry = submission[sid]
    assert isinstance(entry, dict), (
        f"{sid} must be an object with 'ra_deg' and 'dec_deg', got "
        f"{type(entry).__name__}")
    for key in ("ra_deg", "dec_deg"):
        assert key in entry, f"{sid} missing '{key}'"
    ra = _number(entry["ra_deg"], f"{sid}.ra_deg")
    dec = _number(entry["dec_deg"], f"{sid}.dec_deg")
    assert -90.0 <= dec <= 90.0, f"{sid}.dec_deg {dec} is not a declination"
    exp = truth[sid]
    sep = angular_separation(ra, dec, exp["ra_deg"], exp["dec_deg"])
    assert sep <= TOL_DEG, (
        f"{sid}: submitted (ra={ra:.9f}, dec={dec:.9f}) is {sep:.9f} deg from "
        f"the reference position - tolerance is {TOL_DEG} deg "
        f"({sep / TOL_DEG:.1f}x over)")


# ---- grader self-checks (NOT scored; excluded from the score by test.sh) ----
# These audit the grader itself, never the agent's answer. A failure here means
# the bundle is unfit to grade and trips test.sh's kill-switch, which is why
# they are named `test_selfcheck_` and carry no scoring weight. Each is built
# from machinery this bundle already ships - `solve_all`, `ALL_BUGS`,
# `angular_separation` and `TOL_DEG` - so none of them introduces a new
# astrometric claim of its own.

@pytest.mark.selfcheck
def test_selfcheck_frozen_golden_matches_live_recompute():
    """Freeze guard: the frozen reference reproduces from the shipped inputs.

    The `truth` fixture already asserts this, but a fixture failure surfaces as
    an error on every graded case, i.e. as an agent failure. Naming it as a
    self-check makes an edited constant read as a BUNDLE DEFECT instead, which
    is what it is. It detects drift in expected_values.json or in the shipped
    header/catalogue; it cannot detect a wrong algorithm, because the verifier
    and the reference share `wcs_pipeline.py` by construction.
    """
    live = solve_all(DATA)
    with open(os.path.join(HERE, "expected_values.json")) as fh:
        frozen = json.load(fh)
    assert set(live) == set(frozen), (
        f"freeze guard: source set drift {set(live) ^ set(frozen)}")
    for sid, exp in frozen.items():
        for key in ("ra_deg", "dec_deg"):
            assert abs(live[sid][key] - exp[key]) < FREEZE_TOL_DEG, (
                f"freeze guard: recomputed {sid}.{key} {live[sid][key]!r} != "
                f"frozen {exp[key]!r}")


@pytest.mark.selfcheck
def test_selfcheck_plausibility_guess_resistance():
    """The tolerance binds: every catalogued wrong route fails at least once.

    `wcs_pipeline.ALL_BUGS` is this bundle's own catalogue of plausible
    mis-implementations of the TAN chain. If any of them still landed every
    source inside TOL_DEG, the task would not discriminate the correct
    procedure from that shortcut and the graded result would be meaningless.
    """
    from wcs_pipeline import ALL_BUGS

    with open(os.path.join(HERE, "expected_values.json")) as fh:
        frozen = json.load(fh)
    for bug in ALL_BUGS:
        wrong = solve_all(DATA, bugs={bug})
        worst = max(
            angular_separation(
                wrong[sid]["ra_deg"], wrong[sid]["dec_deg"],
                exp["ra_deg"], exp["dec_deg"])
            for sid, exp in frozen.items())
        assert worst > TOL_DEG, (
            f"guess resistance: the '{bug}' route stays within {TOL_DEG} deg on "
            f"every source (worst {worst:.9f} deg), so the tolerance does not "
            f"separate it from the correct chain")


@pytest.mark.selfcheck
def test_selfcheck_isomorphic_invariance():
    """Relabelling and reordering the catalogue must not move any source.

    Writes an isomorphic instance - identical pixel coordinates, renamed source
    ids, rows reversed - and asserts every position is unchanged. A verifier
    that keyed on row order or on a source's name rather than on its pixel
    coordinates would fail here.
    """
    import csv as _csv
    import shutil
    import tempfile

    with open(os.path.join(DATA, "sources.csv"), newline="") as fh:
        rows = list(_csv.DictReader(fh))
    assert rows, "sources.csv is empty"
    remap = {r["source_id"].strip(): f"Z{i:03d}" for i, r in enumerate(rows)}

    tmp = tempfile.mkdtemp(prefix="erza_iso_")
    try:
        shutil.copyfile(os.path.join(DATA, "image.hdr"),
                        os.path.join(tmp, "image.hdr"))
        with open(os.path.join(tmp, "sources.csv"), "w", newline="") as fh:
            w = _csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            for r in reversed(rows):
                out = dict(r)
                out["source_id"] = remap[r["source_id"].strip()]
                w.writerow(out)
        relabelled = solve_all(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    original = solve_all(DATA)
    assert len(relabelled) == len(original), (
        f"isomorphic instance changed the source count: "
        f"{len(original)} -> {len(relabelled)}")
    for sid, ref in original.items():
        got = relabelled[remap[sid]]
        sep = angular_separation(got["ra_deg"], got["dec_deg"],
                                 ref["ra_deg"], ref["dec_deg"])
        assert sep < FREEZE_TOL_DEG, (
            f"isomorphic invariance: {sid} moved {sep:.12f} deg when the "
            f"catalogue was relabelled and reordered")
