"""Why the settling algorithm is right on muddy fills and wrong on clear ones.
Data read straight out of the reports' embedded workflow.json."""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pypdf import PdfReader

D = "/home/nidwe72/development/spectracs/spectracs-references/tmp/2026ß817LigitschA"
ORANGE, RED, BLUE, INK, MUTED = "#e08000", "#b0544e", "#2b6cb0", "#2c2c2c", "#6b7280"

def record(n):
    return json.loads(PdfReader(os.path.join(D, n + ".pdf")).attachments["workflow.json"][0])["monitorRecord"]

def style(ax, title, xlabel, ylabel):
    ax.set_title(title, fontsize=11, fontweight="bold", color=INK, loc="left", pad=10)
    ax.set_xlabel(xlabel, fontsize=9, color=MUTED)
    ax.set_ylabel(ylabel, fontsize=9, color=MUTED)
    ax.tick_params(labelsize=8, colors=MUTED)
    ax.grid(True, alpha=0.22, linewidth=0.5)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#d4d4d4")

fig, axes = plt.subplots(2, 2, figsize=(13.0, 8.8))
fig.patch.set_facecolor("#fcfcfb")
for ax in axes.flat:
    ax.set_facecolor("#fcfcfb")

# --- 1 · the branch that works -------------------------------------------------
r = record("006"); t = [x["t"] for x in r["rows"]]; q = [x["qPercent"] for x in r["rows"]]
ax = axes[0][0]
ax.plot(t, q, color=ORANGE, lw=2, marker="o", markersize=4, zorder=3)
early = min(r["rows"], key=lambda x: abs(x["t"] - 105.0))
ax.plot([early["t"]], [early["qPercent"]], marker="X", markersize=13, color=RED, zorder=5,
        markeredgecolor="white", markeredgewidth=1.5)
ax.annotate("a fixed-time read at 105 s\nwould have said  15.005", xy=(early["t"], early["qPercent"]),
            xytext=(150, 18.2), fontsize=9, color=INK,
            arrowprops=dict(arrowstyle="-", color=MUTED, lw=1))
a = r["answer"]
ax.plot([a["t"]], [a["value"]], marker="o", markersize=11, color=BLUE, zorder=5,
        markeredgecolor="white", markeredgewidth=1.5)
ax.annotate("the gate waited and said  13.990", xy=(a["t"], a["value"]), xytext=(120, 15.6),
            fontsize=9, color=INK, arrowprops=dict(arrowstyle="-", color=MUTED, lw=1))
guide = max(t) + 55
for level in (early["qPercent"], a["value"]):
    ax.plot([early["t"] if level == early["qPercent"] else a["t"], guide - 18], [level, level],
            color="#c9ccd1", lw=1, ls=(0, (4, 3)), zorder=1)
ax.annotate("", xy=(guide - 12, a["value"]), xytext=(guide - 12, early["qPercent"]),
            arrowprops=dict(arrowstyle="<->", color=INK, lw=1.6))
ax.text(guide - 4, (a["value"] + early["qPercent"]) / 2, "1.015\nunits", fontsize=10,
        color=INK, fontweight="bold", va="center")
ax.set_xlim(-15, guide + 42)
style(ax, "1 · THE BRANCH THAT WORKS — a muddy fill (006)", "seconds since the fill went in", "Q%")

# --- 2 · the branch that doesn't ----------------------------------------------
r3 = record("003"); t3 = [x["t"] for x in r3["rows"]]; q3 = [x["qPercent"] for x in r3["rows"]]
ax = axes[0][1]
ax.plot(t3, q3, color=ORANGE, lw=2, marker="o", markersize=5, zorder=3)
ax.plot([t3[-1]], [q3[-1]], marker="X", markersize=13, color=RED, zorder=5,
        markeredgecolor="white", markeredgewidth=1.5)
ax.annotate("what it REPORTED\n(the last look)  14.246", xy=(t3[-1], q3[-1]), xytext=(30, 14.20),
            fontsize=9, color=INK, arrowprops=dict(arrowstyle="-", color=MUTED, lw=1))
ax.plot([t3[0]], [q3[0]], marker="o", markersize=11, color=BLUE, zorder=5,
        markeredgecolor="white", markeredgewidth=1.5)
ax.annotate("what it SHOULD report\n(the first look)  13.764", xy=(t3[0], q3[0]), xytext=(20, 13.90),
            fontsize=9, color=INK, arrowprops=dict(arrowstyle="-", color=MUTED, lw=1))
ax.annotate("", xy=(t3[-1] - 4, q3[0]), xytext=(t3[-1] - 4, q3[-1]),
            arrowprops=dict(arrowstyle="<->", color=INK, lw=1.4))
ax.text(t3[-1] - 30, (q3[0] + q3[-1]) / 2, "0.482 units of photodamage:\nthe lamp bleached the pigment\nwhile the instrument watched",
        fontsize=9.5, color=INK, fontweight="bold", va="center", ha="right")
style(ax, "2 · THE BRANCH THAT DOESN'T — a clear fill (003)", "seconds since the fill went in", "Q%")

# --- 3 · why it rises ----------------------------------------------------------
ax = axes[1][0]
s3 = [x["soret"] for x in r3["rows"]]
ax.plot(t3, s3, color=INK, lw=2, marker="o", markersize=5, zorder=3)
ax.text(10, 0.8368,
        "A_Soret falls 2.5 % across the run -\n"
        "the lamp is destroying pigment.\n\n"
        "Meanwhile the turbidity band is FLAT\n"
        "(-1.7 %, and it dips then recovers),\n"
        "so this is not the fill clearing.",
        fontsize=9, color=INK, va="bottom", linespacing=1.35)
style(ax, "3 · WHY IT RISES — the pigment being destroyed (003)", "seconds since the fill went in",
      "A_Soret  448-460 nm")

# --- 4 · what the fix changes --------------------------------------------------
ax = axes[1][1]
runs = ["001", "002", "003", "005"]
for i, n in enumerate(runs):
    rr = record(n)
    shipped = rr["answer"]["value"]
    fixed = rr["rows"][0]["qPercent"]
    ax.plot([shipped, fixed], [i, i], color="#c9ccd1", lw=2.5, zorder=1, solid_capstyle="round")
    ax.plot([shipped], [i], marker="X", markersize=12, color=RED, zorder=3,
            markeredgecolor="white", markeredgewidth=1.5)
    ax.plot([fixed], [i], marker="o", markersize=10, color=BLUE, zorder=3,
            markeredgecolor="white", markeredgewidth=1.5)
    ax.text(shipped + 0.025, i + 0.20, "%.3f" % shipped, fontsize=8, color=INK)
    ax.text(fixed - 0.025, i - 0.30, "%.3f" % fixed, fontsize=8, color=INK, ha="right")
    ax.text(fixed - 0.025, i + 0.20, "%+.3f" % (fixed - shipped), fontsize=8,
            color=MUTED, ha="right")
ax.set_yticks(range(len(runs)))
ax.set_yticklabels(["run " + n for n in runs], fontsize=9)
ax.set_ylim(-0.7, len(runs) + 0.15)
ax.plot([], [], marker="X", markersize=10, color=RED, lw=0, label="as shipped (last look)")
ax.plot([], [], marker="o", markersize=9, color=BLUE, lw=0, label="after the fix (first look)")
ax.legend(fontsize=8.5, frameon=False, loc="upper left", labelcolor=INK,
          bbox_to_anchor=(0.0, 1.02))
ax.set_xlim(13.35, 14.60)
style(ax, "4 · WHAT THE FIX CHANGES — the four 'arrived clear' runs", "Q%", "")

fig.suptitle("Where the settling algorithm is right, and where it is wrong        Lugitsch A, 2026-08-18",
             fontsize=13, fontweight="bold", color=INK, x=0.008, ha="left", y=0.985)
fig.text(0.008, 0.012,
         "Every value read back out of the reports' own embedded workflow.json. "
         "A 'look' is one 60-frame window, about 17 s.", fontsize=8.5, color=MUTED, ha="left")
fig.tight_layout(rect=[0, 0.03, 1, 0.955])
out = os.path.dirname(os.path.abspath(__file__))
fig.savefig(os.path.join(out, "settling_branches.png"), dpi=115, facecolor=fig.get_facecolor())
fig.savefig(os.path.join(out, "settling_branches.svg"), facecolor=fig.get_facecolor())
print("written")
