"""Mean graded-case score by difficulty tier, no-skill vs with-skill.

Tiers binned on unaided mean score A per task (user-fixed cut-points):
Expert A=0 exactly | Hard 0<A<0.3 | Medium 0.3-0.6 | Easy 0.6-0.8 | Trivial >0.8
Scores are graded-cases-passed / total, read from each run's verifier/process.json.
Nothing is hardcoded, so the figure cannot drift from the data.

Usage: uv run --with matplotlib python3 images/score_by_tier.py
"""

import collections
import glob
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e6e5e1"
C_NOSKILL = "#2a78d6"
C_WITHSKILL = "#eb6834"
C_DELTA = "#1baf7a"

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

ROOT = Path(__file__).resolve().parent.parent


def run_score(run_dir):
    """Graded cases passed / total, from the run's structured report."""
    p = Path(run_dir) / "verifier" / "process.json"
    if p.exists():
        outcome = json.loads(p.read_text())["outcome"]
        return outcome["cases_passed"] / outcome["cases_total"]
    # dataset-era record (3c4a9e2d): the outcome verifier's own archived report
    report = json.loads((Path(run_dir) / "verifier" / "outcome_report.json").read_text())
    return report["passed"] / report["total"]


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


# Derived from the shipped runs, not stored: per-task arm means, then tier bins.
per_task = collections.defaultdict(lambda: collections.defaultdict(list))
for run in glob.glob(str(ROOT / "*" / "trajectories" / "*" / "*" / "run_*")):
    parts = Path(run).parts
    per_task[parts[-5]][parts[-2]].append(run_score(run))
arm_mean = {
    t: {c: sum(v) / len(v) for c, v in arms.items()} for t, arms in per_task.items()
}

tiers = ["Trivial", "Easy", "Medium", "Hard", "Expert"]
task_means = {t: [] for t in tiers}
task_means_b = {t: [] for t in tiers}
for t, arms in arm_mean.items():
    a = arms["no-skill"]
    task_means[tier_of(a)].append(a * 100)
    task_means_b[tier_of(a)].append(arms["with-skill"] * 100)

no_skill = [sum(task_means[t]) / len(task_means[t]) for t in tiers]
with_skill = [sum(task_means_b[t]) / len(task_means_b[t]) for t in tiers]
x = range(5)

fig, ax = plt.subplots(figsize=(10, 5), dpi=140)

# delta connectors: one vertical line per tier joining the two arms
for i, (lo, hi) in enumerate(zip(no_skill, with_skill)):
    ax.plot([i, i], [lo, hi], color=C_DELTA, linewidth=2,
            solid_capstyle="butt", zorder=2)
    last = i == len(no_skill) - 1
    ax.annotate(f"Δ +{hi - lo:.0f} pp", (i, (lo + hi) / 2),
                textcoords="offset points",
                xytext=(-8, 0) if last else (8, 0),
                ha="right" if last else "left",
                va="center", fontsize=9, color=INK)

ax.plot(x, with_skill, "--", color=C_WITHSKILL, linewidth=2, marker="s",
        markersize=8, label="With Skill", zorder=4)
ax.plot(x, no_skill, "--", color=C_NOSKILL, linewidth=2, marker="o",
        markersize=9, label="No Skill", zorder=4)

# individual task means, one faint dot per task
for i, t in enumerate(tiers):
    ax.scatter([i] * len(task_means[t]), task_means[t], s=26,
               color=C_NOSKILL, alpha=0.35, linewidths=0, zorder=3)

# direct value labels in ink, offset to clear the marks
for i, v in enumerate(no_skill):
    ax.annotate(f"{v:.0f}%", (i, v), textcoords="offset points",
                xytext=(0, -16), ha="center", fontsize=9, color=INK)
for i, v in enumerate(with_skill):
    ax.annotate(f"{v:.0f}%", (i, v), textcoords="offset points",
                xytext=(0, 9), ha="center", fontsize=9, color=INK)

ax.set_xticks(list(x), [f"{t}\n(n={len(task_means[t])})" for t in tiers])
ax.set_ylim(-6, 112)
ax.set_yticks(range(0, 101, 20))
ax.set_ylabel("Mean Score (%)")
ax.set_xlabel("Difficulty Tier")
ax.set_title("Mean score by difficulty tier (Opus 4.8)",
             fontweight="bold", pad=12)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", color=GRID, linewidth=0.6)
ax.set_axisbelow(True)
ax.legend(loc="lower left", frameon=True, edgecolor=GRID)

fig.tight_layout()
fig.savefig(Path(__file__).resolve().parent / "score_by_tier.png",
            bbox_inches="tight")
print("written")
