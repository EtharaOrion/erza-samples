"""Mean agent cost per run by difficulty tier, no-skill vs with-skill.

Cost comes from agent_result.cost_usd in each run's result.json. The difficulty
tier comes from the unaided mean score computed off verifier/process.json,
using the same cut-points as score_by_tier.py. Nothing is hardcoded, so the
figure cannot drift from the data.

Usage: uv run --with matplotlib python3 images/cost_by_tier.py
"""

import collections
import glob
import json
import os
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent

INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e6e5e1"
C_NOSKILL = "#2a78d6"
C_WITHSKILL = "#eb6834"

ORDER = ["Trivial", "Easy", "Medium", "Hard", "Expert"]

plt.rcParams.update(
    {
        "font.size": 10,
        "text.color": INK,
        "axes.labelcolor": INK,
        "xtick.color": INK2,
        "ytick.color": INK2,
        "axes.edgecolor": GRID,
        "axes.linewidth": 0.8,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)


def run_score(run_dir):
    """Graded cases passed / total, read from the run's structured report.

    The canonical layout ships verifier/process.json, whose `outcome` block
    already separates the graded `cases` from the grader's own `selfchecks`,
    so no name-pattern guard is needed to keep guards out of the denominator.
    """
    report = json.loads((Path(run_dir) / "verifier" / "process.json").read_text())
    outcome = report["outcome"]
    return outcome["cases_passed"] / outcome["cases_total"]


def tier_of(a):
    if a == 0:
        return "Expert"
    if a < 0.3:
        return "Hard"
    if a < 0.6:
        return "Medium"
    if a < 0.8:
        return "Easy"
    return "Trivial"


scores = collections.defaultdict(lambda: collections.defaultdict(list))
costs = collections.defaultdict(lambda: collections.defaultdict(list))
for run in sorted(glob.glob(str(ROOT / "*" / "trajectories" / "*" / "*" / "run_*"))):
    parts = run.split(os.sep)
    task, cond = parts[-5], parts[-2]
    scores[task][cond].append(run_score(run))
    agent = json.loads((Path(run) / "result.json").read_text()).get("agent_result") or {}
    costs[task][cond].append(agent["cost_usd"])

tiers = {t: tier_of(statistics.mean(scores[t]["no-skill"])) for t in scores}
counts = [sum(1 for t in tiers if tiers[t] == tier) for tier in ORDER]
series = {
    cond: [
        statistics.mean(v for t in tiers if tiers[t] == tier for v in costs[t][cond])
        for tier in ORDER
    ]
    for cond in ("no-skill", "with-skill")
}
x = range(len(ORDER))

fig, ax = plt.subplots(figsize=(10, 5), dpi=140)
ax.plot(x, series["no-skill"], "--", color=C_NOSKILL, linewidth=2, marker="o",
        markersize=9, label="No Skill", zorder=4)
ax.plot(x, series["with-skill"], "--", color=C_WITHSKILL, linewidth=2, marker="s",
        markersize=8, label="With Skill", zorder=4)
for i, v in enumerate(series["no-skill"]):
    ax.annotate(f"${v:.2f}", (i, v), textcoords="offset points", xytext=(0, 10),
                ha="center", fontsize=9, color=INK)
for i, v in enumerate(series["with-skill"]):
    ax.annotate(f"${v:.2f}", (i, v), textcoords="offset points", xytext=(0, -16),
                ha="center", fontsize=9, color=INK)

ax.set_xticks(list(x), [f"{t}\n(n={k})" for t, k in zip(ORDER, counts)])
ax.set_ylim(0, 2.9)
ax.set_ylabel("Mean agent cost per run (USD)")
ax.set_xlabel("Difficulty Tier")
ax.set_title("Mean agent cost per run by difficulty tier (Opus 4.8)",
             fontweight="bold", pad=12)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", color=GRID, linewidth=0.6)
ax.set_axisbelow(True)
ax.legend(loc="upper center", frameon=True, edgecolor=GRID)

fig.tight_layout()
fig.savefig(ROOT / "images" / "cost_by_tier.png", bbox_inches="tight")
print(f"wrote cost_by_tier.png  A={series['no-skill']}  B={series['with-skill']}")
