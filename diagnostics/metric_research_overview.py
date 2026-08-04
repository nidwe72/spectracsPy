"""All 22 runs of the three post-rebuild oils, in one picture. (docs/SPEC_metric_research.md §3)

INSPECTION, not measurement. The point is to look at the corpus §2 of the spec restricts us to --
Kiendler 20260801A/B/C, Steirerkraft 20270729B/C, S-Budget 20260731A -- before any candidate metric is
scored, and to see whether anything separates the classes by eye.

`20270729A_aged24h` is EXCLUDED on purpose: it is a browner oil, not a noisier one (§16.11.16), so
including it would put an uncontrolled ageing axis into a plot meant to show oil class.

Four panels, chosen to answer four different questions:
  A  raw absorbance         -- how much of the spread is just concentration?
  B  normalised at 450 nm   -- with concentration divided out, does SHAPE separate the classes?
  C  1st derivative (SG)    -- where the flank slopes live; additive offsets are already gone here
  D  2nd derivative (SG)    -- a straight baseline is annihilated exactly; what survives is curvature

Writes docs/figures/metric_overview.svg.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/metric_research_overview.py
"""
import os

import numpy as np
from scipy.signal import savgol_filter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from settling_sweep import despikedAbsorption, asArrays

HERE = os.path.dirname(os.path.abspath(__file__))
FIGURES = os.path.abspath(os.path.join(HERE, "..", "docs", "figures"))

# The spec's §2 corpus, and nothing else.
SETS = [("Kiendler A", "Kiendler", ["20260801A/%03d.pdf" % i for i in range(1, 7)]),
        ("Kiendler B", "Kiendler", ["20260801B/%03d.pdf" % i for i in range(1, 3)]),
        ("Kiendler C", "Kiendler", ["20260801C/%03d.pdf" % i for i in range(1, 3)]),
        ("Steirerkraft B", "Steirerkraft", ["20270729B/%03d.pdf" % i for i in range(1, 7)]),
        ("Steirerkraft C", "Steirerkraft", ["20270729C/%03d.pdf" % i for i in range(1, 7)]),
        ("S-Budget D", "S-Budget", ["20260731A/%03d.pdf" % i for i in range(1, 7)])]

GREEN, GREEN_DK, BROWN, INK, MUTED = "#2e7d32", "#1b5e20", "#8d5524", "#1c211c", "#5c655c"
COLOUR = {"Kiendler": GREEN, "Steirerkraft": GREEN_DK, "S-Budget": BROWN}

# The shipped windows, drawn so window placement can be argued about against what the curves do.
WINDOWS = [(440.0, 460.0, "Soret"), (520.0, 540.0, "near"),
           (560.0, 580.0, "Q"), (620.0, 630.0, "far/Qy")]
PIVOT = 450.0                  # panel B divides every run by its own absorbance here
SG_WINDOW, SG_ORDER = 101, 3   # 101 bins x 0.146 nm = 14.7 nm -- narrower than any band in range


def load():
    """One resampled (lam, A) pair per run, on the first run's grid so panels can average later."""
    grid, runs = None, []
    for name, oil, paths in SETS:
        for path in paths:
            lam, values = asArrays(despikedAbsorption(path))
            if grid is None:
                grid = lam
            runs.append((name, oil, np.interp(grid, lam, values)))
    return grid, runs


def bandValue(grid, values, low, high):
    mask = (grid >= low) & (grid <= high)
    return values[mask].mean()


def drawWindows(axis, label=False):
    for low, high, name in WINDOWS:
        axis.axvspan(low, high, color=MUTED, alpha=0.09, zorder=0)
        if label:
            axis.text((low + high) / 2, axis.get_ylim()[1], name, fontsize=6.4, color=MUTED,
                      ha="center", va="top")


def main():
    os.makedirs(FIGURES, exist_ok=True)
    plt.rcParams.update({"font.size": 8.0, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                         "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
                         "svg.fonttype": "none"})
    grid, runs = load()
    print("loaded %d runs over %.1f-%.1f nm, %d bins" % (len(runs), grid.min(), grid.max(), len(grid)))

    step = float(np.median(np.diff(grid)))
    figure, axes = plt.subplots(2, 2, figsize=(11.0, 7.4))
    seen = set()

    for name, oil, values in runs:
        label = oil if oil not in seen else None
        seen.add(oil)
        style = dict(c=COLOUR[oil], lw=0.7, alpha=0.55, zorder=3, label=label)
        axes[0][0].plot(grid, values, **style)
        axes[0][1].plot(grid, values / bandValue(grid, values, PIVOT - 2, PIVOT + 2), **style)
        first = savgol_filter(values, SG_WINDOW, SG_ORDER, deriv=1, delta=step)
        second = savgol_filter(values, SG_WINDOW, SG_ORDER, deriv=2, delta=step)
        axes[1][0].plot(grid, first, **style)
        axes[1][1].plot(grid, second, **style)

    titles = ["A · raw absorbance — most of this spread is CONCENTRATION",
              "B · normalised at %.0f nm — concentration divided out, only SHAPE left" % PIVOT,
              "C · 1st derivative — any constant offset is already gone",
              "D · 2nd derivative — a straight baseline is annihilated exactly"]
    labels = ["A  (absorbance)", "A / A(%.0f nm)" % PIVOT, "dA/dλ  (A/nm)", "d²A/dλ²  (A/nm²)"]
    for axis, title, ylabel in zip(axes.ravel(), titles, labels):
        axis.set_title(title, fontsize=8.6, color=INK)
        axis.set_ylabel(ylabel)
        axis.set_xlabel("wavelength (nm)")
        axis.set_xlim(grid.min(), grid.max())
        axis.axhline(0, c=MUTED, lw=0.6)
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)

    # The derivative panels are dominated by the Soret flank; clip them to where the Q features are
    # legible, which is the whole reason for looking at derivatives in the first place.
    for axis in (axes[1][0], axes[1][1]):
        mask = grid >= 500.0
        pool = np.concatenate([savgol_filter(v, SG_WINDOW, SG_ORDER,
                                             deriv=1 if axis is axes[1][0] else 2, delta=step)[mask]
                               for _, _, v in runs])
        span = np.percentile(np.abs(pool), 99.5) * 1.25
        axis.set_ylim(-span, span)
    axes[0][1].set_ylim(0, 1.35)

    for axis in axes.ravel():
        drawWindows(axis)
    axes[0][0].legend(frameon=False, fontsize=7.6, loc="upper right")
    figure.suptitle("The three post-rebuild oils, all 28 runs — aged fill excluded",
                    fontsize=10.5, color=INK)
    figure.tight_layout(rect=(0, 0, 1, 0.965))
    figure.savefig(os.path.join(FIGURES, "metric_overview.svg"))
    plt.close(figure)
    print("wrote", os.path.join(FIGURES, "metric_overview.svg"))

    # A numeric companion to the eye: per-oil means of the shape quantities the spec's C1/C10 use.
    print("\n%-14s %10s %10s %10s %10s" % ("oil", "slope far", "slope 460-480", "C1 ratio", "A_Q/A_450"))
    print("-" * 60)
    for oil in ("Kiendler", "Steirerkraft", "S-Budget"):
        rows = [v for _, o, v in runs if o == oil]
        far = [np.polyfit(grid[(grid >= 620) & (grid <= 629.8)],
                          v[(grid >= 620) & (grid <= 629.8)], 1)[0] for v in rows]
        soret = [np.polyfit(grid[(grid >= 460) & (grid <= 480)],
                            v[(grid >= 460) & (grid <= 480)], 1)[0] for v in rows]
        ratio = np.array(far) / np.array(soret)
        qOverPivot = [bandValue(grid, v, 560, 580) / bandValue(grid, v, 448, 452) for v in rows]
        print("%-14s %+10.5f %+10.5f %10s %10.4f"
              % (oil, np.mean(far), np.mean(soret),
                 "%.3f±%.3f" % (ratio.mean(), ratio.std(ddof=1)), np.mean(qOverPivot)))


if __name__ == "__main__":
    main()
