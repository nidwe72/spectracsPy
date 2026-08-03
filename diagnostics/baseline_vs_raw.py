"""RAW vs LINEAR-BASELINE S/Q on the two invariances the metric claims (SPEC_capability_proof.md §2.1a).

§2.1a showed the linear baseline is not a correction but a third measuring region. That predicts it should
change how the metric behaves under the two things it is supposed to be immune to. Both are testable on PDFs
already on disk, and both matter:

  DILUTION INVARIANCE - the metric's whole justification (§3): S/Q must cancel concentration.
      green  oilK (2 drops) -> oilL (3 drops)        §11.1 UC2
      brown  oilN (2 drops) -> oilM (3 drops)        §11.4 N-series
      green  set B -> set C, 2026-07-29              §16.11.6 (~17 % apart)

  SETTLING - and specifically the SIGN, which is the open contradiction:
      §11.4c predicts settling makes S/Q *INFLATE*; §11.4a measured 3.66 -> 4.57 over 11 h.
      SPEC_capture_quality §16.12.11 A measures the SHIPPED metric *DEFLATING* over 30 min.
      green  oilO+oilP (fresh afternoon) -> now.pdf (same cuvette, ~11 h later)   §11.4a
      green  set B / set C, first -> last run (~30 min)                          §16.12.11 A

Every number reported is a change that SHOULD BE ZERO. Reporting raw and baselined side by side says whether
the third region helps or hurts each invariance.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/baseline_vs_raw.py
"""
import os

import numpy as np

from far_anchor_probe import spectra
from metric_bench import BASE, feature, plugin
from sciens.spectracs.model.spectral.Spectrum import Spectrum

SORET, Q, WINDOWS = plugin.PB_SORET_BAND, plugin.PB_Q_BAND, plugin.PB_BASELINE_WINDOWS_LEGACY_600   # 600-630 — the anchor this script's published numbers were measured on (§16.20)

REPORT = "measurement_report_oil%s_%03d.pdf"
GREEN_WEAK = [REPORT % ("K", i) for i in range(1, 5)]        # 2 drops
GREEN_STRONG = [REPORT % ("L", i) for i in range(1, 5)]      # 3 drops
BROWN_WEAK = [REPORT % ("N", i) for i in range(1, 5)]        # 2 drops
BROWN_STRONG = [REPORT % ("M", i) for i in range(1, 5)]      # 3 drops
SET_B = ["20270729B/%03d.pdf" % i for i in range(1, 7)]
SET_C = ["20270729C/%03d.pdf" % i for i in range(1, 7)]
FRESH_GREEN = [REPORT % ("O", i) for i in range(1, 5)] + [REPORT % ("P", i) for i in range(1, 5)]
AGED_GREEN = ["measurement_report_now.pdf"]

DILUTION = [("green  K→L  2→3 drops", GREEN_WEAK, GREEN_STRONG),
            ("brown  N→M  2→3 drops", BROWN_WEAK, BROWN_STRONG),
            ("green  set B→C  ~17 %", SET_B, SET_C)]


def metrics(path):
    """(rawSQ, linearBaselineSQ) for one run."""
    values = spectra(path)["ABSORPTION"]
    lam = np.array(sorted(values))
    raw = np.array([values[k] for k in lam])

    source = Spectrum()
    source.valuesByNanometers = dict(values)
    corrected = feature.linearBaselineCorrected(source, WINDOWS)
    fixed = np.array([corrected.valuesByNanometers[k] for k in lam])

    def ratio(data):
        return float(data[(lam >= SORET[0]) & (lam <= SORET[1])].mean() /
                     data[(lam >= Q[0]) & (lam <= Q[1])].mean())

    return ratio(raw), ratio(fixed)


def series(paths):
    """(rawValues, baseValues) as arrays, in the given order."""
    pairs = [metrics(p) for p in paths]
    return np.array([r for r, _ in pairs]), np.array([b for _, b in pairs])


def changePercent(before, after):
    return (after.mean() / before.mean() - 1) * 100.0


def trendPercent(paths, values):
    """Least-squares trend across the set, as % of the mean (matches §16.12.11 A)."""
    times = np.array([os.path.getmtime(BASE + p) for p in paths])
    times = (times - times[0]) / 60.0
    slope = np.polyfit(times, values, 1)[0]
    return slope * (times.max() - times.min()) / abs(values.mean()) * 100.0


def collect():
    dilution, settling = [], []

    for label, weak, strong in DILUTION:
        weakRaw, weakBase = series(weak)
        strongRaw, strongBase = series(strong)
        dilution.append((label, changePercent(weakRaw, strongRaw), changePercent(weakBase, strongBase),
                         weakRaw.mean(), strongRaw.mean(), weakBase.mean(), strongBase.mean()))

    freshRaw, freshBase = series(FRESH_GREEN)
    agedRaw, agedBase = series(AGED_GREEN)
    settling.append(("green  fresh→aged  ~11 h", changePercent(freshRaw, agedRaw),
                     changePercent(freshBase, agedBase)))
    for name, paths in (("green  set B  ~28 min", SET_B), ("green  set C  ~33 min", SET_C)):
        raw, base = series(paths)
        settling.append((name, trendPercent(paths, raw), trendPercent(paths, base)))

    setSeries = []
    for name, paths in (("set B", SET_B), ("set C", SET_C)):
        times = np.array([os.path.getmtime(BASE + p) for p in paths])
        raw, base = series(paths)
        setSeries.append((name, (times - times[0]) / 60.0, raw, base))

    return dilution, settling, setSeries


def main():
    print(__doc__.split("Run:")[0].strip().splitlines()[0])
    print()
    dilution, settling, _ = collect()

    print("=== DILUTION INVARIANCE — change that should be ZERO")
    print("   %-24s %12s %12s   %-22s %-22s" % (
        "pair", "RAW %", "LIN.BASE %", "raw  weak → strong", "base  weak → strong"))
    print("   " + "-" * 100)
    for label, rawChange, baseChange, wr, sr, wb, sb in dilution:
        better = "raw" if abs(rawChange) < abs(baseChange) else "BASE"
        print("   %-24s %+11.2f %+11.2f   %8.3f → %-8.3f   %8.3f → %-8.3f   %s wins" % (
            label, rawChange, baseChange, wr, sr, wb, sb, better))
    print()

    print("=== SETTLING — change that should be ZERO, and the SIGN is the open question")
    print("   §11.4c predicts settling INFLATES S/Q (§11.4a measured 3.66 → 4.57 over 11 h)")
    print("   §16.12.11 A measured the SHIPPED metric DEFLATING over 30 min\n")
    print("   %-24s %12s %12s   %s" % ("interval", "RAW %", "LIN.BASE %", "signs"))
    print("   " + "-" * 74)
    for label, rawChange, baseChange in settling:
        signs = ("agree" if np.sign(rawChange) == np.sign(baseChange) else "⚠ OPPOSITE")
        print("   %-24s %+11.2f %+11.2f   %s" % (label, rawChange, baseChange, signs))
    print()

    rawMean = np.mean([abs(d[1]) for d in dilution])
    baseMean = np.mean([abs(d[2]) for d in dilution])
    print("=== SUMMARY")
    print("   mean |dilution error|      raw %.2f %%   linear baseline %.2f %%" % (rawMean, baseMean))
    print("   mean |settling error|      raw %.2f %%   linear baseline %.2f %%" % (
        np.mean([abs(s[1]) for s in settling]), np.mean([abs(s[2]) for s in settling])))


# --------------------------------------------------------------------------- rendering
def render(output="/home/nidwe72/development/spectracs/spectracs-references/tmp/baseline_vs_raw.png"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # dataviz reference palette, categorical slots 1-2, light mode (validated all-pairs:
    # CVD dE 24.7, normal-vision dE 33.6, contrast >= 3:1). Colour follows the METRIC VARIANT.
    RAW, BASE = "#2a78d6", "#eb6834"
    SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#dedcd6"

    dilution, settling, _ = collect()
    rawMean = np.mean([abs(d[1]) for d in dilution])
    baseMean = np.mean([abs(d[2]) for d in dilution])
    rawSettle = np.mean([abs(s[1]) for s in settling])
    baseSettle = np.mean([abs(s[2]) for s in settling])

    panels = [("A · Dilution invariance", [d[0] for d in dilution],
               [d[1] for d in dilution], [d[2] for d in dilution],
               "S/Q change between two dilutions (%)"),
              ("B · Settling", [s[0] for s in settling],
               [s[1] for s in settling], [s[2] for s in settling],
               "S/Q change across the interval (%)"),
              ("C · Mean |error| — the headline", ["dilution", "settling"],
               [rawMean, rawSettle], [baseMean, baseSettle],
               "mean absolute error (%)")]

    figure, grid = plt.subplots(1, 3, figsize=(16.0, 5.6), dpi=140, facecolor=SURFACE)
    figure.suptitle("Raw vs linear-baseline S/Q — every bar is a change that SHOULD BE ZERO",
                    fontsize=14, color=INK, y=0.985)
    figure.text(0.5, 0.925, "SPEC_capability_proof.md §2.1a · shorter bars are better · "
                            "the linear baseline halves BOTH error terms",
                ha="center", fontsize=9.5, color=MUTED)

    for axes, (title, labels, rawValues, baseValues, ylabel) in zip(grid, panels):
        axes.set_facecolor(SURFACE)
        axes.grid(True, axis="y", color=GRID, linewidth=0.8, zorder=0)
        axes.set_axisbelow(True)
        for side in ("top", "right"):
            axes.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            axes.spines[side].set_color(GRID)
        axes.tick_params(colors=MUTED, labelsize=9)

        positions = np.arange(len(labels))
        width = 0.36
        # 2 px surface gap between adjacent fills: drawn as a surface-coloured edge.
        axes.bar(positions - width / 2, rawValues, width, color=RAW, zorder=3,
                 edgecolor=SURFACE, linewidth=2, label="raw S/Q")
        axes.bar(positions + width / 2, baseValues, width, color=BASE, zorder=3,
                 edgecolor=SURFACE, linewidth=2, label="linear baseline S/Q")
        for position, value, colour in ([(p - width / 2, v, RAW) for p, v in zip(positions, rawValues)] +
                                        [(p + width / 2, v, BASE) for p, v in zip(positions, baseValues)]):
            axes.annotate("%+.1f" % value, xy=(position, value), ha="center",
                          va="bottom" if value >= 0 else "top",
                          xytext=(0, 4 if value >= 0 else -4), textcoords="offset points",
                          fontsize=9, color=MUTED, weight="bold")

        axes.axhline(0, color=INK, linewidth=1.2, zorder=4)
        axes.set_xticks(positions)
        axes.set_xticklabels([l.replace("  ", "\n", 1) for l in labels], fontsize=9, color=MUTED)
        axes.set_title(title, fontsize=12, color=INK, loc="left", pad=10)
        axes.set_ylabel(ylabel, fontsize=9.5, color=MUTED)
        low, high = axes.get_ylim()
        axes.set_ylim(low - 0.12 * (high - low), high + 0.12 * (high - low))

    grid[1].annotate("§11.4a's +24 % over 11 h REPRODUCED (3.66→4.57 = +24.3 %)\n"
                     "and the 30-min sets go DOWN — a timescale difference,\n"
                     "NOT the sign flip §2.1a suspected. Signs agree throughout.",
                     xy=(0.99, 0.72), xycoords="axes fraction", ha="right", va="top",
                     fontsize=9, color=INK,
                     bbox=dict(boxstyle="round,pad=0.5", facecolor="#f2f1ec",
                               edgecolor=GRID, linewidth=1))
    grid[0].legend(frameon=False, fontsize=10, labelcolor=MUTED, loc="lower left")

    figure.tight_layout(rect=(0, 0.01, 1, 0.915))
    figure.savefig(output, facecolor=SURFACE)
    print("wrote %s" % output)


if __name__ == "__main__":
    main()
    render()
