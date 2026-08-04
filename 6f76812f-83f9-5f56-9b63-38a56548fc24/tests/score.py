"""Combine the THREE channels into one process score for a run (Stage-6 doctrine).

Per-criterion score is binary and in [0, 1]:

    positive criterion   -> 1 if satisfied, else 0
    guardrail criterion  -> 1 if the failure mode did NOT occur, else 0

so a criterion scoring 1 always means "this run did the right thing", whichever
polarity it has. Guardrails carry their weight as importance (magnitude), not sign.

Channel score is the weight-adjusted mean of its scored criteria (weight-0 rows are
report-only: their verdict is printed and contributes nothing):

    S_channel = sum(|w_i| * s_i) / sum(|w_i|)          -> S_O, S_D, S_N

The channels are blended by WEIGHT MASS, never by criterion count - splitting one
question into three must not move the final score with no run changing:

    W_O = sum(|w_i|) over scored outcome
    W_D = sum(|w_i|) over scored deterministic
    W_N = sum(|w_i|) over scored judged
    final = (W_O*S_O + W_D*S_D + W_N*S_N) / (W_O + W_D + W_N)

Outcome mass stays deliberately modest: the outcome channel's authority is its
gate, not its mass.

Doctrine rules riding on top:

  * TWO GATES, CAPPING IDENTICALLY AT 0.5, and both can fire together:
      - CRUX-FAILED    a gated process (`deterministic`) criterion scored 0 - the run
                       failed the step the task exists to measure;
      - OUTCOME-FAILED a gated `outcome` criterion scored 0 - the final answer is
                       wrong.
    A run that failed either must not print a near-pass. Only deterministic and
    outcome criteria may gate; panel noise disqualifies a judged verdict from a
    verdict-flipping role.
  * COVERAGE FLOOR. If abstentions leave less than two-thirds of a channel's weight
    mass scored, that channel reports INVALID, not a confident partial number.
    Abstentions are excluded from the numerator AND the mass - never scored 0.
  * CONTINUOUS. Reported beside `final` and never merged into it.

The outcome channel is what makes this instrument STANDALONE: its `o_*` pytest
criteria re-derive the run's final answer from the run's own trajectory by probe
re-execution, so `final` no longer depends on the outcome verifier's artifacts.

Every score artifact is version-stamped with the hashes of TRUTH.md, rubrics.json
and the test file: scores under different stamps are not comparable.

Usage:
    python score.py --run-dir <erza run dir> [--junit results/x.xml] \
                    [--judge results/x.judge.json] [--out results/x.score.json]
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.abspath(__file__))
COVERAGE_FLOOR = 2 / 3  # two-thirds of a channel's weight mass must be scored


def load_spec() -> dict:
    with open(os.path.join(ROOT, "rubrics.json")) as f:
        return json.load(f)


def _sha(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except OSError:
        return "missing"


def version_stamp() -> dict:
    return {
        "truth_md": _sha(os.path.join(ROOT, "..", "TRUTH.md")),
        "rubrics_json": _sha(os.path.join(ROOT, "rubrics.json")),
        "test_trajectory_py": _sha(os.path.join(ROOT, "test_pytest.py")),
    }


def read_junit(path: str) -> dict[str, bool]:
    """criterion id -> did the test pass."""
    root = ET.parse(path).getroot()
    out: dict[str, bool] = {}
    for case in root.iter("testcase"):
        name = case.get("name", "")
        if not name.startswith("test_"):
            continue
        cid = name[len("test_"):]
        failed = any(case.find(t) is not None for t in ("failure", "error"))
        if case.find("skipped") is not None:
            continue
        out[cid] = not failed
    return out


def score_channel(rows: list[dict]) -> tuple[float | None, float, float, int]:
    """(score, scored_mass, total_mass, n_scored). total_mass excludes report-only
    (weight 0) rows; a channel is INVALID if scored_mass < 2/3 * total_mass."""
    total_mass = sum(abs(r["weight"]) for r in rows if r["weight"] != 0)
    scored = [r for r in rows if r["score"] is not None and r["weight"] != 0]
    scored_mass = sum(abs(r["weight"]) for r in scored)
    if total_mass == 0 or scored_mass == 0:
        return None, 0.0, total_mass, 0
    if scored_mass < COVERAGE_FLOOR * total_mass:
        return None, scored_mass, total_mass, len(scored)   # INVALID: below floor
    s = sum(abs(r["weight"]) * r["score"] for r in scored) / scored_mass
    return s, scored_mass, total_mass, len(scored)


def _no_graded_work(rows: list[dict]) -> bool:
    """True when this channel's own evidence says the run did NONE of the graded
    work: every positive criterion that got scored scored 0.

    NULL-RUN GUARDRAIL FLOOR. A guardrail prices "did not cheat WHILE working".
    It reads 1 when its failure mode was not observed - and on a run that did
    nothing, no failure mode is observable, so every guardrail reads 1 and the
    run collects the entire guardrail weight mass for free. An empty trajectory
    used to print a double-digit FINAL on that mass alone. With no work there is
    nothing for a guardrail to certify, so on such a run its row is reported and
    then kept out of the channel's numerator AND its mass, exactly the way a
    report-only (weight-0) row is kept out.

    At least one positive must have been SCORED before this fires: positives that
    ABSTAINED are not evidence that the run did nothing, and that case already
    belongs to the coverage floor - scored mass then falls below two-thirds and
    the channel reports INVALID instead of a confident guardrail-only number.
    Weight-0 rows are report-only and are never evidence of work either way.
    """
    positives = [r for r in rows
                 if r["is_positive"] and r["weight"] != 0 and r["score"] is not None]
    return bool(positives) and all(r["score"] == 0.0 for r in positives)


def continuous(run_dir: str) -> tuple[float | None, str]:
    """Outcome metric: arcs correct / total, from the run's own results.json
    against the golden ledger. Outcome cases only, unweighted. No result => INVALID."""
    golden_path = os.path.join(ROOT, "expected_values.json")
    if not os.path.exists(golden_path):
        return None, "INVALID (golden ledger not found)"
    exp = json.load(open(golden_path))
    items = exp.get("items", [])

    found = [p for p in glob.glob(os.path.join(run_dir, "**", "results.json"), recursive=True)
             if "verifier/process" not in p.replace("\\", "/")]
    if not found:
        return None, "INVALID (no outcome result: results.json absent in run dir)"
    try:
        data = json.load(open(sorted(found, key=len)[0]))
    except (OSError, json.JSONDecodeError):
        return None, "INVALID (results.json unreadable)"
    res = data.get("arc_mean_vtec_tecu", data)
    if not isinstance(res, dict) or not items:
        return None, "INVALID (malformed results or empty golden)"

    total = len(items)
    passed = 0
    for it in items:
        block = res.get(it["station_label"])
        if not isinstance(block, dict):
            continue
        try:
            got = float(block[it["sv_label"]])
        except (KeyError, TypeError, ValueError):
            continue
        if abs(got - float(it["ref_arc_mean_vtec_tecu"])) <= float(it["tolerance_tecu"]):
            passed += 1
    return passed / total, f"{passed}/{total} arcs within tolerance"


def _panel_disclosure(jd, run_dir):
    """REQ.9: self-judging seats and single-vendor limitations are disclosed
    beside any judged score.

    A seat drawn from the graded model's own family carries an unmeasured
    self-leniency, and a panel whose seats all come from one vendor shares that
    vendor's blind spots however different its stances read. Neither fact is
    recoverable from the score alone, so it is recorded next to it.
    """
    seats = {}
    for crit in (jd or {}).get("criteria", []) or []:
        for vote in crit.get("votes") or []:
            model = vote.get("model")
            if model:
                seats[model] = vote.get("stance", "")
    graded = os.path.basename(os.path.dirname(os.path.dirname(
        os.path.abspath(run_dir))))

    def family(name):
        return (name or "").split("-")[0]

    vendors = sorted({family(m) for m in seats if m})
    return {
        "seats": [{"model": m, "stance": s} for m, s in sorted(seats.items())],
        "panel_size": len(seats),
        "graded_model": graded,
        "single_vendor": vendors[0] if len(vendors) == 1 else None,
        "self_judging_seats": sorted(m for m in seats
                                     if family(m) and family(m) == family(graded)),
        "stance_is_confounded_with_model": len(seats) == len({s for s in seats.values()}),
        "panels_run": 1,
        "stability_caveat": (
            "One panel per run. The judged channel is a single draw; repeat "
            "panels on this instrument have moved a channel score by ~5 points "
            "and have returned contradictory unanimous verdicts. Do not compare "
            "two runs whose S_N differ by less than that."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--junit", default="")
    ap.add_argument("--judge", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    spec = load_spec()
    det_pass = read_junit(args.junit) if (args.junit and os.path.exists(args.junit)) else {}

    jd: dict = {}
    judge_by_id: dict[str, dict] = {}
    if args.judge and os.path.exists(args.judge):
        with open(args.judge) as f:
            jd = json.load(f)
        judge_by_id = {c["id"]: c for c in jd["criteria"]}

    det_rows, nd_rows, out_rows = [], [], []
    for c in spec["criteria"]:
        row = {
            "id": c["id"],
            "weight": c["weight"],
            "is_positive": c["is_positive"],
            "is_gate": bool(c.get("is_gate", False)),
            "criterion": c["criterion"],
            "score": None,
            "detail": "",
        }
        # outcome and deterministic criteria are both decided by pytest, so
        # both are read out of the junit report; they are kept in
        # SEPARATE channels because they blend as separate weight masses.
        if c["channel"] in ("outcome", "deterministic"):
            if c["id"] in det_pass:
                good = det_pass[c["id"]]   # the test already encodes guardrail polarity
                row["score"] = 1.0 if good else 0.0
                row["detail"] = "ok" if good else (
                    "failure mode occurred" if not c["is_positive"] else "not satisfied"
                )
            else:
                row["detail"] = "no test result"
            (out_rows if c["channel"] == "outcome" else det_rows).append(row)
        else:
            j = judge_by_id.get(c["id"])
            if j and j.get("voted"):
                sat = bool(j["satisfied"])
                # polarity: for a guardrail, satisfied means the bad thing happened
                row["score"] = (1.0 if sat else 0.0) if c["is_positive"] else (
                    0.0 if sat else 1.0
                )
                row["detail"] = f"{j['resolution']} votes={j['votes']}"
                row["rationales"] = j.get("rationales", [])
            else:
                row["detail"] = "abstained (no judge verdict)"
            nd_rows.append(row)

    # ---- NULL-RUN GUARDRAIL FLOOR (see _no_graded_work) ---------------------
    # Guardrail credit is earned only alongside work: with no graded work done,
    # the guardrail rows are still reported but contribute neither score nor mass
    # to the deterministic channel. The outcome channel carries no guardrail rows
    # (its criteria are all positive `o_*`), so the same rule is a no-op there and
    # is not applied; the judged channel is left to the panel.
    det_null_run = _no_graded_work(det_rows)
    det_graded = [r for r in det_rows if r["is_positive"]] if det_null_run else det_rows
    guardrail_floored = [r["id"] for r in det_rows
                         if det_null_run and not r["is_positive"]]

    s_d, wm_d, tot_d, n_d = score_channel(det_graded)
    s_o, wm_o, tot_o, n_o = score_channel(out_rows)
    s_n, wm_n, tot_n, n_n = score_channel(nd_rows)

    d_invalid = s_d is None and any(r["weight"] != 0 for r in det_rows)
    o_invalid = s_o is None and any(r["weight"] != 0 for r in out_rows)
    n_invalid = s_n is None and any(r["weight"] != 0 for r in nd_rows)

    parts = [(s, wm) for s, wm in ((s_o, wm_o), (s_d, wm_d), (s_n, wm_n))
             if s is not None]
    final = (
        sum(s * wm for s, wm in parts) / sum(wm for _s, wm in parts) if parts else None
    )

    # ---- the two gates: CRUX-FAILED and OUTCOME-FAILED, capping identically ----
    # Only deterministic and outcome criteria may gate. Both gates can fire on the
    # same run; the cap is the same 0.5 either way, and each is reported by name.
    failed_gates = [r["id"] for r in det_rows if r["is_gate"] and r["score"] == 0.0]
    failed_outcome_gates = [r["id"] for r in out_rows
                            if r["is_gate"] and r["score"] == 0.0]
    # An UNEVALUATED gate is not a passed gate. A gated criterion that abstained
    # decides nothing, and when its channel then falls below the coverage floor the
    # channel is dropped from the blend - taking the gate away with it and letting
    # the run print a near-pass on the strength of the channels that remain. That is
    # how naming the answer file without ever writing it used to score 1.0: the
    # outcome probe abstained, the outcome channel vanished, and OUTCOME-FAILED
    # never fired. An unevaluated gate is now reported by name and capped exactly
    # like a failed one, because neither is evidence the run cleared it.
    unevaluated_gates = [r["id"] for r in out_rows + det_rows
                         if r["is_gate"] and r["score"] is None]
    crux_failed = bool(failed_gates)
    outcome_failed = bool(failed_outcome_gates)
    gates_unevaluated = bool(unevaluated_gates)
    verdicts = ([] + (["CRUX-FAILED"] if crux_failed else [])
                + (["OUTCOME-FAILED"] if outcome_failed else [])
                + (["GATE-UNEVALUATED"] if gates_unevaluated else []))
    verdict = " + ".join(verdicts) if verdicts else "ok"
    if (crux_failed or outcome_failed or gates_unevaluated) and final is not None:
        final = min(final, 0.5)

    cont, cont_detail = continuous(args.run_dir)

    out = {
        "run_dir": os.path.abspath(args.run_dir),
        "task_id": spec.get("task_id", spec.get("task", "")),
        "version_stamp": version_stamp(),
        "panel_disclosure": _panel_disclosure(jd, args.run_dir),
        "outcome": {
            "score": s_o, "invalid": o_invalid, "n_scored": n_o,
            "n_total": len(out_rows), "weight_mass_scored": wm_o, "weight_mass_total": tot_o,
            "criteria": out_rows,
        },
        "deterministic": {
            "score": s_d, "invalid": d_invalid, "n_scored": n_d,
            "n_total": len(det_rows), "weight_mass_scored": wm_d, "weight_mass_total": tot_d,
            "criteria": det_rows,
        },
        "non_deterministic": {
            "score": s_n, "invalid": n_invalid, "n_scored": n_n,
            "n_total": len(nd_rows), "weight_mass_scored": wm_n, "weight_mass_total": tot_n,
            "criteria": nd_rows,
        },
        "final_score": final,
        "final_formula": "(W_O*S_O + W_D*S_D + W_N*S_N) / (W_O+W_D+W_N), by weight mass; capped at 0.5 by CRUX-FAILED and/or OUTCOME-FAILED",
        "verdict": verdict,
        "crux_failed": crux_failed,
        "outcome_failed": outcome_failed,
        "failed_gates": failed_gates,
        "unevaluated_gates": unevaluated_gates,
        "gates_unevaluated": gates_unevaluated,
        "failed_outcome_gates": failed_outcome_gates,
        "coverage_floor": COVERAGE_FLOOR,
        "continuous": cont,
        "continuous_detail": cont_detail,
        "guardrail_floor_excluded": guardrail_floored,
        "abstained": [r["id"] for r in out_rows + det_rows + nd_rows
                      if r["score"] is None and r["weight"] != 0],
    }

    payload = json.dumps(out, indent=2)
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w") as f:
            f.write(payload + "\n")

    def pct(x):
        return "  n/a " if x is None else f"{x * 100:6.2f}%"

    def chan(score, invalid, wm, tot, n, total):
        if invalid:
            return f"INVALID (coverage floor: {wm:.0f}/{tot:.0f} weight mass < 2/3 scored)"
        return f"{pct(score)}   ({n}/{total} criteria, {wm:.0f}/{tot:.0f} weight mass)"

    print(f"run                : {os.path.basename(os.path.normpath(args.run_dir))}")
    print(f"outcome            : {chan(s_o, o_invalid, wm_o, tot_o, n_o, len(out_rows))}")
    print(f"deterministic      : {chan(s_d, d_invalid, wm_d, tot_d, n_d, len(det_rows))}")
    print(f"non-deterministic  : {chan(s_n, n_invalid, wm_n, tot_n, n_n, len(nd_rows))}")
    if crux_failed:
        print(f"** CRUX-FAILED **  : gated process criterion scored 0 "
              f"({', '.join(failed_gates)}); final capped at {0.5}")
    if outcome_failed:
        print(f"** OUTCOME-FAILED**: the re-derived final answer is wrong "
              f"({', '.join(failed_outcome_gates)}); final capped at {0.5}")
    print(f"FINAL              : {pct(final)}"
          + ("   [CRUX-FAILED, capped 0.5]" if crux_failed else ""))
    if cont is None:
        print(f"CONTINUOUS         : {cont_detail}")
    else:
        print(f"CONTINUOUS         : {pct(cont)}   ({cont_detail})")
    if out["guardrail_floor_excluded"]:
        print("guardrail floor    : no graded deterministic work; guardrails "
              f"excluded from the mean ({', '.join(out['guardrail_floor_excluded'])})")
    if out["abstained"]:
        print(f"abstained          : {', '.join(out['abstained'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
