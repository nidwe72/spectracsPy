"""Plot the TIME FIT of SPEC_capture_quality.md §16.12.11 A - the settling trend, sets B and C.

Four panels, all against elapsed minutes, so the eye can check the claim directly:

  A  the SHIPPED metric in absolute units          - what actually drifts
  B  the same, as % deviation from each set's mean - puts B and C on one scale
  C  A_Soret as % deviation                        - the numerator, where the trend lives
  D  A_Q as % deviation                            - the denominator, which does NOT trend
                                                     => the ratio cannot cancel it

Dashed line per set = the least-squares fit that `detrend()` removes; the annotation carries the
trend across the set and Student's t (4 df, |t| > 2.78 is p < 0.05).

Run:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/settling_plot.py
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from settling_sweep import BASE, SETS, detrend, measure

OUTPUT = "/home/nidwe72/development/spectracs/spectracs-references/tmp/settling_curves.png"

# dataviz reference palette, categorical slots 1-2, light mode. Validated all-pairs:
# CVD dE 24.7, normal-vision dE 33.6, contrast >= 3:1. Colour follows the SET, in fixed order.
SERIES = ["#2a78d6", "#eb6834"]
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#dedcd6"

# Six panels: BOTH metric variants, then the four absorbance quantities that feed them. Colour follows the
# SET in every panel, so identity never repaints between panels.
PANELS = [("S/Q raw", "A · S/Q RAW — no baseline", "S/Q, raw", False),
          ("S/Q linear base", "B · S/Q LINEAR BASELINE — the shipped metric", "S/Q, linear baseline", False),
          ("A_Soret raw", "C · A_Soret 440–460 — the numerator", "deviation from set mean (%)", True),
          ("A_Q raw", "D · A_Q 560–580 — the denominator", "deviation from set mean (%)", True),
          ("A_near 520-540", "E · A_near 520–540 — the near anchor", "deviation from set mean (%)", True),
          ("A_far 600-630", "F · A_far 600–630 — the THIRD REGION (§2.1a)", "deviation from set mean (%)", True)]


def style(axes):
    axes.set_facecolor(SURFACE)
    axes.grid(True, color=GRID, linewidth=0.8, zorder=0)
    axes.set_axisbelow(True)
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axes.spines[side].set_color(GRID)
    axes.tick_params(colors=MUTED, labelsize=9)


def main():
    loaded = []
    for name, paths in SETS:
        runs = [(os.path.getmtime(BASE + p), measure(p)) for p in paths]
        start = runs[0][0]
        loaded.append((name.split()[1], [((s - start) / 60.0, v) for s, v in runs]))

    figure, grid = plt.subplots(2, 3, figsize=(18.0, 9.0), dpi=140, facecolor=SURFACE)
    figure.suptitle("Dilution settling — the time fit  (SPEC_capture_quality.md §16.12.11 A)",
                    fontsize=14, color=INK, x=0.5, y=0.985)
    figure.text(0.5, 0.945, "sets B and C, 2026-07-29 · green oil · 6 re-seats of one fill each · "
                            "dashed = fitted trend, removed by detrending · "
                            "A–B are the two metric variants, C–F the four absorbances that feed them",
                ha="center", fontsize=9.5, color=MUTED)

    for axes, (metric, title, ylabel, normalise) in zip(grid.flat, PANELS):
        style(axes)
        for index, (setName, runs) in enumerate(loaded):
            times = np.array([t for t, _ in runs])
            values = np.array([v[metric] for _, v in runs])
            plotted = (values / values.mean() - 1) * 100 if normalise else values
            _, residualCv, trend, tStatistic = detrend(times, values)

            colour = SERIES[index]
            axes.plot(times, plotted, "o", color=colour, markersize=8, zorder=3,
                      markeredgecolor=SURFACE, markeredgewidth=2,
                      label="set %s" % setName if metric == "S/Q raw" else None)
            slope, intercept = np.polyfit(times, plotted, 1)
            span = np.array([times.min(), times.max()])
            axes.plot(span, slope * span + intercept, "--", color=colour, linewidth=2, zorder=2)
            axes.annotate("set %s   %+.1f %%   t %+.2f%s" % (
                setName, trend, tStatistic, "  ✓p<0.05" if abs(tStatistic) > 2.78 else ""),
                xy=(0.035, 0.115 - 0.070 * index), xycoords="axes fraction",
                fontsize=9.5, color=colour, weight="bold")

        if normalise:
            axes.axhline(0, color=MUTED, linewidth=1, zorder=1)
        # Clear space under the data for the per-set annotations (they sit at 0.05-0.14 axes-fraction).
        low, high = axes.get_ylim()
        axes.set_ylim(low - 0.30 * (high - low), high)
        axes.set_title(title, fontsize=11.5, color=INK, loc="left", pad=8)
        axes.set_ylabel(ylabel, fontsize=9.5, color=MUTED)
        axes.set_xlabel("minutes since the set's first run", fontsize=9.5, color=MUTED)

    # The headline, on the panel that carries it.
    grid.flat[1].annotate("pooled CV  2.92 %  →  1.89 % after detrending\n"
                          "⇒ 58 % of the 'seating' variance is this trend",
                          xy=(0.97, 0.93), xycoords="axes fraction", ha="right", va="top",
                          fontsize=10, color=INK,
                          bbox=dict(boxstyle="round,pad=0.5", facecolor="#f2f1ec",
                                    edgecolor=GRID, linewidth=1))
    grid.flat[3].annotate("flat, never significant — so the\nRATIO cannot cancel the trend",
                          xy=(0.97, 0.93), xycoords="axes fraction", ha="right", va="top",
                          fontsize=10, color=INK,
                          bbox=dict(boxstyle="round,pad=0.5", facecolor="#f2f1ec",
                                    edgecolor=GRID, linewidth=1))
    grid.flat[5].annotate("the third region (§2.1a): it enters the\n"
                          "metric with +0.941 / −0.471 coefficients",
                          xy=(0.97, 0.93), xycoords="axes fraction", ha="right", va="top",
                          fontsize=9.5, color=INK,
                          bbox=dict(boxstyle="round,pad=0.5", facecolor="#f2f1ec",
                                    edgecolor=GRID, linewidth=1))
    grid.flat[0].legend(frameon=False, fontsize=10, labelcolor=MUTED, loc="upper right")

    figure.tight_layout(rect=(0, 0.01, 1, 0.935))
    figure.savefig(OUTPUT, facecolor=SURFACE)
    print("wrote %s" % OUTPUT)


if __name__ == "__main__":
    main()
