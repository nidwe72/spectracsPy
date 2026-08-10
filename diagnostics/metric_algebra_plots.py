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
    # ⚠ The Soret caption is DERIVED from the constant, not typed (SPEC_soret_448_trim.md §3): the window moved
    # 440-460 -> 448-460 on 2026-08-10, and a hardcoded label would have kept saying 440-460 over a shaded band
    # that had moved. ⚠ The figures COMMITTED under docs/figures/ (and the published Spectracs_MetricAlgebra.pdf)
    # were generated on 440-460; regenerating them now redraws that band. Regenerate deliberately, not by habit.
    for (lo, hi), colour, name in ((SORET, "#4a6fd0", "Soret\n%g–%g" % SORET), (Q, "#c04a4a", "Q\n560–580"),
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

    # ---------------------------------------------------------------- 4  the TILT, measured (2026-08-10)
    # The MEASURED counterpart to `pigment_far_window_slope.svg`, which shows this mechanism as a schematic.
    # Question behind it (Edwin): "the Soret is shifted down for the greener oil too — how does that help?"
    #
    # ⭐ THE ANSWER, and it is not the symmetric one: the two classes' baselines nearly COINCIDE at the blue
    # end and FAN APART toward the red, because the near anchors agree while the far anchors do not. So the
    # tilt is worth ~1 % of B_Soret and ~45 % of B_Q — the numerator barely notices it and the denominator is
    # made of it. That is §5.3a's "the long lever costs about one per cent", measured.
    # ⚠ The crossing wavelength is NOT a property of the metric: it moves with the pair (473 nm for these
    # two set means, 518 nm for the single-run pair the discussion started from). Do not quote it as a
    # constant — what is stable is the FANNING, not where the fan closes.
    figure, axes = plt.subplots(2, 1, figsize=(9.2, 6.6),
                                gridspec_kw={"height_ratios": [1.0, 1.25]})
    at = lambda fit, nm: fit[0] * np.asarray(nm) + fit[1]      # meanLine returns (slope, intercept)
    crossing = (brownLine[1] - greenLine[1]) / (greenLine[0] - brownLine[0])
    for axis, (lo, hi), (ylo, yhi) in zip(axes, ((440, 636), (505, 636)), ((-0.02, 0.9), (0.0, 0.26))):
        for (bandLo, bandHi), tint in ((SORET, "0.86"), (NEAR, "#c8d2dc"), (Q, "0.86"), (FAR, "#c8d2dc")):
            axis.axvspan(bandLo, bandHi, color=tint, zorder=-10)
        for values, line, colour, label in ((green, greenLine, GREEN_COLOUR, "green oil"),
                                            (brown, brownLine, BROWN_COLOUR, "brown oil")):
            axis.plot(lam, values, color=colour, lw=1.4, label="%s — A(λ)" % label)
            axis.plot(lam, at(line, lam), color=colour, lw=1.4, ls="--", alpha=0.85,
                      label="%s — fitted baseline" % label)
        axis.axvline(crossing, color="0.35", lw=1.0, ls=":")
        axis.set_xlim(lo, hi)
        axis.set_ylim(ylo, yhi)
        axis.set_ylabel("absorbance A")
        axis.grid(alpha=0.25, lw=0.5)
    axes[0].annotate("the two baselines nearly coincide here\nand fan apart toward the red",
                     xy=(crossing, 0.30), xytext=(crossing + 14, 0.62), fontsize=8, color="0.25",
                     arrowprops=dict(arrowstyle="->", color="0.45", lw=0.8))
    axes[0].annotate("", xy=(454, at(greenLine, 454.0)), xytext=(454, at(brownLine, 454.0)),
                     arrowprops=dict(arrowstyle="<->", color="#c0392b", lw=1.3))
    axes[0].annotate("at the Soret the two lines barely differ:\nthe tilt is worth ~1 % of B_Soret",
                     xy=(456, at(greenLine, 456.0)), xytext=(486, 0.34), fontsize=8, color="#c0392b",
                     arrowprops=dict(arrowstyle="->", color="#c0392b", lw=0.8))
    axes[1].annotate("", xy=(570, at(greenLine, 570.0)), xytext=(570, at(brownLine, 570.0)),
                     arrowprops=dict(arrowstyle="<->", color="#c0392b", lw=1.3))
    axes[1].annotate("at Q the SAME tilt is worth ~45 % of B_Q —\ngreen's line sits higher, so less Q survives",
                     xy=(572, 0.140), xytext=(583, 0.043), fontsize=8, color="#c0392b",
                     arrowprops=dict(arrowstyle="->", color="#c0392b", lw=0.8))
    axes[1].annotate("and this is what tilts it: the green oil's\nred band stands higher (Qy, ~625 nm)",
                     xy=(624, 0.196), xytext=(534, 0.238), fontsize=8, color="#1f618d",
                     arrowprops=dict(arrowstyle="->", color="#1f618d", lw=0.8))
    axes[0].legend(fontsize=8, loc="upper right")
    axes[1].set_xlabel("wavelength (nm)")
    figure.tight_layout()
    figure.savefig(os.path.join(OUT, "metric_algebra_pivot.png"), dpi=170)

    for name in ("metric_algebra_bands.png", "metric_algebra_corrected.png", "metric_algebra_qzoom.png",
                 "metric_algebra_pivot.png"):
        print("wrote", os.path.join(OUT, name))


if __name__ == "__main__":
    main()
