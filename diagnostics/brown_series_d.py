"""Series D — the brown oil, six re-seats of one fill. (SPEC_capture_quality.md §16.13)

This is §16.11.11 step 2's load-bearing measurement: the brown class's re-seat sigma, which decides
whether green-vs-brown discrimination works. §16.11.12 pre-registered the two outcomes BEFORE the data
existed -- sigma ~0.23-0.37 proves it, sigma ~0.83 says the rebuild helped green only.

It is deliberately run through the SAME harness as §16.12.11 (settling_sweep.measure/detrend), because
that section showed the green sets' raw CV is mostly a SETTLING TREND, not seating. A raw CV alone is
therefore not comparable across sessions; the residual is.

Reported here, in order:
  1  the raw record, run by run, in the §16.11.3a table shape
  2  raw vs residual CV for every input quantity -- brown against the green sets B and C
  3  discrimination on the shipped metric: gap, Cohen's d, margins to the shipped T = 10.6
  4  a chi-square interval on sigma, because n = 6 estimates a sigma only loosely

Diagnostic only -- nothing here is applied to the pipeline. Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/brown_series_d.py
"""
import os

import numpy as np
from scipy import stats

from settling_sweep import BASE, detrend, measure

SET_B = ["20270729B/%03d.pdf" % i for i in range(1, 7)]      # green, dilution #1, re-seats
SET_C = ["20270729C/%03d.pdf" % i for i in range(1, 7)]      # green, dilution #2, re-seats
SET_D = ["20260731A/%03d.pdf" % i for i in range(1, 7)]      # BROWN, one fill, re-seats

SHIPPED = "S/Q linear base"
THRESHOLD = 10.6                                             # §16.10.17d, shipped
ARCHIVED_BROWN_MEAN = 9.361                                  # 20260727C, old rig, 6 FILLS (§16.10.2)

METRICS = ["S/Q raw", SHIPPED, "A_Soret raw", "A_Q raw", "A_near 520-540", "A_far 600-630"]


def elapsed(paths):
    """Minutes since the set's first run. File mtimes are the real capture times -- the embedded
    workflow's header.timestampIso is None in every one of these PDFs (§16.12.11's note)."""
    times = np.array([os.path.getmtime(BASE + p) for p in paths])
    return (times - times.min()) / 60.0


def main():
    print(__doc__.split("Run:")[0].strip().splitlines()[0])
    print()

    runs = {p: measure(p) for p in SET_B + SET_C + SET_D}

    # ------------------------------------------------------------------ 1 the raw record
    print("=== SERIES D - brown, tmp/20260731A, ONE fill re-seated six times")
    print("   %-4s %6s %8s %8s %8s %9s %9s %8s" % (
        "run", "min", "A_Soret", "A_Q", "A_near", "A_far", "S/Q raw", "S/Q_lin"))
    print("   " + "-" * 66)
    minutes = elapsed(SET_D)
    for path, minute in zip(SET_D, minutes):
        r = runs[path]
        print("   %-4s %6.1f %8.3f %8.3f %8.3f %9.3f %9.3f %8.3f" % (
            path[-7:-4], minute, r["A_Soret raw"], r["A_Q raw"], r["A_near 520-540"],
            r["A_far 600-630"], r["S/Q raw"], r[SHIPPED]))
    print()

    # ------------------------------------------------------------------ 2 raw vs residual CV
    print("=== RAW vs RESIDUAL CV - brown D against the green sets")
    print("   %-18s %19s %19s %19s" % ("", "set B (green)", "set C (green)", "SET D (BROWN)"))
    print("   %-18s %6s %5s %6s %6s %5s %6s %6s %5s %6s" % (
        "metric", "CV%", "res%", "t", "CV%", "res%", "t", "CV%", "res%", "t"))
    print("   " + "-" * 78)
    for metric in METRICS:
        cells = []
        for paths in (SET_B, SET_C, SET_D):
            rawCv, residCv, _, t = detrend(elapsed(paths), [runs[p][metric] for p in paths])
            cells += [rawCv, residCv, t]
        print("   %-18s %6.2f %5.2f %6.2f %6.2f %5.2f %6.2f %6.2f %5.2f %6.2f" % (metric, *cells))
    print("   (t: 4 df, so |t| > 2.78 is p < 0.05 two-sided)")
    print()

    print("   trend across each set, %% of mean:")
    for metric in METRICS:
        trends = [detrend(elapsed(p), [runs[q][metric] for q in p])[2] for p in (SET_B, SET_C, SET_D)]
        print("     %-18s B %+7.2f%%   C %+7.2f%%   D %+7.2f%%" % (metric, *trends))
    print()

    # ------------------------------------------------------------------ 3 discrimination
    green = np.array([runs[p][SHIPPED] for p in SET_B + SET_C])
    brown = np.array([runs[p][SHIPPED] for p in SET_D])
    greenMean, greenSd = green.mean(), green.std(ddof=1)
    brownMean, brownSd = brown.mean(), brown.std(ddof=1)
    gap = greenMean - brownMean
    pooledSd = np.sqrt((greenSd ** 2 + brownSd ** 2) / 2)

    print("=== DISCRIMINATION on %s" % SHIPPED)
    print("   green B+C  n=%2d  mean %7.4f  sd %6.4f  CV %5.2f%%" % (
        len(green), greenMean, greenSd, 100 * greenSd / greenMean))
    print("   BROWN D    n=%2d  mean %7.4f  sd %6.4f  CV %5.2f%%" % (
        len(brown), brownMean, brownSd, 100 * brownSd / brownMean))
    # Two pooled-SD conventions are in circulation and they DIVERGE when the groups differ in size,
    # which they do here (12 green against 6 brown). Report both so the figure is never quoted without
    # its recipe -- DOC_metric_algebra.md Appendix B / SPEC_capture_quality.md 16.13.5.
    dfWeighted = np.sqrt(((len(green) - 1) * greenSd ** 2 + (len(brown) - 1) * brownSd ** 2)
                         / (len(green) + len(brown) - 2))
    hedges = (gap / dfWeighted) * (1.0 - 3.0 / (4.0 * (len(green) + len(brown) - 2) - 1.0))
    print("   gap %.4f = %.1f%% of the brown mean" % (gap, 100 * gap / brownMean))
    print("   Cohen d, RMS pooled sd        %.4f -> %5.2f   <- what earlier revisions quoted" % (
        pooledSd, gap / pooledSd))
    print("   Cohen d, df-weighted pooled   %.4f -> %5.2f   <- conventional at UNEQUAL n (%d vs %d)" % (
        dfWeighted, gap / dfWeighted, len(green), len(brown)))
    print("   Hedges g (df-weighted, small-n corrected)    %5.2f   <- quote this one externally" % hedges)
    print("   archived brown %.3f (20260727C, old rig, 6 FILLS) -> %.3f, delta %+.2f%%" % (
        ARCHIVED_BROWN_MEAN, brownMean, 100 * (brownMean - ARCHIVED_BROWN_MEAN) / ARCHIVED_BROWN_MEAN))
    print("   T = %.1f : green %+.2f sigma above | brown %+.2f sigma below" % (
        THRESHOLD, (greenMean - THRESHOLD) / greenSd, (THRESHOLD - brownMean) / brownSd))
    print("   midpoint of the two class means would sit at %.3f" % ((greenMean + brownMean) / 2))
    print()

    # ------------------------------------------------------------------ 4 how well is sigma known?
    n = len(brown)
    lo = brownSd * np.sqrt((n - 1) / stats.chi2.ppf(0.975, n - 1))
    hi = brownSd * np.sqrt((n - 1) / stats.chi2.ppf(0.025, n - 1))
    print("=== HOW WELL IS THE BROWN SIGMA KNOWN? (n = %d)" % n)
    print("   sigma %.4f, 95%% chi-square interval [%.4f, %.4f]" % (brownSd, lo, hi))
    print("   false-GREEN rate at T = %.1f, t-distribution on %d df (§16.10.11a: the error is" % (
        THRESHOLD, n - 1))
    print("   heavy-tailed, so the Gaussian is optimistic exactly where it matters):")
    for label, sd in [("point estimate", brownSd), ("sigma upper 95%", hi),
                      ("if brown were green-like (0.367)", 0.367),
                      ("old-rig assumption (0.83)", 0.83)]:
        margin = (THRESHOLD - brownMean) / sd
        print("     %-34s sd %.3f -> %5.2f sigma  %8.4f%% (t)  %10.6f%% (gauss)" % (
            label, sd, margin, 100 * stats.t.sf(margin, n - 1), 100 * stats.norm.sf(margin)))
    greenMargin = (greenMean - THRESHOLD) / greenSd
    print("   green false-BROWN: %.2f sigma -> %.4f%% (t, %d df)" % (
        greenMargin, 100 * stats.t.sf(greenMargin, len(green) - 1), len(green) - 1))


if __name__ == "__main__":
    main()
