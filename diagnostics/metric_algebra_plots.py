"""Figures for DOC_metric_algebra.md — what the linear baseline does, drawn.

Three panels, all from the two post-rebuild sets (green 20270729C, brown 20260731A), each the mean of
its six runs on the de-spiked absorbance:

    metric_algebra_bands.png     A(lambda) with the four windows shaded and the fitted baselines drawn
    metric_algebra_corrected.png the same curves after subtracting their own baseline
    metric_algebra_qzoom.png     the Q band before and after -- where the discrimination is actually born

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/metric_algebra_plots.py
"""
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# NEAR/FAR/WINDOWS follow `metric_walkthrough`'s METRIC_ANCHOR, so the figures cannot drift from the
# numbers in the text: set METRIC_ANCHOR=600 there and BOTH move to the legacy anchor together.
from metric_walkthrough import (BASE, GREEN, BROWN, SORET, Q, NEAR, FAR, WINDOWS, absorption,
                                fittedLine, plugin, feature)

OUT = os.path.join(BASE)
GREEN_COLOUR, BROWN_COLOUR = "#2e7d32", "#8d5524"


def meanCurve(paths, corrected=False):
    """Mean spectrum over a set, on the common wavelength grid, optionally baseline-corrected first."""
    grids, curves = None, []
    for path in paths:
        spectrum = absorption(path)
        if corrected:
            spectrum = feature.linearBaselineCorrected(spectrum, WINDOWS)
        lam = np.array(sorted(spectrum.valuesByNanometers))
        values = np.array([spectrum.valuesByNanometers[k] for k in lam])
        if grids is None:
            grids = lam
        curves.append(np.interp(grids, lam, values))
    return grids, np.mean(curves, axis=0)


def meanLine(paths):
    """Mean fitted baseline (slope, intercept) over a set."""
    fits = np.array([fittedLine(absorption(p)) for p in paths])
    return fits.mean(axis=0)


def shade(axis, label=True):
    bottom, top = axis.get_ylim()
    for (lo, hi), colour, name in ((SORET, "#4a6fd0", "Soret\n440–460"), (Q, "#c04a4a", "Q\n560–580"),
                                   (NEAR, "#9e9e9e", "near\n%g–%g" % NEAR),
                                   (FAR, "#9e9e9e", "far\n%g–%g" % FAR)):
        axis.axvspan(lo, hi, color=colour, alpha=0.13, lw=0)
        if label:                                   # along the BOTTOM: the legend owns the top-right
            axis.text((lo + hi) / 2, bottom + 0.035 * (top - bottom), name, ha="center", va="bottom",
                      fontsize=7.5, color="#444")


def main():
    lam, green = meanCurve(GREEN)
    _, brown = meanCurve(BROWN)
    greenLine, brownLine = meanLine(GREEN), meanLine(BROWN)

    # ---------------------------------------------------------------- 1  raw + fitted baselines
    # Two rows: the Soret rises to A ~ 2.1 and would flatten everything else, so the lower row
    # re-plots the same curves on the scale the other three windows actually live on.
    figure, axes = plt.subplots(2, 1, figsize=(9.2, 6.6), sharex=True,
                                gridspec_kw={"height_ratios": [1.0, 1.25]})
    for axis, limit in zip(axes, ((0, 2.25), (0.03, 0.30))):
        axis.plot(lam, green, color=GREEN_COLOUR, lw=1.6, label="green oil (20270729C, mean of 6)")
        axis.plot(lam, brown, color=BROWN_COLOUR, lw=1.6, label="brown oil (20260731A, mean of 6)")
        axis.plot(lam, greenLine[0] * lam + greenLine[1], color=GREEN_COLOUR, lw=1.1, ls="--",
                  label="fitted baseline (green)")
        axis.plot(lam, brownLine[0] * lam + brownLine[1], color=BROWN_COLOUR, lw=1.1, ls="--",
                  label="fitted baseline (brown)")
        axis.set_ylim(*limit)
        shade(axis, label=limit[1] < 1)          # label the magnified row only — the top row has no room
        axis.set_ylabel("absorbance A")
        axis.grid(alpha=0.25, lw=0.5)
    axes[0].set_title("A(λ), de-spiked — the four windows and the baseline fitted through two of them",
                      fontsize=10.5)
    axes[0].legend(fontsize=8, loc="upper right", framealpha=0.95)
    axes[1].set_title("same curves, magnified onto the weak-absorbance region — no part of this "
                      "window is signal-free (note the ~473 and ~607 nm lamp lines, both now OUTSIDE "
                      "every window the metric reads)", fontsize=8.4)
    axes[1].set_xlabel("wavelength (nm)")
    figure.tight_layout()
    figure.savefig(os.path.join(OUT, "metric_algebra_bands.png"), dpi=170)

    # ---------------------------------------------------------------- 2  after subtraction
    lamC, greenC = meanCurve(GREEN, corrected=True)
    _, brownC = meanCurve(BROWN, corrected=True)
    figure, axis = plt.subplots(figsize=(9.2, 4.6))
    axis.plot(lamC, greenC, color=GREEN_COLOUR, lw=1.6, label="green oil, baseline-corrected")
    axis.plot(lamC, brownC, color=BROWN_COLOUR, lw=1.6, label="brown oil, baseline-corrected")
    axis.axhline(0, color="#666", lw=0.9, ls=":")
    axis.set_ylim(-0.09, 1.35)
    shade(axis)
    axis.set_xlabel("wavelength (nm)")
    axis.set_ylabel("absorbance above the fitted baseline")
    axis.set_title("After subtracting each curve's own baseline — the two anchor windows are pinned to zero",
                   fontsize=10.5)
    axis.legend(fontsize=8, loc="upper right", framealpha=0.95)
    axis.grid(alpha=0.25, lw=0.5)
    figure.tight_layout()
    figure.savefig(os.path.join(OUT, "metric_algebra_corrected.png"), dpi=170)

    # ---------------------------------------------------------------- 3  the Q band, before and after
    figure, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))
    window = (lam >= 545) & (lam <= 600)
    for axis, (gCurve, bCurve, title) in zip(axes, (
            (green, brown, "before correction — the Q bands nearly coincide"),
            (greenC, brownC, "after correction — brown's Q is now HIGHER"))):
        axis.plot(lam[window], gCurve[window], color=GREEN_COLOUR, lw=1.8, label="green")
        axis.plot(lam[window], bCurve[window], color=BROWN_COLOUR, lw=1.8, label="brown")
        axis.axvspan(Q[0], Q[1], color="#c04a4a", alpha=0.13, lw=0)
        axis.set_title(title, fontsize=9.5)
        axis.set_xlabel("wavelength (nm)")
        axis.grid(alpha=0.25, lw=0.5)
        axis.legend(fontsize=8)
    axes[0].set_ylabel("absorbance A")
    figure.tight_layout()
    figure.savefig(os.path.join(OUT, "metric_algebra_qzoom.png"), dpi=170)

    for name in ("metric_algebra_bands.png", "metric_algebra_corrected.png", "metric_algebra_qzoom.png"):
        print("wrote", os.path.join(OUT, name))


if __name__ == "__main__":
    main()
