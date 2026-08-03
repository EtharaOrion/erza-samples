"""Negative fixtures: a synthetic run for every deterministic criterion, each SEEN
to fire; plus a correct run proving the positives stay green and the guardrails
stay quiet (Stage-7 false-negative AND guardrail-specificity checks).

A test you have never seen fail is not a test; a guardrail you have never seen
stay quiet under temptation is not a guardrail. This file exercises both halves.

Each fixture is a real Erza run directory (a `trajectory/llm_trajectory.jsonl` in
the shape the normaliser reads), so the whole path - normaliser + detector - runs,
not just the regex.

    python3 verification/negative_fixtures_test.py     # human-readable firing table
    python3 -m pytest verification/negative_fixtures_test.py -q

The benign near-misses at the bottom are not decoration. Four of them are drawn
from behaviour that ACTUALLY OCCURRED in the predecessor task's ten recorded runs and
that an over-eager detector would have charged:

  * two runs print raw-counts `d.min(), d.max()` diagnostics - not a peak-to-peak
    measurement;
  * runs read and discuss a published magnitude for the event - naming one is not
    reporting one, and only a data path into the emitted answer may fire;
  * one run used the epicentral distance directly and PASSED the outcome
    (measured at 0.04x the graded tolerance), so nothing here may fail it;
  * one run could have used the pre-IASPEI Wood-Anderson magnification (0.43x
    tolerance) and would still have passed, so the crux detector must accept it.

Every fixture that stands for a CORRECT chain writes `zeros': [0j, 0j]`. That is not
incidental: the Wood-Anderson acts on displacement and carries two origin zeros, and
the one-zero velocity form -- which the predecessor's oracle, skill, TRUTH.md and this
file's own fixtures all previously carried -- is now the crux negative fixture at
line ~191. It is the only place in this file where a single zero is correct.
"""
import atexit
import json
import os
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PROC = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(PROC, "lib"))
import trajectory as T  # noqa: E402
import checks  # noqa: E402

_TMP: list[str] = []


def _mk(file_writes=(), commands=(), prose="", file_reads=()):
    """Build a synthetic run dir and load it into a normalised Trajectory.

    `file_reads` synthesises read-only tool calls - a `file_path` with no
    `content`. Fixtures that only ever emit write/bash blocks are structurally
    blind to the read tool, which is how a false negative in a "did it open this
    file?" detector survives until it meets a real trajectory.
    """
    blocks = []
    for path, content in file_writes:
        blocks.append({"type": "tool_use", "name": "Write",
                       "input": {"file_path": path, "content": content}})
    for path in file_reads:
        blocks.append({"type": "tool_use", "name": "Read",
                       "input": {"file_path": path}})
    for c in commands:
        blocks.append({"type": "tool_use", "name": "Bash", "input": {"command": c}})
    if prose:
        blocks.append({"type": "text", "text": prose})
    line = {"request": {"body": {"messages": [{"role": "assistant", "content": blocks}]}},
            "response": {"body": {"content": []}}}
    d = tempfile.mkdtemp(prefix="ml-fix-")
    _TMP.append(d)
    os.makedirs(os.path.join(d, "trajectory"))
    with open(os.path.join(d, "trajectory", "llm_trajectory.jsonl"), "w") as f:
        f.write(json.dumps(line) + "\n")
    return T.load(d)


@atexit.register
def _cleanup():
    for d in _TMP:
        shutil.rmtree(d, ignore_errors=True)


# A correct solver: the whole chain, every convention pinned. Every positive
# detector must pass on this and every guardrail must stay quiet. Written as a
# heredoc command, which is how all ten recorded runs author their solver.
CORRECT_SOLVER = """python3 << 'PY'
import json
import numpy as np
from obspy import read, read_inventory, Stream

q = json.load(open('/root/data/question.json'))
st = read('/root/data/waveform.mseed')
inv = read_inventory('/root/data/station.xml')

horiz = [tr for tr in st if tr.stats.channel[-1] in ('N', 'E', '1', '2')]
S = Stream(horiz).copy()
S.detrend('linear'); S.taper(0.05)
S.remove_response(inventory=inv, output='DISP',
                  pre_filt=(0.005, 0.01, 20, 25), water_level=60)

paz_wa = {'sensitivity': 2080.0, 'zeros': [0j, 0j], 'gain': 1.0,
          'poles': [-6.2832 - 4.7124j, -6.2832 + 4.7124j]}
S.simulate(paz_simulate=paz_wa)

amps_mm = [float(np.max(np.abs(tr.data))) * 1000.0 for tr in S]
A = max(amps_mm)

r = np.sqrt(q['epicentral_distance_km']**2 + q['event_depth_km']**2)
logA0 = 1.110 * np.log10(r / 100.0) + 0.00189 * (r - 100.0) + 3.0
ML = float(np.log10(A) + logA0)

json.dump({'local_magnitude_ml': round(ML, 3)}, open('/root/results.json', 'w'))
PY"""


def correct_run():
    return _mk(commands=["cat /root/data/question.json", CORRECT_SOLVER],
               prose="A published magnitude for this event would be an Mw, a different "
                     "quantity; ML must be measured from the record itself. The "
                     "Wood-Anderson acts on displacement, so its paz carries two zeros "
                     "at the origin -- checked by driving it with a 1 mm sinusoid and "
                     "confirming a 2080 mm deflection.")


# ---- one negative fixture per positive deterministic criterion ----
NEGATIVE = {
    # straight into the frequency domain: neither detrended nor tapered before
    # the response removal, the rest of the chain intact
    "R14": lambda: _mk(
        commands=["python3 -c \"\n"
                  "S = st.select(component='N') + st.select(component='E')\n"
                  "S.remove_response(inventory=inv, output='DISP',"
                  " pre_filt=(0.005,0.01,20,25), water_level=60)\n"
                  "S.simulate(paz_simulate=paz_wa)\n"
                  "A = max(float(np.max(np.abs(tr.data)))*1000.0 for tr in S)\n"
                  "ML = np.log10(A) + logA0\n\""]),
    # never opened the shipped inputs: answered from the prose task statement
    "R3": lambda: _mk(
        commands=["python3 -c \"import json; json.dump({'local_magnitude_ml': 4.4},"
                  " open('/root/results.json','w'))\""]),
    # python invoked, but no solver source authored: probes and module runs only.
    # The python invocations are load-bearing - a detector that counted any
    # `python` token as "authored a solver" would pass this.
    "R4": lambda: _mk(
        commands=["cat /root/data/question.json", "ls -la /root/data/",
                  "python3 --version",
                  "python3 -m json.tool /root/data/question.json"]),
    # solver authored but never run
    "R5": lambda: _mk(
        file_writes=[("/root/solve.py", "print('hi')")],
        commands=["cat /root/data/question.json"]),
    # measured the VERTICAL component instead of the horizontals
    "R6": lambda: _mk(
        commands=["python3 -c \"\n"
                  "st = read('/root/data/waveform.mseed')\n"
                  "tr = st.select(channel='HHZ')[0]\n"
                  "tr.remove_response(inventory=inv, output='DISP')\n"
                  "tr.simulate(paz_simulate=paz_wa)\n\""]),
    # deconvolved to VELOCITY: the Wood-Anderson is fed the wrong dimension
    "R7": lambda: _mk(
        commands=["python3 -c \"\n"
                  "horiz = [tr for tr in st if tr.stats.channel[-1] in ('N','E')]\n"
                  "S.remove_response(inventory=inv, output='VEL',"
                  " pre_filt=(0.005,0.01,20,25), water_level=60)\n"
                  "S.simulate(paz_simulate=paz_wa)\n\""]),
    # THE CRUX fixture: response removed, amplitude measured, Wood-Anderson never
    # simulated (the `skip WA` control: |dML| 3.318 = 11.06x tolerance).
    # See also test_wood_anderson_named_but_never_simulated_still_fires below: the
    # harder half of this criterion is a run that WRITES the instrument and never
    # applies it, which is the defect the doctrine's pilot found in its own crux.
    "R8": lambda: _mk(
        commands=["python3 -c \"\n"
                  "horiz = [tr for tr in st if tr.stats.channel[-1] in ('N','E')]\n"
                  "S.detrend('linear'); S.taper(0.05)\n"
                  "S.remove_response(inventory=inv, output='DISP',"
                  " pre_filt=(0.005,0.01,20,25), water_level=60)\n"
                  "A = max(float(np.max(np.abs(tr.data)))*1000.0 for tr in S)\n"
                  "logA0 = 1.110*np.log10(r/100.0) + 0.00189*(r-100.0) + 3.0\n"
                  "ML = np.log10(A) + logA0\n\""]),
    # amplitude left in METRES: the mm conversion never happens (10.00x tolerance)
    "R9": lambda: _mk(
        commands=["python3 -c \"\n"
                  "S.simulate(paz_simulate=paz_wa)\n"
                  "A = max(float(np.max(np.abs(tr.data))) for tr in S)\n"
                  "ML = np.log10(A) + logA0\n\""]),
    # the log-distance term dropped: the correction keeps only the linear term and
    # the 100-km reference constant (2.09x tolerance)
    "R10": lambda: _mk(
        commands=["python3 -c \"\n"
                  "logA0 = 0.00189*(r - 100.0) + 3.0\n"
                  "ML = np.log10(A_mm) + logA0\n\""]),
    # no log10: the magnitude relation was never formed
    "R11": lambda: _mk(
        commands=["python3 -c \"\n"
                  "A_mm = max(float(np.max(np.abs(tr.data)))*1000.0 for tr in S)\n"
                  "answer = A_mm / 35.0\n\""]),
    # right chain, wrong output contract: a differently-named key
    "R12": lambda: _mk(
        commands=[CORRECT_SOLVER.replace("local_magnitude_ml", "ml")
                                .replace("/root/results.json", "/root/out.txt")]),
    # THE CRUX: a single origin zero -- the VELOCITY response -- on a displacement
    # input. Understates the amplitude by |2*pi*f| = 2.654x the graded tolerance.
    "R13": lambda: _mk(
        commands=["python3 -c \"\n"
                  "wa = {'poles':[-6.283185-4.712389j, -6.283185+4.712389j],\n"
                  "      'zeros':[0+0j], 'gain':1.0, 'sensitivity':2080.0}\n"
                  "tr.remove_response(inventory=inv, output='DISP')\n"
                  "tr.simulate(paz_simulate=wa)\n\""]),
}

# ---- one failure fixture per guardrail (the failure mode DID occur) ----
GUARDRAIL_FAIL = {
    # A catalogue magnitude RECALLED and emitted as the answer. question.json no
    # longer carries the field, so the failure mode is now recall rather than copy --
    # and it is graded -5 precisely because the outcome verifier cannot see it: the
    # catalogue Mw sits 0.107x tolerance from the true ML, so this run scores 1.
    "R15": lambda: _mk(
        commands=["python3 -c \"\n"
                  "ml = 5.25   # catalogue Mw for this event\n"
                  "json.dump({'local_magnitude_ml': ml},"
                  " open('/root/results.json','w'))\n\""],
        prose="This is the well-known M5.25 Salton Sea event; I will report the "
              "catalogue magnitude."),
    # peak-to-peak swing used as the amplitude, unhalved (1.00x tolerance)
    "R16": lambda: _mk(
        commands=["python3 -c \"\n"
                  "S.simulate(paz_simulate=paz_wa)\n"
                  "A = max(float(np.ptp(tr.data))*1000.0 for tr in S)\n"
                  "ML = np.log10(A) + logA0\n\""]),
    # the shipped record edited in place
    "R17": lambda: _mk(
        commands=["sed -i 's/26.552/12.0/' /root/data/question.json",
                  CORRECT_SOLVER]),
    # network / package install in a no-network container
    "R18": lambda: _mk(
        commands=["pip install obspy", CORRECT_SOLVER]),
}


@pytest.mark.parametrize("cid", list(NEGATIVE))
def test_positive_detector_fires_on_negative_fixture(cid):
    traj = NEGATIVE[cid]()
    detector = checks.DETECTORS[cid][0]
    assert detector(traj) is False, \
        f"{cid}: detector did NOT fire on its negative fixture (false negative)"


@pytest.mark.parametrize("cid", list(GUARDRAIL_FAIL))
def test_guardrail_fires_on_failure_fixture(cid):
    traj = GUARDRAIL_FAIL[cid]()
    detector = checks.DETECTORS[cid][0]
    assert detector(traj) is True, \
        f"{cid}: guardrail did NOT detect the failure mode it names"


def test_every_criterion_has_a_fixture():
    """No detector may ship unbound. Positives need a negative fixture, guardrails
    need a failure fixture."""
    for cid, (_det, is_guard) in checks.DETECTORS.items():
        bound = GUARDRAIL_FAIL if is_guard else NEGATIVE
        assert cid in bound, f"{cid}: no fixture binds this detector"


def test_correct_run_positives_all_green():
    traj = correct_run()
    for cid, (det, is_guard) in checks.DETECTORS.items():
        if not is_guard:
            assert det(traj) is True, f"{cid}: false negative on a fully correct run"


def test_guardrails_quiet_on_correct_run():
    traj = correct_run()
    for cid, (det, is_guard) in checks.DETECTORS.items():
        if is_guard:
            assert det(traj) is False, f"{cid}: guardrail fired on a correct run"


# ---- benign near-misses: behaviour adjacent to a failure mode, but innocent ----

def test_naming_the_catalogue_magnitude_in_prose_stays_quiet():
    """RECALLING a published magnitude and saying so is not reporting it.

    A capable run may well recognise the event and know a catalogue magnitude for it.
    Saying "the catalogue Mw is about 5.25, which is a different quantity, so I will
    measure ML" is exactly the reasoning the task wants. Only a data path from that
    value into the emitted answer is the failure mode.
    """
    traj = _mk(commands=["cat /root/data/question.json", CORRECT_SOLVER],
               prose="I recognise this as the June 2021 Salton Sea event, catalogue "
                     "magnitude about 5.25 Mw. That is a moment magnitude, not ML, and "
                     "it was not measured from this record; I will compute ML properly "
                     "and not assume the two agree.")
    assert checks.failure_reports_catalog_magnitude(traj) is False, (
        "merely naming/discussing a recalled catalogue magnitude was charged as "
        "reporting it")


def test_catalogue_value_reaching_the_answer_still_fires():
    """The same value in the other direction - into the emitted key - must fire.

    This is the -5 case: the outcome verifier grades this run 1, because the catalogue
    Mw is 0.107x tolerance from the true ML. Only this guardrail can see that nothing
    was measured.
    """
    traj = _mk(commands=["python3 -c \"json.dump({'local_magnitude_ml': 5.25},"
                         " open('/root/results.json','w'))\""])
    assert checks.failure_reports_catalog_magnitude(traj) is True, \
        "the catalogue value emitted as the answer was not detected"


def test_raw_counts_min_max_diagnostic_stays_quiet():
    """`d.min(), d.max()` printed as a raw-counts diagnostic is not a peak-to-peak
    amplitude measurement.

    Two recorded runs do exactly this while measuring correctly with
    np.max(np.abs(...)); one of them prints the literal string "min/max counts:".
    A guardrail matching any min/max token would have charged both.
    """
    traj = _mk(commands=[CORRECT_SOLVER,
                         "python3 -c \"\n"
                         "for tr in st:\n"
                         "    d = tr.data\n"
                         "    print(tr.id, 'min/max counts:', d.min(), d.max(),"
                         " 'n at max:', np.sum(d==d.max()))\n\""])
    assert checks.failure_peak_to_peak_amplitude(traj) is False, \
        "a raw-counts min/max diagnostic was charged as a peak-to-peak measurement"


def test_halved_peak_to_peak_stays_quiet():
    """A peak-to-peak swing that IS halved recovers the zero-to-peak amplitude and
    is arithmetically identical to the oracle's route on a symmetric trace."""
    traj = _mk(commands=["python3 -c \"\n"
                         "S.simulate(paz_simulate=paz_wa)\n"
                         "A = max(float(np.ptp(tr.data)) / 2.0 * 1000.0 for tr in S)\n"
                         "ML = np.log10(A) + logA0\n\""])
    assert checks.failure_peak_to_peak_amplitude(traj) is False, \
        "a correctly halved peak-to-peak swing was charged as an unhalved one"


def test_read_direction_copy_of_inputs_stays_quiet():
    """`cp /root/data/x /tmp/` takes the inputs OUT and mutates nothing.

    This is the defect the doctrine names explicitly. A mutation guardrail matching
    any cp/mv/rm token near the data path would charge a correct run this suite's
    heaviest penalty. No recorded run happened to copy the inputs out, so only a
    fixture can catch it.
    """
    traj = _mk(commands=["cp /root/data/question.json /tmp/q.json",
                         "cp -r /root/data /tmp/snapshot",
                         CORRECT_SOLVER])
    assert checks.failure_mutated_input_data(traj) is False, \
        "read-direction copy of the inputs OUT was charged as a mutation"


def test_copy_into_data_dir_still_fires():
    """The same verb in the other direction is a real mutation and must fire."""
    traj = _mk(commands=["cp /tmp/forged.mseed /root/data/waveform.mseed",
                         CORRECT_SOLVER])
    assert checks.failure_mutated_input_data(traj) is True, \
        "copy INTO the input directory was not detected as a mutation"


def test_version_probe_is_not_a_package_install():
    """`python3 -c 'import obspy; print(obspy.__version__)'` and `pip list` are
    probes, not installs. Every recorded run opens with exactly such a probe."""
    traj = _mk(commands=["python3 -c \"import obspy; print('obspy', obspy.__version__)\"",
                         "pip list", "pip show obspy", CORRECT_SOLVER])
    assert checks.failure_network_or_package_install(traj) is False, \
        "a version probe was charged as a package install"


def test_inputs_opened_with_the_read_tool_count_as_read():
    """Opening the shipped inputs with a read-only tool is reading them.

    This is the regression `Trajectory.tool_surface` exists for. A Read call
    carries a `file_path` and no `content`, so it is invisible to both
    `file_writes` and `commands`; a detector grepping `agent_code` alone reports a
    false negative on every run that used the read tool.
    """
    traj = _mk(file_reads=["/root/data/question.json", "/root/data/station.xml"],
               commands=["python3 -c \"x = 1\""])
    assert "question.json" not in traj.agent_code, \
        "fixture no longer exercises the read-only path"
    assert checks.reads_inputs(traj) is True, \
        "inputs opened via the read tool were scored as never read"


def test_results_written_with_the_write_tool_counts_as_reporting():
    """Three recorded runs emit /root/results.json with a write tool: the PATH is
    in the tool input and the KEY is in the written content, so neither appears in
    `commands`. Both halves must be found on the tool surface."""
    traj = _mk(file_writes=[("/root/results.json", '{"local_magnitude_ml": 4.42}\n')],
               commands=[CORRECT_SOLVER.replace(
                   "json.dump({'local_magnitude_ml': round(ML, 3)},"
                   " open('/root/results.json', 'w'))", "print(ML)")])
    assert checks.reports_contract(traj) is True, \
        "a results file emitted with the write tool was scored as never emitted"


def test_pre_iaspei_magnification_2800_still_passes_the_crux():
    """Measured at 0.43x the graded tolerance: a run on the pre-IASPEI Wood-Anderson
    magnification still lands inside tolerance, so the crux detector must accept
    it. Weighting a NOT-outcome-breaking lever as a failure is exactly the
    over-reading TRUTH.md Step 4 cautions against.

    The magnification is the SOLE Wood-Anderson evidence here: the poles are
    derived from the free period and damping rather than written as literals, the
    instrument is never named, and the conventional `paz_wa` identifier is not
    used. Without that isolation the fixture is vacuous - an earlier version also
    spelled the literal pole pair, so a detector accepting only 2080 still passed
    it, and a mutation run proved the fixture was not load-bearing.
    """
    traj = _mk(commands=["python3 -c \"\n"
                         "w0 = 2.0*np.pi/0.8\n"
                         "h = 0.7\n"
                         "poles = [-h*w0 - 1j*w0*np.sqrt(1-h**2),\n"
                         "         -h*w0 + 1j*w0*np.sqrt(1-h**2)]\n"
                         "paz = {'sensitivity': 2800.0, 'zeros': [0j, 0j],"
                         " 'gain': 1.0, 'poles': poles}\n"
                         "S.simulate(paz_simulate=paz)\n\""])
    assert not any(tok in traj.agent_code for tok in ("2080", "6.2832", "4.7124")), \
        "fixture no longer isolates the magnification"
    assert checks.wood_anderson_simulation(traj) is True, \
        "the pre-IASPEI magnification was scored as no Wood-Anderson simulation"


def test_wood_anderson_named_but_never_simulated_still_fires():
    """Writing the Wood-Anderson paz is not simulating with it.

    This is the crux detector's dangerous half, and it is the same shape as the
    defect the doctrine's own pilot found in ITS most important test: a run that
    merely NAMES the thing passing a check that was supposed to prove it did it.
    Here the run defines `paz_wa` with the IASPEI magnification and the correct
    pole pair, then measures the response-removed displacement directly - the
    11.06x-tolerance failure mode wearing the crux's vocabulary.
    """
    traj = _mk(commands=["python3 -c \"\n"
                         "paz_wa = {'sensitivity': 2080.0, 'zeros': [0j, 0j],"
                         " 'gain': 1.0,\n"
                         "          'poles': [-6.2832-4.7124j, -6.2832+4.7124j]}"
                         "  # Wood-Anderson\n"
                         "S.remove_response(inventory=inv, output='DISP',"
                         " pre_filt=(0.005,0.01,20,25), water_level=60)\n"
                         "A = max(float(np.max(np.abs(tr.data)))*1000.0 for tr in S)\n"
                         "ML = np.log10(A) + logA0\n\""])
    assert "paz_wa" in traj.agent_code and "2080" in traj.agent_code, \
        "fixture no longer carries the crux vocabulary"
    assert checks.wood_anderson_simulation(traj) is False, \
        "naming the Wood-Anderson paz was accepted as having simulated with it"


def test_wood_anderson_mentioned_only_in_a_comment_still_fires():
    """A comment naming the instrument cannot stand in for code applying it.

    This binds the comment strip in `checks._code`. Here the run DOES call
    `simulate`, so the simulation half of the crux detector is satisfied - but the
    only Wood-Anderson evidence (the name and the magnification) lives in a `#`
    comment, while the paz actually applied is a different instrument. Without the
    strip the detector would score this run as having simulated a Wood-Anderson.
    """
    traj = _mk(commands=["python3 -c \"\n"
                         "# Wood-Anderson, IASPEI sensitivity 2080, T0=0.8s\n"
                         "paz = {'sensitivity': 1.0, 'zeros': [0j, 0j], 'gain': 1.0,\n"
                         "       'poles': [-4.44-4.44j, -4.44+4.44j]}\n"
                         "S.simulate(paz_simulate=paz)\n\""])
    assert "2080" in traj.agent_code and "Wood-Anderson" in traj.agent_code, \
        "fixture no longer puts the crux vocabulary in a comment"
    assert checks.wood_anderson_simulation(traj) is False, \
        "a commented-out mention of the Wood-Anderson was accepted as simulating one"


def test_dropping_only_the_linear_distance_term_stays_green():
    """Measured at 0.46x the graded tolerance, holding the golden amplitude fixed:
    a correction that keeps the log-distance term and drops the small linear one
    still lands inside tolerance, so the criterion must not fail it.

    This is why R10 requires the log-distance coefficient
    only. An earlier version demanded both, and a mutation run against this suite
    showed nothing would have caught the over-reading.
    """
    traj = _mk(commands=["python3 -c \"\n"
                         "logA0 = 1.110*np.log10(r/100.0) + 3.0\n"
                         "ML = np.log10(A_mm) + logA0\n\""])
    assert "0.00189" not in traj.agent_code, \
        "fixture no longer isolates the linear term"
    assert checks.hutton_boore_correction(traj) is True, \
        "dropping the linear distance term (0.46x tolerance) was charged as a failure"


def test_derived_poles_without_any_magnification_still_passes_the_crux():
    """The other isolation of the same alternation: a run that spells the pole pair
    as literals and never writes a magnification at all (obspy applies the paz as
    given) must still count as having simulated the Wood-Anderson."""
    traj = _mk(commands=["python3 -c \"\n"
                         "paz = {'zeros': [0j, 0j], 'gain': 1.0,\n"
                         "       'poles': [-6.2832-4.7124j, -6.2832+4.7124j]}\n"
                         "S.simulate(paz_simulate=paz)\n\""])
    assert "2080" not in traj.agent_code and "2800" not in traj.agent_code, \
        "fixture no longer isolates the pole-pair spelling"
    assert checks.wood_anderson_simulation(traj) is True, \
        "a Wood-Anderson identified only by its pole pair was scored as no simulation"


def test_epicentral_distance_fails_no_criterion():
    """Measured at 0.04x the graded tolerance. One recorded no-skill run used the
    epicentral distance directly and PASSED the outcome. There is no
    hypocentral-distance criterion, and no other detector may fail such a run."""
    traj = _mk(commands=["cat /root/data/question.json",
                         "python3 -c \"\n"
                         "import numpy as np, json\n"
                         "from obspy import read, read_inventory\n"
                         "st = read('/root/data/waveform.mseed')\n"
                         "inv = read_inventory('/root/data/station.xml')\n"
                         "r = 26.552\n"
                         "paz_wa = {'poles':[-6.283185-4.712389j,"
                         " -6.283185+4.712389j],\n"
                         "          'zeros':[0j, 0j], 'gain':1.0, 'sensitivity':2080}\n"
                         "amps = {}\n"
                         "for ch in ['HHE','HHN']:\n"
                         "    tr = st.select(channel=ch)[0].copy()\n"
                         "    tr.detrend('linear'); tr.taper(0.05)\n"
                         "    tr.remove_response(inventory=inv, output='DISP',"
                         " pre_filt=[0.01,0.02,18,20])\n"
                         "    tr.simulate(paz_simulate=paz_wa)\n"
                         "    amps[ch] = np.max(np.abs(tr.data * 1000.0))\n"
                         "logA0 = 1.110*np.log10(r/100.0) + 0.00189*(r-100.0) + 3.0\n"
                         "ML = np.log10(max(amps.values())) + logA0\n"
                         "json.dump({'local_magnitude_ml': round(ML,2)},"
                         " open('/root/results.json','w'))\n\""])
    for cid, (det, is_guard) in checks.DETECTORS.items():
        if is_guard:
            assert det(traj) is False, \
                f"{cid}: guardrail fired on a run that used the epicentral distance"
        else:
            assert det(traj) is True, \
                f"{cid}: failed a run that used the epicentral distance and PASSED " \
                f"the outcome (0.04x tolerance)"


def test_averaging_the_horizontals_fails_no_criterion():
    """Three of the four passing no-skill runs averaged the two horizontals (or the
    two per-component magnitudes) instead of taking the maximum, and all three
    passed. The amplitude criterion is deliberately silent on the combination
    rule."""
    traj = _mk(commands=["cat /root/data/question.json",
                         "python3 -c \"\n"
                         "import numpy as np, json\n"
                         "from obspy import read, read_inventory\n"
                         "st = read('/root/data/waveform.mseed')\n"
                         "inv = read_inventory('/root/data/station.xml')\n"
                         "q = json.load(open('/root/data/question.json'))\n"
                         "r = np.sqrt(q['epicentral_distance_km']**2"
                         " + q['event_depth_km']**2)\n"
                         "paz_wa = {'poles':[-6.2832-4.7124j, -6.2832+4.7124j],\n"
                         "          'zeros':[0j, 0j], 'gain':1.0, 'sensitivity':2080.0}\n"
                         "mls = []\n"
                         "for ch in ['HHN','HHE']:\n"
                         "    tr = st.select(channel=ch)[0].copy()\n"
                         "    tr.detrend('linear'); tr.taper(0.05)\n"
                         "    tr.remove_response(inventory=inv, output='DISP',"
                         " pre_filt=(0.005,0.01,20,25), water_level=60)\n"
                         "    tr.simulate(paz_simulate=paz_wa)\n"
                         "    A = np.max(np.abs(tr.data)) * 1000.0\n"
                         "    logA0 = 1.110*np.log10(r/100.0) + 0.00189*(r-100.0) + 3.0\n"
                         "    mls.append(np.log10(A) + logA0)\n"
                         "ML = float(np.mean(mls))\n"
                         "json.dump({'local_magnitude_ml': round(ML,2)},"
                         " open('/root/results.json','w'))\n\""])
    for cid, (det, is_guard) in checks.DETECTORS.items():
        if is_guard:
            assert det(traj) is False, \
                f"{cid}: guardrail fired on a run that averaged the horizontals"
        else:
            assert det(traj) is True, \
                f"{cid}: failed a run that averaged the horizontals and PASSED " \
                f"the outcome"


def main():
    print("negative fixtures - every deterministic criterion SEEN to fire:\n")
    ok = True
    for cid in NEGATIVE:
        fired = checks.DETECTORS[cid][0](NEGATIVE[cid]()) is False
        ok &= fired
        print(f"  {cid:<32} test FIRES on its negative fixture   {'OK' if fired else 'MISS'}")
    for cid in GUARDRAIL_FAIL:
        fired = checks.DETECTORS[cid][0](GUARDRAIL_FAIL[cid]()) is True
        ok &= fired
        print(f"  {cid:<32} guardrail DETECTS the failure mode   {'OK' if fired else 'MISS'}")
    traj = correct_run()
    pos_ok = all(d(traj) for _c, (d, g) in checks.DETECTORS.items() if not g)
    guard_quiet = all(not d(traj) for _c, (d, g) in checks.DETECTORS.items() if g)
    ok &= pos_ok and guard_quiet
    print("\ncorrect run - positives green, guardrails quiet:")
    print(f"  positives all satisfied on correct run              {'OK' if pos_ok else 'MISS'}")
    print(f"  guardrails stay quiet on correct run                {'OK' if guard_quiet else 'MISS'}")

    print("\nbenign near-misses - adjacent behaviour that must NOT be charged:")
    near = [
        ("naming the catalogue magnitude in prose",
         lambda: checks.failure_reports_catalog_magnitude(
             _mk(commands=[CORRECT_SOLVER, "cat /root/data/question.json"],
                 prose="the catalogue magnitude for this event is about 5.25 mw, "
                       "a different quantity from ML")
         ) is False),
        ("raw-counts min/max diagnostic",
         lambda: checks.failure_peak_to_peak_amplitude(
             _mk(commands=[CORRECT_SOLVER,
                           "python3 -c \"print(tr.id, 'min/max counts:',"
                           " d.min(), d.max())\""])) is False),
        ("halved peak-to-peak swing",
         lambda: checks.failure_peak_to_peak_amplitude(
             _mk(commands=["python3 -c \"A = np.ptp(tr.data) / 2.0 * 1000.0\""])) is False),
        ("read-direction copy of the inputs OUT",
         lambda: checks.failure_mutated_input_data(
             _mk(commands=["cp /root/data/question.json /tmp/q.json",
                           CORRECT_SOLVER])) is False),
        ("version probe, not a package install",
         lambda: checks.failure_network_or_package_install(
             _mk(commands=["python3 -c \"import obspy; print(obspy.__version__)\"",
                           "pip list"])) is False),
        ("inputs opened with the read-only tool",
         lambda: checks.reads_inputs(
             _mk(file_reads=["/root/data/question.json"],
                 commands=["python3 -c \"x=1\""])) is True),
        ("results emitted with the write tool",
         lambda: checks.reports_contract(
             _mk(file_writes=[("/root/results.json",
                               '{"local_magnitude_ml": 4.42}')],
                 commands=["python3 -c \"print(ML)\""])) is True),
        ("pre-IASPEI magnification 2800, sole WA evidence (0.43x tol)",
         lambda: checks.wood_anderson_simulation(
             _mk(commands=["python3 -c \"w0 = 2.0*np.pi/0.8; h = 0.7\n"
                           "poles = [-h*w0 - 1j*w0*np.sqrt(1-h**2),"
                           " -h*w0 + 1j*w0*np.sqrt(1-h**2)]\n"
                           "paz = {'sensitivity': 2800.0, 'zeros': [0j, 0j],"
                           " 'gain': 1.0, 'poles': poles}\n"
                           "S.simulate(paz_simulate=paz)\""])) is True),
        ("pole pair as sole WA evidence, no magnification written",
         lambda: checks.wood_anderson_simulation(
             _mk(commands=["python3 -c \"paz = {'zeros': [0j, 0j], 'gain': 1.0,"
                           " 'poles': [-6.2832-4.7124j, -6.2832+4.7124j]}\n"
                           "S.simulate(paz_simulate=paz)\""])) is True),
        ("linear distance term dropped, log term kept (0.46x tol)",
         lambda: checks.hutton_boore_correction(
             _mk(commands=["python3 -c \"logA0 = 1.110*np.log10(r/100.0)"
                           " + 3.0\""])) is True),
        ("WA paz written but simulate never called -> MUST fire",
         lambda: checks.wood_anderson_simulation(
             _mk(commands=["python3 -c \"paz_wa = {'sensitivity': 2080.0,"
                           " 'zeros': [0j, 0j], 'gain': 1.0, 'poles':"
                           " [-6.2832-4.7124j, -6.2832+4.7124j]}\n"
                           "A = max(np.max(np.abs(tr.data))*1000.0 for tr in S)\""])
         ) is False),
        ("WA named only in a comment -> MUST fire",
         lambda: checks.wood_anderson_simulation(
             _mk(commands=["python3 -c \"# Wood-Anderson, sensitivity 2080\n"
                           "paz = {'sensitivity': 1.0, 'zeros': [0j, 0j], 'gain': 1.0,"
                           " 'poles': [-4.44-4.44j, -4.44+4.44j]}\n"
                           "S.simulate(paz_simulate=paz)\""])) is False),
        ("python invoked but no solver authored -> MUST fire",
         lambda: checks.writes_solver(
             _mk(commands=["python3 --version",
                           "python3 -m json.tool /root/data/question.json"])) is False),
    ]
    for label, fn in near:
        good = fn()
        ok &= good
        print(f"  {label:<48} {'OK' if good else 'MISS'}")

    print(f"\nALL FIXTURES BEHAVE AS SPECIFIED : {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())


def test_comparing_the_result_against_a_recalled_catalogue_value_stays_quiet():
    """Printing or comparing against 5.25 is not binding the answer to it.

    Pins the specificity claim that lets failure_reports_catalog_magnitude drop its
    catalogue-naming requirement: the detector keys on an ASSIGNMENT of the literal to
    a magnitude variable, so a run that measures properly and then sanity-checks its
    answer against a recalled catalogue value -- good practice, and explicitly invited
    by TRUTH.md Step 8 -- must not be charged.
    """
    traj = _mk(commands=[CORRECT_SOLVER,
                         "python3 -c \"\n"
                         "print('measured', ML, 'vs recalled catalogue 5.25',"
                         " abs(ML - 5.25))\n\""],
               prose="I recall a catalogue magnitude near 5.25 Mw for this event. "
                     "That is a different quantity and I am not reporting it; I note "
                     "the comparison only to see whether my measurement is sane.")
    assert checks.failure_reports_catalog_magnitude(traj) is False, \
        "comparing against a recalled catalogue value was charged as reporting it"
