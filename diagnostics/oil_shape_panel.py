"""The six-oil baseline / baseline+SNV panel, with one oil opened up into its individual runs.
   (`SPEC_history_tracker.md` §2 — the picture the whole tracker idea came from.)

Every fill except one keeps the `all_oils_panel` form (mean of its runs, ±1 sd band, solid); the oil
named by `--oil` is drawn run by run (dashed), so its run-to-run behaviour can be read against the
between-oil spread. Edwin's observation on 2026-08-13 — *"the similarity of the three curves is
obvious, though M448 differs very much"* — is what §3's shape distance formalises, and §6.4 explains.

⭐ Eight fills since 2026-08-14: the six of `all_oils_panel` plus the archive's two OTHER Steirerkraft
fills, in one teal family. ⇒ **One product, three fills** — and §8.5's result is visible: they do not
coincide, while a different oil (Spar Premium) sits nearer to `0807D` than either of them does.

Three panels, and the THIRD is the one that matches the metric:
  1  the linear-baselined curves
  2  SNV over the whole 448-629 capture range — ⛔ NOT what `D` compares; the Soret sets the sd here
  3  SNV over 550-600 alone — ⭐ literally the vectors `D` compares (§3.1's rule, §7.2's window)

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/oil_shape_panel.py [--oil "Ja! Natürlich"]
"""
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from settling_sweep import despikedAbsorption, asArrays, feature
from shape_similarity import FILLS, BASELINE

OUTPUT = "/home/nidwe72/development/spectracs/spectracs-references/tmp/oil_shape_panel.png"
RUN_COLORS = ["#0b3d0f", "#2e7d32", "#7cb342"]                       # the per-run oil, greens

# ⭐ The two OTHER Steirerkraft fills in the archive (Edwin 2026-08-14). Drawn in the same teal
# family as `20260807D`, so that ONE PRODUCT / THREE FILLS reads at a glance — §8.5: they do not
# overlap, and a different oil (Spar Premium) sits nearer to 0807D than either of them.
# ⛔ Added HERE and not to `shape_similarity.FILLS`, which the 18-run tables of §8.1 and §6.3 count.
EXTRA_FILLS = [("Steirerkraft 0729B", ["20270729B/%03d.pdf" % i for i in range(1, 7)]),
               ("Steirerkraft 0729C", ["20270729C/%03d.pdf" % i for i in range(1, 7)])]
COLORS = {"Steirerkraft g.g.A.": "#00838f", "Steirerkraft 0729B": "#4dd0e1",
          "Steirerkraft 0729C": "#004d40", "Spar Steirisches": "#5c6bc0",
          "Spar Premium g.g.A.": "#a89b3a", "Spar S-Budget": "#8d5524",
          "Billa Clever": "#5d3317", "Ja! Natürlich": "#2e7d32"}
LO, HI = 448.0, 629.0
ANALYSIS = (550.0, 600.0)          # §7.2 — the window the tracker uses
GRID = np.arange(LO, HI + .01, 0.5)


def curve(path, snv, window=None):
    """`window` = None plots the whole capture range; a window renormalises INSIDE it, which is what
    §3.1 requires and therefore exactly the vector `D` compares."""
    spectrum = feature.linearBaselineCorrected(despikedAbsorption(path), BASELINE)
    lam, values = asArrays(spectrum)
    grid = GRID if window is None else np.arange(window[0], window[1] + .01, 0.5)
    y = np.interp(grid, lam, values)
    return (y - y.mean()) / y.std() if snv else y


def draw(axis, singled, others, snv, lineWidth, window=None):
    grid = GRID if window is None else np.arange(window[0], window[1] + .01, 0.5)
    for name, paths in others:
        colour = COLORS[name]
        data = np.array([curve(p, snv, window) for p in paths])
        mean, sd = data.mean(0), data.std(0, ddof=1)
        axis.fill_between(grid, mean - sd, mean + sd, color=colour, alpha=.15)
        axis.plot(grid, mean, color=colour, lw=lineWidth, label="%s  (n=%d)" % (name, len(paths)))
    name, paths = singled
    for i, (path, colour) in enumerate(zip(paths, RUN_COLORS), start=1):
        axis.plot(grid, curve(path, snv, window), color=colour, lw=lineWidth, ls=(0, (5, 1.6)),
                  label="%s · run %03d" % (name, i))


def render(oil):
    everything = list(FILLS) + EXTRA_FILLS
    singled = next((n, p) for n, p in everything if n == oil)
    others = [(n, p) for n, p in everything if n != oil]

    figure, axes = plt.subplots(1, 3, figsize=(21, 6.2))
    for snv, axis, title, ylabel in [
            (False, axes[0], "linear baseline (520–540 / 620–630)", "A above baseline"),
            (True, axes[1], "baseline + SNV over the capture range 448–629", "SNV units")]:
        draw(axis, singled, others, snv, 1.8)
        axis.set_xlim(LO, HI)
        axis.set_title(title)
        axis.set_xlabel("wavelength (nm)")
        axis.set_ylabel(ylabel)
        axis.grid(alpha=.2)
        axis.legend(fontsize=7, loc="upper right")

    # ⭐ Panel 3 renormalises INSIDE 550-600, so these are literally the vectors `D` compares.
    # ⛔ Panel 2 is NOT — it is SNV'd over the whole capture range, where the Soret sets the sd (§3.1).
    axis = axes[2]
    draw(axis, singled, others, True, 2.2, window=ANALYSIS)
    axis.set_xlim(*ANALYSIS)
    axis.set_title("SNV over 550–600 alone — what `D` actually compares (§3.1, §7.2)")
    axis.set_xlabel("wavelength (nm)")
    axis.set_ylabel("SNV units, normalised in-window")
    axis.grid(alpha=.25)
    axis.legend(fontsize=7, loc="lower right")

    figure.suptitle("Six oils + the two archive Steirerkraft refills (teal family) — "
                    "%s shown run by run" % oil, fontsize=13)
    plt.tight_layout(rect=(0, 0, 1, 0.96))
    figure.savefig(OUTPUT, dpi=110)
    print("written", OUTPUT)


def main():
    oil = "Ja! Natürlich"
    if "--oil" in sys.argv:
        oil = sys.argv[sys.argv.index("--oil") + 1]
    known = [n for n, _ in list(FILLS) + EXTRA_FILLS]
    if oil not in known:
        raise SystemExit("unknown oil %r — known: %s" % (oil, ", ".join(known)))
    render(oil)


if __name__ == "__main__":
    main()
