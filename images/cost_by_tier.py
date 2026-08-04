"""Mean agent cost per run by difficulty tier, no-skill vs with-skill.

Tiers as in score_by_tier.py. Costs are agent_result.cost_usd means over each
arm's runs in the tier, from the shipped result.json files.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e6e5e1"
C_NOSKILL = "#2a78d6"
C_WITHSKILL = "#eb6834"

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

tiers = ["Trivial", "Easy", "Medium", "Hard", "Expert"]
n = [1, 2, 2, 2, 3]
no_skill = [2.4758, 0.9088, 0.2896, 0.8920, 1.6737]
with_skill = [0.4749, 0.3078, 0.2614, 0.4499, 0.3236]
x = range(5)

fig, ax = plt.subplots(figsize=(10, 5), dpi=140)
ax.plot(x, no_skill, "--", color=C_NOSKILL, linewidth=2, marker="o",
        markersize=9, label="No Skill", zorder=4)
ax.plot(x, with_skill, "--", color=C_WITHSKILL, linewidth=2, marker="s",
        markersize=8, label="With Skill", zorder=4)
for i, v in enumerate(no_skill):
    ax.annotate(f"${v:.2f}", (i, v), textcoords="offset points",
                xytext=(0, 10), ha="center", fontsize=9, color=INK)
for i, v in enumerate(with_skill):
    ax.annotate(f"${v:.2f}", (i, v), textcoords="offset points",
                xytext=(0, -16), ha="center", fontsize=9, color=INK)

ax.set_xticks(list(x), [f"{t}\n(n={k})" for t, k in zip(tiers, n)])
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
fig.savefig("/Users/AgisSpectre/erza-samples/images/cost_by_tier.png",
            bbox_inches="tight")
print("written")
