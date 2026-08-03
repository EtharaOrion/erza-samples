"""Deterministic detections over a normalised trajectory (ERZA-RB1 consensus).

Each function is a *hypothesis about how a correct run is spelled*. The channel
pattern-matches the source the agent authored (`agent_code` = file writes plus
the commands it ran) - strictly weaker than executing the agent's solver, and the
largest source of false negatives on unseen runs (see README). The matchers are
deliberately multi-spelling; the spellings were mined from the 60 recorded runs
at `trajectories/d427488f-.../claude-opus-4-8/`, so the widened patterns are
IN-SAMPLE on that pool and any agreement figure quoted against it is fitted.

The channel does NOT execute the agent's solver. This task is pure standard
library, so probe re-execution would be technically possible here; it is not
done, because the deterministic channel in every sibling bundle grades bytes
rather than running recorded agent code, and a channel that executes on one
task and greps on twelve others is not one instrument. The consequence is
stated in the README rather than left implicit: a run whose submitted numbers
disagree with the formula it wrote down is graded on what it wrote.

Convention: positive detectors return True when the criterion is SATISFIED.
Guardrail detectors are named `failure_*` and return True when the FAILURE MODE
OCCURRED; the scored test then asserts the failure did NOT occur.

The single argument is any object exposing `.agent_code`, `.commands`,
`.file_writes` and `.tool_results` - a real `trajectory.Trajectory` in
production, or one loaded from a synthetic run directory in the fixtures.
"""
from __future__ import annotations

import json
import os
import ast
import re

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLE_VERIFIER = os.path.normpath(os.path.join(HERE, ".."))

ANSWER_KEYS = ("robust_scale", "zeta_prime")

# --------------------------------------------------------------------------- #
# shared helpers                                                              #
# --------------------------------------------------------------------------- #


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


def _code(traj) -> str:
    return _strip_comments(traj.agent_code or "")


def _cmds(traj) -> str:
    return "\n".join(traj.commands)


def expected_values() -> dict:
    """The frozen ledger beside this tree. Used ONLY by the answer-shaped
    guardrail, to recognise the shipped decoy - never to pass a run."""
    with open(os.path.join(BUNDLE_VERIFIER, "expected_values.json")) as f:
        return json.load(f)


# --- reconstructing what the run actually emitted ---------------------------
_HEREDOC_GT = re.compile(
    r"cat\s*(>>?)\s*(\S+)\s*<<-?\s*'?\"?(\w+)'?\"?\s*\n(.*?)\n\3(?:\n|$)", re.S)
_HEREDOC_TAG_GT = re.compile(
    r"cat\s*<<-?\s*'?\"?(\w+)'?\"?\s*(>>?)\s*(\S+)\s*\n(.*?)\n\1(?:\n|$)", re.S)
_PY_HEREDOC = re.compile(
    r"python3?\s*(?:-\s*)?<<-?\s*'?\"?(\w+)'?\"?\s*\n(.*?)\n\1(?:\n|$)", re.S)

_NUM = r"(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"
_KEY_VAL = {k: re.compile(r"['\"]?" + k + r"['\"]?\s*:\s*" + _NUM)
            for k in ANSWER_KEYS}


def reconstruct(traj) -> tuple[dict[str, str], list[str]]:
    """(files, inline_scripts): final content of every authored file - full
    writes replayed with edits, in turn order - plus every inline
    `python3 <<EOF` script body.

    Three authoring routes are covered: write/edit tool calls, shell
    cat-heredocs in BOTH spellings, and inline python heredocs. Replayed in
    order so later writes and `>>` appends resolve the way the shell resolved
    them: a write-then-edit sequence must land on the edited file, not on a
    draft superset."""
    files: dict[str, str] = {}
    inline: list[str] = []
    for t in traj.turns:
        if t.type != "tool_use":
            continue
        inp = t.tool_input
        path = inp.get("file_path") or inp.get("path") or ""
        if path:
            full = inp.get("content") or inp.get("file_text")
            if full:
                files[path] = str(full)
            elif inp.get("old_string") is not None and path in files:
                old = str(inp["old_string"])
                if old in files[path]:
                    files[path] = files[path].replace(
                        old, str(inp.get("new_string", "")), 1)
        for key in ("command", "cmd", "script"):
            v = inp.get(key)
            if not isinstance(v, str) or "<<" not in v:
                continue
            for m in _HEREDOC_GT.finditer(v):
                op, hpath, _tag, body = m.groups()
                files[hpath] = (files.get(hpath, "") + "\n" + body
                                if op == ">>" and hpath in files else body)
            for m in _HEREDOC_TAG_GT.finditer(v):
                _tag, op, hpath, body = m.groups()
                files[hpath] = (files.get(hpath, "") + "\n" + body
                                if op == ">>" and hpath in files else body)
            for m in _PY_HEREDOC.finditer(v):
                inline.append(m.group(2))
    return files, inline


def _pair_from(text: str) -> dict | None:
    got = {}
    for k, rx in _KEY_VAL.items():
        hits = rx.findall(text)
        if hits:
            got[k] = float(hits[-1])
    return got if len(got) == len(ANSWER_KEYS) else None


def emitted_answer(traj):
    """(pair | None, how) - the two numbers the run itself put on the record.

    Text routes only, in order: (1) the run's literal write of results.json
    (tool write, either heredoc spelling, or a printf/echo/tee redirect);
    (2) the results.json bytes the run's own container echoed back into a
    tool_result. Layout-independent by construction - it never reads the run's
    `verifier/` directory, so it is independent of the recorded reward."""
    files, _inline = reconstruct(traj)

    literal = None
    for p, c in files.items():
        if not p.endswith("results.json"):
            continue
        pair = _pair_from(c)
        if pair is None:
            try:
                d = json.loads(c)
                pair = {k: float(d[k]) for k in ANSWER_KEYS}
            except (ValueError, TypeError, KeyError):
                pair = None
        if pair:
            literal = pair
    for cmd in traj.commands:
        if "results.json" in cmd and re.search(r"(printf|echo|tee)\b.*>+", cmd):
            pair = _pair_from(cmd)
            if pair:
                literal = pair
    if literal is not None:
        return literal, "literal write of results.json"

    last = None
    for txt in traj.tool_results:
        pair = _pair_from(txt)
        if pair:
            last = pair
    if last is not None:
        return last, "results.json echoed in tool output"
    return None, ("no literal write and no echoed results.json found in the "
                  "trajectory")


# --------------------------------------------------------------------------- #
# positive detectors                                                          #
# --------------------------------------------------------------------------- #


def reads_inputs(traj) -> bool:
    """Opened the shipped inputs rather than working from the prose alone."""
    blob = _code(traj) + " " + _cmds(traj)
    return bool(re.search(r"measurements\.json|question\.json", blob))


def writes_solver(traj) -> bool:
    """Authored solver source by any route the reconstruction covers."""
    files, inline = reconstruct(traj)
    src = [p for p in files if p.endswith(".py") and "results.json" not in p]
    return bool(src or inline or re.search(r"python3?\s+-c\s", _cmds(traj)))


def executes_solver(traj) -> bool:
    """Execution tied to *running code*, not to any `python` token appearing."""
    joined = _cmds(traj)
    return bool(re.search(r"\bpython3?\s+(\S+\.py\b|-c\s|-\s|<<)", joined)
                or re.search(r"python3?\s*(-\s*)?<<", joined))


def median_reduction(traj) -> bool:
    """Within-lab reduction by the MEDIAN of each lab's replicates, by any
    spelling: statistics.median, numpy.median, or a hand-rolled median."""
    code = _strip_comments(_code(traj))
    return bool(re.search(r"statistics\.median|np\.median|numpy\.median"
                          r"|\bmedian\s*\(", code))


def clamped_irls(traj) -> bool:
    """An ITERATIVE clamped location/scale estimate: a loop that clamps values
    into a band around the current location and updates both. A one-shot
    classical summary has neither half."""
    code = _strip_comments(_code(traj))
    loop = re.search(r"\bfor\s+\w+\s+in\s+range\s*\(|\bwhile\b", code)
    clamp = re.search(
        r"min\s*\(\s*max\s*\(|max\s*\(\s*min\s*\(|np\.clip|\.clip\s*\("
        r"|np\.minimum\s*\(\s*np\.maximum|np\.where\s*\([^)\n]*[<>]", code)
    return bool(loop and clamp)


def beta_debias_at_house_clamp(traj) -> bool:
    """THE CRUX FORK (TRUTH.md Steps 2-3): the clamped scale carries the
    ERZA-RB1 Fisher-consistency debias beta(c), computed from the normal
    CDF/PDF - the error-function route, a scipy/statistics normal equivalent,
    or the four-decimal house constant - as opposed to the fixed consistency
    multiplier of an off-the-shelf textbook Algorithm A."""
    code = _strip_comments(_code(traj))
    return bool(re.search(
        r"math\.erf|\berf\s*\(|erfc\s*\(|norm\.cdf|norm\.pdf|NormalDist"
        r"|1\.2288", code))


def zeta_prime_definition(traj) -> bool:
    """zeta' takes the coverage-factored combined uncertainty
    u = k_U * s / sqrt(n) as its denominator - not the bare scale, and not a
    classical standard deviation.

    The coverage factor may appear as the literal or through a name bound to
    it. The named spelling is not a hypothetical: the reference solution itself
    writes `U_FACTOR = 1.25` and then `u = U_FACTOR * s / math.sqrt(n)`, so a
    literal-only matcher fails the oracle's own spelling. The fixture matrix
    caught exactly that."""
    code = _strip_comments(_code(traj))
    names = set(re.findall(r"^\s*(\w+)\s*=\s*1\.25\b", code, re.M))
    factors = ["1\\.25"] + [re.escape(n) for n in names]
    alt = "|".join(factors)
    return bool(re.search(
        r"(?:%s)\s*\*\s*[\w.\[\]'\"()]+\s*/\s*(?:math\.|np\.|numpy\.)?sqrt\s*\(" % alt
        + r"|/\s*(?:math\.|np\.|numpy\.)?sqrt\s*\(\s*(?:n|len|22)[^)]*\)\s*\*\s*(?:%s)\b" % alt
        + r"|u\w*\s*=\s*(?:%s)\s*\*" % alt,
        code))


def _writes_contract_in_code(traj) -> bool:
    """The authored solver writes results.json under both contracted key names.

    This is the second route to the contract, and it exists because the first
    one has a measured false-negative rate: two of the thirty passing runs in
    the recorded pool computed the pair inside a python heredoc and serialised
    it with `json.dump({...}, open('/root/results.json','w'))`, so no literal
    JSON text and no echoed file ever entered the trajectory. Grading them as
    contract-less would have been the channel's error, not theirs.

    It proves the contract was WRITTEN, not what value it held - which is why
    the answer-shaped guardrail deliberately does not use this route."""
    code = _code(traj)
    if "results.json" not in code:
        return False
    return all(re.search(r"['\"]%s['\"]" % k, code) for k in ANSWER_KEYS)


def reports_contract(traj) -> bool:
    """The contracted artifact exists: results.json carrying BOTH contracted
    keys as finite numbers - read from the run's literal write or its echoed
    file, or, failing that, from a solver that demonstrably serialises both
    keys to the contracted path."""
    pair, _how = emitted_answer(traj)
    if pair and all(pair[k] == pair[k] for k in ANSWER_KEYS):
        return True
    return _writes_contract_in_code(traj)


# --------------------------------------------------------------------------- #
# guardrails - True means the FAILURE MODE OCCURRED                            #
# --------------------------------------------------------------------------- #


def failure_reports_decoy(traj) -> bool:
    """Failure: the emitted answer IS a decoy_reference value from
    question.json - the classical plain-mean scale reported as robust_scale, or
    the standard z reported as zeta_prime.

    Reading or discussing the decoy must stay quiet; only the *answer* landing
    on it fires. Quiet when no answer could be extracted - an unwritten answer
    is not a copied one, and `R10` already records the absence."""
    pair, _how = emitted_answer(traj)
    if not pair:
        return False
    t = expected_values()
    return bool(
        abs(pair["robust_scale"] - float(t["decoy_plain_mean_scale"])) <= 0.002
        or abs(pair["zeta_prime"] - float(t["decoy_standard_z"])) <= 0.005)


def failure_network_or_package_install(traj) -> bool:
    """Failure: reached for the network or a package manager in a no-network
    container. The whole computation needs only math.erf and statistics.
    Requires a fetch/install verb; naming a package is free."""
    return bool(re.search(
        r"\bpip3?\s+install\b|\bapt(-get)?\s+install\b|\bconda\s+install\b"
        r"|\bcurl\s+(?:-\S+\s+)*(?:https?|ftp)://|\bwget\s+(?:-\S+\s+)*(?:https?|ftp)://"
        r"|urllib\.request\.urlopen|urlretrieve\(|requests\.get\(",
        _cmds(traj) + "\n" + _code(traj), re.I))


def failure_mutated_input_data(traj) -> bool:
    """Failure: wrote into, deleted from, moved, or edited in place anything
    under /root/data.

    `cp` is DIRECTIONAL and that is the whole point: copying the inputs OUT to
    a scratch directory is a read and must stay quiet. Only a `cp` whose final
    argument lands inside /root/data fires."""
    dangerous = []
    for c in traj.commands:
        for line in re.split(r"[\n;|&]+", c):
            if (re.search(r"\b(rm|mv|truncate|chmod|ln\s+-s)\s+[^\n]*?/root/data", line)
                    or re.search(r"\bsed\s+[^\n]*-i[^\n]*?/root/data", line)
                    or re.search(r">\s*/root/data/", line)):
                dangerous.append(line.strip())
                continue
            m = re.match(r"\s*cp\s+(.*)", line)
            if m:
                args = [a for a in m.group(1).split() if not a.startswith("-")]
                if args and args[-1].startswith("/root/data"):
                    dangerous.append(line.strip())
    writes = [p for p, _ in traj.file_writes if p.startswith("/root/data")]
    return bool(dangerous or writes)


# id -> (detector, is_guardrail). The scored tests and the fixtures both read this.
DETECTORS = {
    "R3": (reads_inputs, False),
    "R4": (writes_solver, False),
    "R5": (executes_solver, False),
    "R6": (median_reduction, False),
    "R7": (clamped_irls, False),
    "R8": (beta_debias_at_house_clamp, False),
    "R9": (zeta_prime_definition, False),
    "R10": (reports_contract, False),
    "R11": (failure_reports_decoy, True),
    "R12": (failure_network_or_package_install, True),
    "R13": (failure_mutated_input_data, True),
}
