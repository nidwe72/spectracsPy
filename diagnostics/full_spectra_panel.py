"""The COMPLETE spectra — the whole 448-629 capture range, not the Q-band zoom.
   (Edwin 2026-08-14: *"show me the according complete spectra of the S-Budget and Steirerkraft
   oils"*. `SPEC_history_tracker.md` §8.6b)

Every earlier figure cropped to 550-600, where the tracker's window lives. This one shows what the
instrument actually delivers, in the three representations the analysis moves through:

  1  de-spiked ABSORBANCE, as measured        — the Soret dominates; nothing is subtracted yet
  2  after the LINEAR BASELINE chord          — what `feature.linearBaselineCorrected` produces, with
                                                the two anchor windows shaded so the chord's feet are
                                                visible (§7.1)
  3  after SNV over the whole range           — shape only, and the panel that shows why §3.1 forbids
                                                normalising here when the Q band is the subject: the
                                                Soret sets the standard deviation

⚠ Below ~460 nm the curves are on the steep Soret flank where §16.29 puts the dynamic-range wall, and
above ~605 nm the lamp lines sit (visible as the spikes the de-spiker did not fully flatten). Read
the middle of the range; the ends are instrument, not oil.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/full_spectra_panel.py [--only "Steirerkraft,S-Budget"] \
            [--at 473] [--runs "Natürlich"] [--range 500,580]

⭐ `--runs <substring>` opens the matching fills up into their INDIVIDUAL runs instead of a mean and a
band, so within-fill behaviour (drift, a bad seating) can be read against the between-fill spread.

⭐ `--range lo,hi` crops the x axis and rescales y to what is actually inside it. `--at 580 --range
500,580` is the "depth below the Q peak" view: every curve ends at 0.0 on the right and its distance
below zero at each wavelength is how far the plateau sits under that fill's own Q maximum.

⭐ `--at <nm>` shifts every curve so its value is 0.0 there. 473.0 nm is the LAMP LINE, and it sits at
473.0 on all 25 archive runs (sd 0.00-0.29 across four sessions) — so it is an instrument fiducial,
not an oil feature, and pivoting on it anchors every spectrum to the same instrumental landmark.
⚠ It is also a 2-3 point spike, so the pivot inherits its noise; 558 nm (`shape_pivot_panel.py`) is
the quieter choice when numbers are to be quoted rather than looked at.
"""
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from settling_sweep import despikedAbsorption, asArrays, feature
from shape_similarity import BASELINE
from oil_shape_panel import COLORS, RUN_COLORS
from shape_pivot_panel import selected, FILTER_COLORS, CAPTURE

OUTPUT = "/home/nidwe72/development/spectracs/spectracs-references/tmp/full_spectra%s.png"
GRID = np.arange(CAPTURE[0], CAPTURE[1] + .01, 0.5)
BANDS = ((448.0, 460.0, "Soret 448–460"), (560.0, 580.0, "Q 560–580"))


def curve(path, mode, pivot=None):
    """mode: 'raw' as measured, 'base' after the chord, 'snv' after SNV over the whole range."""
    spectrum = despikedAbsorption(path)
    if mode != "raw":
        spectrum = feature.linearBaselineCorrected(spectrum, BASELINE)
    lam, values = asArrays(spectrum)
    y = np.interp(GRID, lam, values)
    if mode == "snv":
        y = (y - y.mean()) / y.std()
    return y if pivot is None else y - float(np.interp(pivot, GRID, y))


def expanded(fills, runs):
    """Split any fill matching `runs` into one series per capture."""
    if not runs:
        return fills, {}
    wanted = [term.strip().lower() for term in runs.split(",") if term.strip()]
    out, palette = [], {}
    for name, paths in fills:
        if not any(term in name.lower() for term in wanted):
            out.append((name, paths))
            continue
        for i, path in enumerate(paths, start=1):
            label = "%s · run %03d" % (name, i)
            out.append((label, [path]))
            palette[label] = RUN_COLORS[(i - 1) % len(RUN_COLORS)]
    return out, palette


def draw(axis, fills, mode, only, pivot, palette=None, window=None):
    palette = palette or {}
    shown = []
    showRuns = len(fills) <= 5
    for name, paths in fills:
        data = np.array([curve(p, mode, pivot) for p in paths])
        mean = data.mean(0)
        sd = data.std(0, ddof=1) if len(paths) > 1 else None   # a single run has no spread to shade
        colour = palette.get(name) or (FILTER_COLORS.get(name, COLORS.get(name, "#666666"))
                                       if only else COLORS[name])
        if sd is not None:
            axis.fill_between(GRID, mean - sd, mean + sd, color=colour, alpha=.18)
        if showRuns and len(paths) > 1:
            for row in data:
                axis.plot(GRID, row, color=colour, lw=0.6, alpha=.45)
        axis.plot(GRID, mean, color=colour, lw=2.0, ls="--" if len(paths) == 1 else "-",
                  label=name if len(paths) == 1 else "%s  (n=%d)" % (name, len(paths)))
        shown.extend([mean] if sd is None else [mean - sd, mean + sd])
    axis.set_xlim(*(window or CAPTURE))
    if window:
        inside = (GRID >= window[0]) & (GRID <= window[1])
        low = min(v[inside].min() for v in shown)
        high = max(v[inside].max() for v in shown)
        pad = 0.05 * (high - low)
        axis.set_ylim(low - pad, high + pad)
    if pivot is not None:
        axis.axvline(pivot, color="#555555", lw=1.1, ls=":")
    axis.grid(alpha=.22)
    axis.set_xlabel("wavelength (nm)")


def annotate(axis, mode):
    """Anchor windows on the baselined panel, the two measured bands everywhere else."""
    if mode == "base":
        for low, high in BASELINE:
            axis.axvspan(low, high, color="#9e9e9e", alpha=.20, lw=0)
        axis.annotate("baseline anchors", xy=(530, axis.get_ylim()[1]),
                      xytext=(497, axis.get_ylim()[1] * 0.93), fontsize=8, color="#444444")
    else:
        for low, high, label in BANDS:
            axis.axvspan(low, high, color="#90a4ae", alpha=.16, lw=0)
    axis.axhline(0.0, color="#555555", lw=0.8, ls=":")


def render(only, pivot, runs, window=None):
    fills, palette = expanded(selected(only), runs)
    figure, axes = plt.subplots(1, 3, figsize=(22, 6.6))
    panels = [("raw", "de-spiked absorbance, as measured", "A"),
              ("base", "after the linear baseline chord (520–540 / 620–630)", "A above baseline"),
              ("snv", "after SNV over the whole 448–629 range", "SNV units")]
    for axis, (mode, title, ylabel) in zip(axes, panels):
        draw(axis, fills, mode, only, pivot, palette, window)
        annotate(axis, mode)
        axis.set_title(title + ("" if pivot is None else "  ·  pivoted to 0.0 at %g nm" % pivot),
                       fontsize=11)
        axis.set_ylabel(ylabel + ("" if pivot is None else ", above the pivot"))

    heading = ("%s — hue = product, shade = session"
               % " + ".join(term.strip() for term in only.split(",")) if only else "All fills")
    figure.suptitle("%s · the COMPLETE spectra, 448–629 nm%s"
                    % (heading, "" if pivot is None
                       else "  ·  every spectrum shifted to 0.0 at %g nm%s"
                       % (pivot, " (the lamp line)" if abs(pivot - 473.0) < 0.6 else "")),
                    fontsize=13)
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="lower center", ncol=min(5, len(labels)), fontsize=9,
                  frameon=False, bbox_to_anchor=(0.5, 0.005))
    plt.tight_layout(rect=(0, 0.09 if len(labels) > 5 else 0.06, 1, 0.95))
    output = OUTPUT % ((("_" + only.lower().replace(" ", "").replace(",", "_")) if only else "")
                       + ("" if pivot is None else "_pivot%g" % pivot)
                       + ("_runs" if runs else "")
                       + ("" if not window else "_%g-%g" % window))
    figure.savefig(output, dpi=110)
    print("written", output)


def table(only, runs):
    print("\n   Band means on the BASELINED curve, and the shipped ratio")
    print("   %-28s %12s %12s %10s" % ("fill", "B_Soret", "B_Q", "S/Q"))
    for name, paths in expanded(selected(only), runs)[0]:
        soret, q = [], []
        for path in paths:
            lam, values = asArrays(feature.linearBaselineCorrected(despikedAbsorption(path),
                                                                   BASELINE))
            for band, sink in ((BANDS[0], soret), (BANDS[1], q)):
                window = (lam >= band[0]) & (lam <= band[1])
                sink.append(float(values[window].mean()))
        soret, q = np.array(soret), np.array(q)
        print("   %-28s %12.4f %12.4f %10.2f"
              % (name, soret.mean(), q.mean(), soret.mean() / q.mean()))


def main():
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    pivot = float(sys.argv[sys.argv.index("--at") + 1]) if "--at" in sys.argv else None
    runs = sys.argv[sys.argv.index("--runs") + 1] if "--runs" in sys.argv else None
    window = None
    if "--range" in sys.argv:
        window = tuple(float(x) for x in sys.argv[sys.argv.index("--range") + 1].split(","))
    render(only, pivot, runs, window)
    table(only, runs)


if __name__ == "__main__":
    main()
