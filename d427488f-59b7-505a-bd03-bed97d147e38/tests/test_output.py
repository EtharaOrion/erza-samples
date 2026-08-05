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

"""Deterministic channel: one test per deterministic rubric criterion.

Each test is named `test_<criterion_id>` so the junit report joins straight back
to `rubrics.json` (see `score.py: read_junit`). The tests read the *normalised
trajectory* - the source the agent authored, the commands it ran, and the bytes
its own container echoed back - never the recorded verifier artifacts. Detection
logic lives in `checks.py`; every detector is bound by a fixture in
`the grader self-audit fixtures`.

Positive criteria: the test passes when the criterion is satisfied.
Guardrail criteria (`test_d_g_*`): the test passes when the failure mode did NOT
occur, and fails when it did - which `score.py` reads as "the failure happened".

The name-to-id pairing is load-bearing: `score.py` strips the leading `test_` and
joins on the remainder, so a test whose remainder is not a rubric id makes its
criterion abstain SILENTLY and can drag the channel below its coverage floor.
`test_zz_meta_every_detector_pairs_with_a_rubric_id` asserts the join in both
directions rather than leaving it to inspection.
"""
import json
import os

import checks

_HERE = os.path.dirname(os.path.abspath(__file__))
_RUBRICS = os.path.join(_HERE, "rubrics.json")


# --------------------------- positive criteria ---------------------------

@pytest.mark.process
def test_R3(traj):
    assert checks.reads_inputs(traj), \
        "never referenced any shipped input under /root/data"


@pytest.mark.process
def test_R4(traj):
    assert checks.writes_solver(traj), \
        "no solver source authored (file write, heredoc, or python -c)"


@pytest.mark.process
def test_R5(traj):
    assert checks.executes_solver(traj), \
        "no python execution found: the consensus was asserted, not computed"


@pytest.mark.process
def test_R6(traj):
    assert checks.median_reduction(traj), \
        "no median-based within-lab reduction found: a spiked replicate is " \
        "free to move its laboratory's value"


@pytest.mark.process
def test_R7(traj):
    assert checks.clamped_irls(traj), \
        "no clamped iterative location/scale estimation found - the consensus " \
        "was not computed by a clamped iteration"


@pytest.mark.process
def test_R8(traj):
    assert checks.beta_debias_at_house_clamp(traj), \
        "CRUX: no beta(c) Fisher-consistency debias found - the scale update " \
        "does not carry the house bias correction (textbook substitute?)"


@pytest.mark.process
def test_R9(traj):
    assert checks.zeta_prime_definition(traj), \
        "no combined uncertainty u = k_U * s / sqrt(n) found: the zeta-prime " \
        "denominator is not the coverage-factored uncertainty"


@pytest.mark.process
def test_R10(traj):
    pair, how = checks.emitted_answer(traj)
    assert checks.reports_contract(traj), \
        f"no finite {' + '.join(checks.ANSWER_KEYS)} on the record ({how})"


# --------------------------- guardrails ---------------------------

@pytest.mark.process
def test_R11(traj):
    pair, how = checks.emitted_answer(traj)
    assert not checks.failure_reports_decoy(traj), (
        f"reported answer {pair} ({how}) lands on the decoy_reference block "
        "question.json labels as not the answer")


@pytest.mark.process
def test_R12(traj):
    assert not checks.failure_network_or_package_install(traj), \
        "network or package-manager attempt in a no-network container"


@pytest.mark.process
def test_R13(traj):
    assert not checks.failure_mutated_input_data(traj), \
        "wrote into, deleted from or edited /root/data in place - this task's " \
        "outcome verifier recomputes from those bytes, so this voids grading"


# --------------------------- meta ---------------------------

@pytest.mark.process
def test_zz_meta_every_detector_pairs_with_a_rubric_id():
    """The junit name join must be exact in both directions.

    score.py pairs a testcase to a criterion by stripping `test_`. A mismatch
    does not error - the criterion simply abstains - so it is asserted here.
    """
    with open(_RUBRICS) as fh:
        spec = json.load(fh)
    rubric_ids = {c["id"] for c in spec["criteria"]
                  if c.get("channel") == "deterministic"}
    detector_ids = set(checks.DETECTORS)
    # `outcome` criteria are pytest too, but they live in their own channel and
    # join to their own rubric ids; both joins are asserted, in both directions.
    outcome_rubric_ids = {c["id"] for c in spec["criteria"]
                          if c.get("channel") == "outcome"}
    all_test_ids = {n[len("test_"):] for n in globals()
                    if n.startswith("test_") and not n.startswith(
                        ("test_zz_", "test_score_", "test_selfcheck_"))}
    outcome_test_ids = {i for i in all_test_ids if i in outcome_rubric_ids}
    test_ids = all_test_ids - outcome_test_ids
    assert outcome_test_ids == outcome_rubric_ids, (
        "outcome test names and outcome rubric ids disagree: "
        "only-in-tests=%s only-in-rubrics=%s"
        % (sorted(outcome_test_ids - outcome_rubric_ids),
           sorted(outcome_rubric_ids - outcome_test_ids)))

    assert detector_ids == rubric_ids, (
        "detector ids and deterministic rubric ids disagree: "
        "only-in-checks=%s only-in-rubrics=%s"
        % (sorted(detector_ids - rubric_ids), sorted(rubric_ids - detector_ids)))
    assert test_ids == rubric_ids, (
        "test names and deterministic rubric ids disagree: "
        "only-in-tests=%s only-in-rubrics=%s"
        % (sorted(test_ids - rubric_ids), sorted(rubric_ids - test_ids)))

    guardrails = {i for i, (_d, g) in checks.DETECTORS.items() if g}
    for crit in spec["criteria"]:
        if crit["id"] in guardrails:
            assert crit["weight"] < 0, \
                "guardrail %s must carry a negative weight" % crit["id"]
        elif crit["channel"] == "deterministic":
            assert crit["weight"] > 0, \
                "positive criterion %s must carry a positive weight" % crit["id"]


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
    """Fingerprint a wrong answer against the bundle's recorded wrong paths, so
    a failure arrives pre-diagnosed instead of merely far away."""
    gaps = outcome["cfg"].get("control_gaps")
    if not isinstance(gaps, dict) or not gaps:
        return ""
    return ("\n  named wrong paths recorded for this task: %s"
            % ", ".join(sorted(gaps)))

_ANSWER_NAME = "results.json"


def _frozen_cases(cfg):
    return {
        "robust_scale": (float(cfg["ref_robust_scale"]),
                         float(cfg["tolerance_robust_scale_abs"])),
        "zeta_prime": (float(cfg["ref_zeta_prime"]),
                       float(cfg["tolerance_zeta_prime_abs"])),
    }


def _submitted_cases(ans, cfg):
    out = {}
    for k in ("robust_scale", "zeta_prime"):
        v = _o_num(_o_dig(ans, k))
        if v is not None:
            out[k] = v
    return out


# ==========================================================================
# OUTCOME CHANNEL + GRADER SELF-CHECKS
# ==========================================================================

"""Outcome tests for the ERZA-RB1 robust-consensus task.

Ground truth is the ERZA-RB1 house method (expected_values.json), NOT the naive
plain-mean / standard-deviation / standard-z summary carried as a decoy in
question.json. Reporting the decoy, reducing each lab by the mean instead of the
median, omitting the beta(c) debias, or using a different clamp all miss at least
one tolerance.

Test (d) is an anti-memorization control: it recomputes the reference on a
bijectively RELABELLED instance (lab IDs permuted, values and the nominated-lab
mapping preserved) and asserts the answer is invariant, documenting that the
reference is procedure-defined rather than tied to instance lab names.
"""
import json
import math
import random
import statistics
from pathlib import Path

import pytest

RESULTS = Path("/root/results.json")
EXPECTED = Path(__file__).parent / "expected_values.json"
MEAS = Path("/root/data/measurements.json")


@pytest.fixture(scope="module")
def cfg():
    return json.loads(EXPECTED.read_text())


@pytest.fixture(scope="module")
def res():
    d = json.loads(RESULTS.read_text())
    assert "robust_scale" in d, "results.json must have key 'robust_scale'"
    assert "zeta_prime" in d, "results.json must have key 'zeta_prime'"
    return {"robust_scale": float(d["robust_scale"]), "zeta_prime": float(d["zeta_prime"])}


# ----------------------- (a) plausibility guards -----------------------
@pytest.mark.selfcheck
def test_selfcheck_plausible(res):
    s = res["robust_scale"]
    z = res["zeta_prime"]
    assert 0.0 < s < 5.0, f"robust_scale {s} outside plausible range"
    assert -20.0 < z < 20.0, f"zeta_prime {z} outside plausible range"


# ----------------------- (b) robust-scale tolerance -----------------------
@pytest.mark.outcome
def test_score_robust_scale(cfg, res):
    ref = float(cfg["ref_robust_scale"])
    tol = float(cfg["tolerance_robust_scale_abs"])
    err = abs(res["robust_scale"] - ref)
    assert err <= tol, f"robust_scale {res['robust_scale']:.6f} off ref {ref:.6f} by {err:.6f} (tol {tol})"


# ----------------------- (c) zeta-prime tolerance -----------------------
@pytest.mark.outcome
def test_score_zeta_prime(cfg, res):
    ref = float(cfg["ref_zeta_prime"])
    tol = float(cfg["tolerance_zeta_prime_abs"])
    err = abs(res["zeta_prime"] - ref)
    assert err <= tol, f"zeta_prime {res['zeta_prime']:.6f} off ref {ref:.6f} by {err:.6f} (tol {tol})"


# ---- ERZA-RB1 recomputation for the isomorphic-invariance control ----
def _phi(z):
    return math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)


def _Phi(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _beta_of_c(c):
    ew2 = (2.0 * _Phi(c) - 1.0) - 2.0 * c * _phi(c) + 2.0 * c * c * (1.0 - _Phi(c))
    return 1.0 / math.sqrt(ew2)


def _erza_rb1(labs, lstar, c=1.25, ufac=1.25):
    lab_val = {k: statistics.median(v) for k, v in labs.items()}
    vals = list(lab_val.values())
    n = len(vals)
    b = _beta_of_c(c)
    m = statistics.median(vals)
    x = m
    s = 1.4826 * statistics.median([abs(v - m) for v in vals])
    for _ in range(60):
        lo, hi = x - c * s, x + c * s
        clamped = [min(max(v, lo), hi) for v in vals]
        xn = sum(clamped) / n
        var = sum((v - xn) ** 2 for v in clamped) / (n - 1)
        sn = b * math.sqrt(var)
        if abs(xn - x) < 1e-12 and abs(sn - s) < 1e-12:
            x, s = xn, sn
            break
        x, s = xn, sn
    u = ufac * s / math.sqrt(n)
    return s, (lab_val[lstar] - x) / u


# ----------------------- (d) IPT isomorphic-invariance control -----------------------
@pytest.mark.selfcheck
def test_selfcheck_isomorphic_invariance(cfg):
    meas = json.loads(MEAS.read_text())
    labs = meas["labs"]
    lstar = cfg["nominated_lab"]

    # reference recomputed directly on the shipped instance
    s0, z0 = _erza_rb1(labs, lstar)

    # bijective relabel: permute lab IDs, preserve values and the L* mapping
    rng = random.Random(4242)
    old = list(labs.keys())
    new = old[:]
    rng.shuffle(new)
    remap = dict(zip(old, new))
    relabelled = {remap[k]: v for k, v in labs.items()}
    s1, z1 = _erza_rb1(relabelled, remap[lstar])

    assert abs(s1 - s0) < 1e-12, f"robust_scale not invariant under relabel: {s0} vs {s1}"
    assert abs(z1 - z0) < 1e-12, f"zeta_prime not invariant under relabel: {z0} vs {z1}"
    # and the invariant recomputation must agree with the shipped reference
    assert abs(s0 - float(cfg["ref_robust_scale"])) <= 5e-6, "recomputed scale disagrees with stored reference"
    assert abs(z0 - float(cfg["ref_zeta_prime"])) <= 5e-6, "recomputed zeta disagrees with stored reference"
