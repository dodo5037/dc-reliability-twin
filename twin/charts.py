"""Charts for the README and dashboard. Run: python -m twin.charts"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from . import scenarios as S

BLUE, ORANGE, AQUA, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#b4b3ad"
INK, MUTED, SURFACE, GRID = "#0b0b0b", "#52514e", "#fcfcfb", "#e4e3de"
plt.rcParams.update({"font.family": "Helvetica", "font.size": 11, "axes.edgecolor": GRID, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.spines.left": False, "figure.facecolor": SURFACE,
                     "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE, "xtick.color": MUTED, "ytick.color": MUTED,
                     "text.color": INK})


def scenario_chart(path="results/scenarios.png"):
    lines = [(S.crah_failure("N+1", standby_works=True), BLUE, "CRAH fails, standby works"),
             (S.crah_failure("N+1", standby_works=False), ORANGE, "CRAH fails, standby has a hidden fault"),
             (S.utility_loss("N+1", buffer_min=6), AQUA, "Utility loss, 6-minute chilled-water tank"),
             (S.common_mode("2N"), INK, "All chillers trip together (2N)")]
    fig, ax = plt.subplots(figsize=(10, 5.6))
    fig.subplots_adjust(left=0.08, right=0.66, top=0.83, bottom=0.14)
    for o, c, label in lines:
        ax.plot(o.minutes, o.temps, color=c, linewidth=2.4, label=label)
    for y, text in ((27, "27 C recommended limit"), (32, "32 C allowable limit"), (40, "40 C servers shut down (assumed)")):
        ax.axhline(y, color=MUTED, linewidth=0.9, linestyle=(0, (4, 3)))
        ax.text(24.8, y + 0.25, text, fontsize=8.5, color=MUTED, ha="right")
    ax.axvline(2, color=GRID, linewidth=1)
    ax.text(2.2, 23.6, "failure", fontsize=8.5, color=MUTED)
    ax.set_xlim(0, 25)
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False, fontsize=9.5)
    ax.set_ylim(23, 42)
    ax.set_xlabel("Minutes", color=MUTED)
    ax.set_ylabel("Server inlet temperature (C)", color=MUTED)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    fig.text(0.02, 0.965, "Server inlet temperature after four hypothetical failures, 46 C outdoor", fontsize=14, fontweight="bold", va="top")
    fig.text(0.02, 0.915, "1 MW hall, heat balance stepped every 10 seconds. Hypothetical scenarios, not real incidents.", fontsize=10.5, color=MUTED, va="top")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


if __name__ == "__main__":
    print("wrote", scenario_chart())
