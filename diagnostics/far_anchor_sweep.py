"""Sweep the linear baseline's FAR anchor window (SPEC_capture_quality.md §16.12.12).

§16.12.12 showed the shipped far window 600-630 nm is NOT oil-quiet: it stands on real green-pigment
absorption (the flank toward the chlorophyll Q max near 665 nm), 5.1 sigma, and ~3.4x stronger in green
than in brown. Because it sets the fitted baseline's SLOPE, and that slope is subtracted from a small Q
denominator, the contamination does not cancel in the ratio.

§16.11.14 swept the Soret band's edges. The BASELINE windows have never been swept. This does that, two ways:

  SWEEP 1  right edge pulled in, left edge pinned at 600  - "chop off the contaminated red end"
  SWEEP 2  fixed 20 nm width slid left                    - separates WHERE from HOW WIDE

Each candidate is judged on three things that must be read together:
  * DISCRIMINATION - leave-one-FILL-out errors + Cohen's d (does green still separate from brown?)
  * PRECISION      - median within-fill CV (does the metric get noisier?)
  * SETTLING       - the §16.12.11 A time trend on sets B and C (does the drift shrink?)

A window that keeps discrimination, keeps precision AND shrinks the trend is a free win. One that trades
them tells us how much of today's separation rests on window placement - which is the real question.

Run:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/far_anchor_sweep.py
"""
import os

import numpy as np

from far_anchor_probe import spectra
from metric_bench import BASE, bestThreshold, feature, plugin
from settling_sweep import detrend

SORET, Q = plugin.PB_SORET_BAND, plugin.PB_Q_BAND
NEAR = plugin.PB_BASELINE_WINDOWS[0]                       # 520-540, held fixed throughout
SHIPPED_FAR = plugin.PB_BASELINE_WINDOWS[1]                # 600-630

# 07-27 fills are the established scoring basis (§16.10.9 quotes 1/25 errors on exactly these four).
# The 07-29 sets are a later session and BOTH green, so they are reported separately, never mixed into
# the headline score - adding two same-class fills would flatter any threshold.
SCORING_FILLS = [("green", "green B", ["20260727B/%03d.pdf" % i for i in range(1, 10)]),
                 ("green", "green E", ["20260727E/%03d.pdf" % i for i in range(1, 8)]),
                 ("brown", "brown C", ["20260727C/%03d.pdf" % i for i in range(1, 7)]),
                 ("brown", "brown D", ["20260727D/%03d.pdf" % i for i in range(1, 4)])]

SETTLING_SETS = [("set B", ["20270729B/%03d.pdf" % i for i in range(1, 7)]),
                 ("set C", ["20270729C/%03d.pdf" % i for i in range(1, 7)])]

SWEEP_1 = [(600.0, 630.0), (600.0, 625.0), (600.0, 620.0), (600.0, 615.0), (600.0, 610.0)]
SWEEP_2 = [(610.0, 630.0), (605.0, 625.0), (600.0, 620.0), (595.0, 615.0), (590.0, 610.0), (585.0, 605.0)]


def load(paths):
    """[(path, Spectrum)] - each PDF opened ONCE; the sweep only re-runs the cheap baseline fit."""
    out = []
    for path in paths:
        found = spectra(path)
        spectrum = type("S", (), {})()
        spectrum.valuesByNanometers = found["ABSORPTION"]
        out.append((path, spectrum))
    return out


def metric(spectrum, far):
    """S/Q with the linear baseline fitted through (NEAR, far)."""
    from sciens.spectracs.model.spectral.Spectrum import Spectrum
    source = Spectrum()
    source.valuesByNanometers = dict(spectrum.valuesByNanometers)
    corrected = feature.linearBaselineCorrected(source, (NEAR, far))
    if corrected is None:
        return float("nan")
    lam = np.array(sorted(corrected.valuesByNanometers))
    values = np.array([corrected.valuesByNanometers[k] for k in lam])

    def band(window):
        return values[(lam >= window[0]) & (lam <= window[1])].mean()

    denominator = band(Q)
    return float(band(SORET) / denominator) if denominator else float("nan")


def score(far, scoring, settling):
    """(lofoErrors, cohenD, cleanGap, medianWithinFillCv, meanTrendPct, meanResidualCv)."""
    runs = [(label, fillName, metric(spectrum, far))
            for (label, fillName, loaded) in scoring for _, spectrum in loaded]

    green = np.array([v for label, _, v in runs if label == "green"])
    brown = np.array([v for label, _, v in runs if label == "brown"])
    pooled = np.sqrt(((len(green) - 1) * green.var(ddof=1) + (len(brown) - 1) * brown.var(ddof=1)) /
                     (len(green) + len(brown) - 2))
    cohenD = (green.mean() - brown.mean()) / pooled if pooled else 0.0
    gap = green.min() - brown.max()                       # >0 means the classes do not overlap at all

    values = [v for _, _, v in runs]
    labels = [label for label, _, v in runs]
    lofo = 0
    for _, fillName, _ in scoring:
        trainValues = [v for _, name, v in runs if name != fillName]
        trainLabels = [label for label, name, _ in runs if name != fillName]
        cut, greenIsHigh, _ = bestThreshold(trainValues, trainLabels)
        lofo += sum(1 for label, name, v in runs
                    if name == fillName and ((v > cut) == greenIsHigh) != (label == "green"))

    withinFill = []
    for _, fillName, _ in scoring:
        group = np.array([v for _, name, v in runs if name == fillName])
        withinFill.append(group.std(ddof=1) / abs(group.mean()) * 100.0)

    trends, residuals = [], []
    for _, loaded in settling:
        times = np.array([os.path.getmtime(BASE + path) for path, _ in loaded])
        times = (times - times[0]) / 60.0
        _, residualCv, trend, _ = detrend(times, [metric(s, far) for _, s in loaded])
        trends.append(trend)
        residuals.append(residualCv)

    return lofo, cohenD, gap, float(np.median(withinFill)), float(np.mean(trends)), float(np.mean(residuals))


def report(title, windows, scoring, settling, runCount):
    print("=== %s" % title)
    print("   %-14s %8s %7s %9s %10s %10s %10s" % (
        "far window", "LOFO", "|d|", "gap", "CV/fill%", "trend%", "resid CV%"))
    print("   " + "-" * 76)
    for far in windows:
        lofo, cohenD, gap, cv, trend, residual = score(far, scoring, settling)
        marker = "  <- SHIPPED" if far == SHIPPED_FAR else ""
        print("   %-14s %5d/%-2d %7.2f %9s %10.2f %10.2f %10.2f%s" % (
            "%.0f-%.0f nm" % far, lofo, runCount, abs(cohenD),
            ("+%.3f" % gap) if gap > 0 else "OVERLAP", cv, trend, residual, marker))
    print()


def main():
    print(__doc__.split("Run:")[0].strip().splitlines()[0])
    print()
    scoring = [(label, fillName, load(paths)) for label, fillName, paths in SCORING_FILLS]
    settling = [(name, load(paths)) for name, paths in SETTLING_SETS]
    runCount = sum(len(loaded) for _, _, loaded in scoring)

    print("   discrimination: %d runs, 4 fills, 2026-07-27  (§16.10.9's basis)" % runCount)
    print("   settling:       sets B and C, 2026-07-29, mean of the two")
    print("   LOFO  = leave-one-FILL-out errors      |d| = Cohen's d, green vs brown")
    print("   gap   = green.min - brown.max (>0 = classes fully separated)")
    print("   trend = §16.12.11 A time trend across a set; resid CV = after detrending\n")

    report("SWEEP 1 - right edge pulled in, left edge pinned at 600 nm",
           SWEEP_1, scoring, settling, runCount)
    report("SWEEP 2 - fixed 20 nm width, window slid left",
           SWEEP_2, scoring, settling, runCount)


if __name__ == "__main__":
    main()
