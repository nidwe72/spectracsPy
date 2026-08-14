"""ONE PRODUCT, THREE FILLS — the Steirerkraft g.g.A. refills, alone. (`SPEC_history_tracker.md` §8.5)

The picture behind the result that blocks the tracker: `20270729B` and `20270729C` were prepared on
one evening; `20260807D` nine days later, on the capillary recipe (§16.27.6a). Against `0807D` as
reference, a DIFFERENT oil (Spar Premium, 7.5-8.3 %) sits nearer than either of this oil's own
earlier fills (31.4-45.9 %).

Colour says session, not oil: the two same-evening fills share the cyan family, `0807D` is orange
because it is the one measured in a different session on a different recipe.

Each fill is drawn as its individual runs (thin), their mean (thick) and a ±1 sd band, so
within-fill scatter and between-fill separation are on the same axes.

The three panels answer "how much do they differ?" in the three normalisations that matter, and each
title carries the measured `D` between the fill templates, so the picture and the number agree:
  1  linear baseline, full capture range — the amplitudes, which agree well
  2  SNV over 550-600 — §7.2's window, `D` ~ 20 %
  3  SNV over 560-580 — the narrow window, `D` ~ 36 %
⇒ ⚠ The same three fills, the same maths, and the disagreement nearly doubles with the window.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/steirerkraft_refills_panel.py
"""
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from settling_sweep import despikedAbsorption, asArrays, feature
from shape_similarity import BASELINE, dissimilarity

OUTPUT = "/home/nidwe72/development/spectracs/spectracs-references/tmp/steirerkraft_refills.png"
FILLS = [("0729B  2026-07-29", ["20270729B/%03d.pdf" % i for i in range(1, 7)], "#4dd0e1"),
         ("0729C  2026-07-29", ["20270729C/%03d.pdf" % i for i in range(1, 7)], "#00838f"),
         ("0807D  2026-08-07 · capillary recipe", ["20260807D/%03d.pdf" % i for i in (1, 2, 3)],
          "#e65100")]
FULL = (448.0, 629.0)


def curves(paths, window, snv):
    grid = np.arange(window[0], window[1] + .01, 0.5)
    out = []
    for path in paths:
        lam, values = asArrays(feature.linearBaselineCorrected(despikedAbsorption(path), BASELINE))
        y = np.interp(grid, lam, values)
        out.append((y - y.mean()) / y.std() if snv else y)
    return grid, np.array(out)


def template(paths, window):
    _, data = curves(paths, window, True)
    mean = data.mean(0)
    return (mean - mean.mean()) / mean.std()


def spread(window):
    """Mean pairwise D between the three fill templates, and the worst pair."""
    templates = [(name, template(paths, window)) for name, paths, _ in FILLS]
    pairs = [(dissimilarity(a, b), na.split()[0], nb.split()[0])
             for i, (na, a) in enumerate(templates) for nb, b in templates[i + 1:]]
    return float(np.mean([p[0] for p in pairs])), max(pairs)


def draw(axis, window, snv):
    for name, paths, colour in FILLS:
        grid, data = curves(paths, window, snv)
        mean, sd = data.mean(0), data.std(0, ddof=1)
        axis.fill_between(grid, mean - sd, mean + sd, color=colour, alpha=.18)
        for row in data:
            axis.plot(grid, row, color=colour, lw=0.7, alpha=.55)
        axis.plot(grid, mean, color=colour, lw=2.3, label="%s  (n=%d)" % (name, len(paths)))
    axis.set_xlim(*window)
    axis.grid(alpha=.22)
    axis.set_xlabel("wavelength (nm)")


def render():
    figure, axes = plt.subplots(1, 3, figsize=(21, 6.4))

    draw(axes[0], FULL, False)
    axes[0].set_title("linear baseline (520–540 / 620–630) — the amplitudes")
    axes[0].set_ylabel("A above baseline")
    axes[0].legend(fontsize=9, loc="upper right")

    for axis, window in ((axes[1], (550.0, 600.0)), (axes[2], (560.0, 580.0))):
        draw(axis, window, True)
        mean, (worst, a, b) = spread(window)
        axis.set_title("SNV over %g–%g alone — mean D = %.1f %%  (worst %s vs %s: %.1f %%)"
                       % (window[0], window[1], mean, a, b, worst))
        axis.set_ylabel("SNV units, normalised in-window")
        axis.legend(fontsize=9, loc="lower right")

    figure.suptitle("Steirerkraft g.g.A. — ONE PRODUCT, THREE FILLS "
                    "(cyan = one evening, orange = nine days later)", fontsize=13)
    plt.tight_layout(rect=(0, 0, 1, 0.955))
    figure.savefig(OUTPUT, dpi=110)
    print("written", OUTPUT)


def main():
    render()
    print()
    print("   %-14s %10s   %s" % ("window", "mean D", "worst pair"))
    for window in ((550.0, 600.0), (560.0, 580.0), (540.0, 584.0)):
        mean, (worst, a, b) = spread(window)
        print("   %-14s %9.2f%%   %s vs %s  %.2f%%" % ("%g-%g nm" % window, mean, a, b, worst))


if __name__ == "__main__":
    main()
