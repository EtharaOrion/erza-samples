"""Print the full per-run breakdown for every scored run in results/.

    python report.py [--results results] [--md]

Reads the `*.score.json` files written by score.py and renders, for each run,
every criterion in both channels with its verdict, plus the channel and final
scores next to the legacy outcome score.
"""
from __future__ import annotations

import argparse
import glob
import json
import os


def mark(row: dict) -> str:
    if row["score"] is None:
        return " -- "
    return " ok " if row["score"] == 1.0 else "FAIL"


def render(path: str, md: bool) -> str:
    with open(path) as f:
        d = json.load(f)
    run = os.path.basename(d["run_dir"])
    arm = os.path.basename(os.path.dirname(d["run_dir"]))
    out = []
    bar = "=" * 78
    out.append(bar)
    out.append(f"RUN: {arm}/{run}")
    out.append(f"  path: {d['run_dir']}")
    out.append(bar)

    for ch, label in (("deterministic", "CHANNEL A - deterministic (pytest over trajectory)"),
                      ("non_deterministic", "CHANNEL B - non-deterministic (LLM judge panel)")):
        c = d[ch]
        s = c["score"]
        out.append("")
        out.append(f"{label}")
        out.append(f"  score {('%.2f%%' % (s * 100)) if s is not None else 'n/a':>8}"
                   f"   ({c['n_scored']}/{c['n_total']} criteria scored,"
                   f" weight total {c['weight_mass_total']:g})")
        out.append("")
        for row in c["criteria"]:
            pol = "" if row["is_positive"] else "  [GUARDRAIL]"
            out.append(f"  [{mark(row)}] w={row['weight']:+d}  {row['id']}{pol}")
            if row.get("detail"):
                out.append(f"           {row['detail']}")
            for r in (row.get("rationales") or [])[:1]:
                out.append(f"           judge: {r[:150]}")

    out.append("")
    out.append("-" * 78)

    def pct(x):
        return "n/a" if x is None else f"{x * 100:.2f}%"

    out.append(f"  deterministic      S_D = {pct(d['deterministic']['score'])}"
               f"   n_D = {d['deterministic']['n_scored']}")
    out.append(f"  non-deterministic  S_N = {pct(d['non_deterministic']['score'])}"
               f"   n_N = {d['non_deterministic']['n_scored']}")
    out.append(f"  FINAL              {pct(d['final_score'])}"
               f"      = {d['final_formula']}")
    if "outcome_score" in d:
        out.append(f"  legacy outcome     {pct(d['outcome_score'])}"
                   f"   pass@1 = {int(d.get('outcome_pass_at_1', 0))}")
    if d.get("abstained"):
        out.append(f"  abstained          {', '.join(d['abstained'])}")
    out.append("-" * 78)
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results")
    args = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(args.results, "*.score.json")))
    if not paths:
        print(f"no *.score.json under {args.results}/")
        return 1

    blocks = [render(p, False) for p in paths]
    print("\n\n".join(blocks))

    print("\n\n" + "=" * 78)
    print("SUMMARY")
    print("=" * 78)
    print(f"{'run':<26}{'S_D':>9}{'S_N':>9}{'FINAL':>9}{'outcome':>10}{'pass@1':>8}")
    print("-" * 78)
    for p in paths:
        with open(p) as f:
            d = json.load(f)
        run = os.path.basename(d["run_dir"])
        arm = os.path.basename(os.path.dirname(d["run_dir"]))

        def pct(x):
            return "n/a" if x is None else f"{x * 100:.1f}%"
        print(f"{arm + '/' + run:<26}"
              f"{pct(d['deterministic']['score']):>9}"
              f"{pct(d['non_deterministic']['score']):>9}"
              f"{pct(d['final_score']):>9}"
              f"{pct(d.get('outcome_score')):>10}"
              f"{int(d.get('outcome_pass_at_1', 0)):>8}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
