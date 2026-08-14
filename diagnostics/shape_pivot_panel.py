"""The Q-band zoom with every spectrum PIVOTED to 0.0 at a chosen wavelength.
   (Edwin 2026-08-14: *"show this graph but with the spectra shifted such that their values at 558 nm
   are at 0.0"*. `SPEC_history_tracker.md` §8.6)

Subtracting each run's own value at the pivot removes the vertical offset the eye otherwise has to
correct for by hand, so what remains above the pivot is the FAN-OUT: how far each fill's Q band
climbs from a common starting point. 558 nm is a good pivot because it is where the curves already
nearly cross — below it they are flat and uninformative, above it they separate.

⚠ A pivot is NOT a baseline correction and changes no `D`. `D` is invariant to `a -> k*a + b` by
construction (§3.1) and a pivot is exactly such a `b`. ⇒ This figure changes what is easy to SEE, not
what is measured. ⚠ It also inherits whatever noise each run carries at that single wavelength; use a
mean over 556-560 instead if numbers are to be quoted off it rather than looked at.

Two panels, because the pivot means different things on the two quantities:
  1  on the SNV curve (normalised over 448-629) — shape only, amplitude removed
  2  on the linear-baselined absorbance — the physical quantity, in absorbance units

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/shape_pivot_panel.py [--at 558] [--only "Steirerkraft,S-Budget"]

`--only` takes a comma-separated list of substrings, keeps the matching fills and writes a separate
file. ⭐ With a filtered set the individual runs are drawn too, fills are labelled by session, and
colour becomes **hue = product, shade = session** — which is what makes a shared instrument drift
distinguishable from a per-product preparation difference (§8.6a).
"""
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from settling_sweep import despikedAbsorption, asArrays, feature
from shape_similarity import FILLS, BASELINE
from oil_shape_panel import EXTRA_FILLS, COLORS, RUN_COLORS

OUTPUT = "/home/nidwe72/development/spectracs/spectracs-references/tmp/shape_pivot%s.png"
SINGLED = "Ja! Natürlich"                 # drawn run by run in the unfiltered figure
CAPTURE = (448.0, 629.0)
ZOOM = (550.0, 600.0)
READOUT = (565.0, 573.0, 580.0, 590.0)    # where the fan-out is tabulated

# Second fills the six-oil panel does not carry — available to `--only` without disturbing it.
# ⚠ The three Kiendler fills are ONE session and a DELIBERATE dilution series (`kiendler_dilution.py`):
# A = 18 mL + 6 drops, B = A enriched to 7 in place, C = a fresh 18 mL + 7 drops. So for Kiendler the
# shade encodes DOSE, not session — and the A-vs-C gap is a scale bar for what one drop costs.
ARCHIVE_FILLS = [("Spar S-Budget 0731A", ["20260731A/%03d.pdf" % i for i in range(1, 7)]),
                 ("Billa Clever 0812A", ["20260812_BillaClever/%03d.pdf" % i for i in (1, 2, 3)]),
                 ("Kiendler 0801A 6drop", ["20260801A/%03d.pdf" % i for i in range(1, 7)]),
                 ("Kiendler 0801B 7drop", ["20260801B/%03d.pdf" % i for i in (1, 2)]),
                 ("Kiendler 0801C 7drop", ["20260801C/%03d.pdf" % i for i in (1, 2)])]
# In a filtered figure the session matters, so every name says which fill it is.
SESSION_NAMES = {"Steirerkraft g.g.A.": "Steirerkraft 0807D",
                 "Spar S-Budget": "Spar S-Budget 0807B",
                 "Billa Clever": "Billa Clever 0812B",
                 "Spar Steirisches": "Spar Steirisches 0807A",
                 "Spar Premium g.g.A.": "Spar Premium 0807C",
                 "Ja! Natürlich": "Ja! Natürlich 0812"}
# ⭐ hue = product, shade = session (light -> dark with date). A COMMON session shift would show as
# both products' dark curves departing from their light ones in the same direction; a per-product
# preparation difference moves only one hue. That comparison is the point of the figure.
FILTER_COLORS = {"Steirerkraft 0729B": "#4dd0e1", "Steirerkraft 0729C": "#0097a7",
                 "Steirerkraft 0807D": "#004d40",
                 "Spar S-Budget 0731A": "#ffb300", "Spar S-Budget 0807B": "#bf360c",
                 "Billa Clever 0812A": "#a1887f", "Billa Clever 0812B": "#4e342e",
                 "Spar Steirisches 0807A": "#5c6bc0", "Spar Premium 0807C": "#a89b3a",
                 "Ja! Natürlich 0812": "#2e7d32",
                 "Kiendler 0801A 6drop": "#ce93d8", "Kiendler 0801B 7drop": "#ab47bc",
                 "Kiendler 0801C 7drop": "#6a1b9a"}


def curve(path, snv, pivot):
    """One run over the capture range, optionally SNV'd, then shifted to 0.0 at `pivot`."""
    lam, values = asArrays(feature.linearBaselineCorrected(despikedAbsorption(path), BASELINE))
    grid = np.arange(CAPTURE[0], CAPTURE[1] + .01, 0.5)
    y = np.interp(grid, lam, values)
    if snv:
        y = (y - y.mean()) / y.std()
    return grid, y - float(np.interp(pivot, grid, y))


def selected(only):
    """[(displayName, paths)] — everything, or just the fills matching one of the substrings."""
    everything = [(SESSION_NAMES.get(name, name) if only else name, paths)
                  for name, paths in list(FILLS) + EXTRA_FILLS + (ARCHIVE_FILLS if only else [])]
    if not only:
        return everything
    wanted = [term.strip().lower() for term in only.split(",") if term.strip()]
    kept = [(name, paths) for name, paths in everything
            if any(term in name.lower() for term in wanted)]
    if not kept:
        raise SystemExit("nothing matches %r — known: %s"
                         % (only, ", ".join(name for name, _ in everything)))
    return kept


def draw(axis, snv, pivot, only):
    everything = selected(only)
    showRuns = bool(only) and len(everything) <= 5    # room for the runs once the set is small
    visible = []          # ⚠ autoscale would fit the Soret, which lies outside the plotted zoom
    for name, paths in everything:
        if name == SINGLED and not only:
            continue
        data = np.array([curve(p, snv, pivot)[1] for p in paths])
        grid = curve(paths[0], snv, pivot)[0]
        mean, sd = data.mean(0), data.std(0, ddof=1)
        colour = FILTER_COLORS.get(name, COLORS.get(name, "#666666")) if only else COLORS[name]
        axis.fill_between(grid, mean - sd, mean + sd, color=colour, alpha=.18)
        if showRuns:
            for row in data:
                axis.plot(grid, row, color=colour, lw=0.7, alpha=.5)
        axis.plot(grid, mean, color=colour, lw=2.2 if showRuns else 1.9,
                  label="%s  (n=%d)" % (name, len(paths)))
        inside = (grid >= ZOOM[0]) & (grid <= ZOOM[1])
        visible.extend([(mean - sd)[inside].min(), (mean + sd)[inside].max()])
    if not only:
        for i, (path, colour) in enumerate(zip(dict(everything)[SINGLED], RUN_COLORS), start=1):
            grid, y = curve(path, snv, pivot)
            axis.plot(grid, y, color=colour, lw=1.9, ls=(0, (5, 1.6)),
                      label="%s · run %03d" % (SINGLED, i))
            inside = (grid >= ZOOM[0]) & (grid <= ZOOM[1])
            visible.extend([y[inside].min(), y[inside].max()])

    axis.axvline(pivot, color="#555555", lw=1.1, ls=":")
    axis.axhline(0.0, color="#555555", lw=0.9, ls=":")
    axis.annotate("pivot %g nm" % pivot, xy=(pivot, 0), xytext=(pivot + 0.8, 0.02),
                  fontsize=9, color="#333333")
    axis.set_xlim(*ZOOM)
    margin = 0.04 * (max(visible) - min(visible))     # tight — the legend sits below the figure
    axis.set_ylim(min(visible) - margin, max(visible) + margin)
    axis.grid(alpha=.22)
    axis.set_xlabel("wavelength (nm)")


def render(pivot, only):
    figure, axes = plt.subplots(1, 2, figsize=(17, 6.6))
    draw(axes[0], True, pivot, only)
    axes[0].set_title("SNV (448–629), pivoted to 0.0 at %g nm — shape only" % pivot)
    axes[0].set_ylabel("SNV units above the pivot")
    draw(axes[1], False, pivot, only)
    axes[1].set_title("linear-baselined absorbance, pivoted to 0.0 at %g nm" % pivot)
    axes[1].set_ylabel("A above the pivot")

    heading = ("%s — hue = product, shade = session"
               % " + ".join(term.strip() for term in only.split(","))
               if only else "The Q band from a common starting point")
    figure.suptitle("%s · every spectrum shifted to 0.0 at %g nm" % (heading, pivot), fontsize=13)
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="lower center", ncol=min(5, len(labels)), fontsize=9,
                  frameon=False, bbox_to_anchor=(0.5, 0.005))
    plt.tight_layout(rect=(0, 0.10 if len(labels) > 5 else 0.07, 1, 0.95))
    output = OUTPUT % (("_" + only.lower().replace(" ", "").replace(",", "_")) if only else "")
    figure.savefig(output, dpi=110)
    print("written", output)


def table(pivot, only):
    print("\n   Climb above the %g nm pivot, SNV units (mean of runs)" % pivot)
    print("   %-24s %s" % ("fill", "".join("%12s" % ("%g nm" % w) for w in READOUT)))
    rows = []
    for name, paths in selected(only):
        grid = curve(paths[0], True, pivot)[0]
        mean = np.mean([curve(p, True, pivot)[1] for p in paths], axis=0)
        rows.append((float(np.interp(580.0, grid, mean)), name,
                     [float(np.interp(w, grid, mean)) for w in READOUT]))
    for _, name, values in sorted(rows, reverse=True):
        print("   %-24s %s" % (name, "".join("%12.3f" % v for v in values)))


def main():
    pivot = float(sys.argv[sys.argv.index("--at") + 1]) if "--at" in sys.argv else 558.0
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    render(pivot, only)
    table(pivot, only)


if __name__ == "__main__":
    main()
