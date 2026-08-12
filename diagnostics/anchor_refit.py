"""Re-derive the pedestal residual `r_Q` for ALTERNATIVE far anchors, on the archive.

SPEC_capture_quality.md §16.29 established that the shipped metric is effectively a `QB` measurement
(r = +0.933 against 1/QB) and that `QB` collapses for green oils. §16.29.3 traced the collapse to the far
anchor sitting ON the protochlorophyll Qy band, so the fitted line tilts up toward the red and subtracts
pigment from the Q band.

The obvious response — move the anchor off the band — makes dilution invariance WORSE when tried with the
shipped `r_Q`, because `r_Q` was fitted to the 620-630 geometry. This script asks the fair question instead:

    refit `r_Q` for each anchor, then compare.

⚠ It CHANGES NOTHING. It reports. `PB_R_Q` and `PB_BASELINE_WINDOWS` are read, never written.

⚠ `r_Q` is an instrument constant that §16.19 shows does not survive a rebuild, and this refits it on the
pre-2026-08-12 archive. The numbers answer "is this geometry better in principle", NOT "ship this constant".

Run:  PYTHONPATH=.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins \
      python3 diagnostics/anchor_refit.py
"""
import os
import sys
import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from settling_sweep import despikedAbsorption, asArrays, bandMean, feature, plugin, BASE

# The shipped Soret window (448-460), not settling_sweep's pinned legacy 440-460: this is a forward-looking
# comparison, and every anchor below is scored on the same numerator so only the ANCHOR varies.
SORET = plugin.PB_SORET_BAND
Q = plugin.PB_Q_BAND
NEAR = (520.0, 540.0)

# ⭐ The candidates. "flat" is Edwin's single-quiet-frequency idea: no red anchor at all, just subtract the
# near window as a constant. The valley windows sit between the Q band (ends 580) and the far band (starts
# ~615), minus the 607 nm lamp line — whose artefact in A was measured wandering to 613 nm on 2026-08-12,
# hence 592 rather than 610 as the blue edge.
ANCHORS = [("620-630  SHIPPED", (620.0, 630.0)),
           ("615-630", (615.0, 630.0)),
           ("600-630  legacy", (600.0, 630.0)),
           ("592-604  valley", (592.0, 604.0)),
           ("585-605  wide valley", (585.0, 605.0)),
           ("flat (no red anchor)", None)]

SETS = [("Kiendler A", "Kiendler", ["20260801A/%03d.pdf" % i for i in range(1, 7)]),
        ("Kiendler B", "Kiendler", ["20260801B/%03d.pdf" % i for i in range(1, 3)]),
        ("Kiendler C", "Kiendler", ["20260801C/%03d.pdf" % i for i in range(1, 3)]),
        ("Steirerkraft B", "Steirerkraft", ["20270729B/%03d.pdf" % i for i in range(1, 7)]),
        ("Steirerkraft C", "Steirerkraft", ["20270729C/%03d.pdf" % i for i in range(1, 7)]),
        ("S-Budget D", "S-Budget", ["20260731A/%03d.pdf" % i for i in range(1, 7)])]
CLASS = {"Kiendler": "green", "Steirerkraft": "green", "S-Budget": "brown"}

# Out-of-sample dilution check: the ONLY controlled concentration change in the archive (§16.29.1).
# Same oil, same jar, 10 mL -> 8 mL of IPA, k = 1.25. Settled runs only.
DILUTION = ("20260812_BillaClever/003.pdf", "20260812_BillaCleverB/003.pdf", 1.25)


def bands(path, window):
    """(B_Soret, B_Q) above the baseline this anchor defines."""
    spectrum = despikedAbsorption(path)
    if window is None:
        lam, raw = asArrays(spectrum)
        offset = bandMean(lam, raw, NEAR)
        return bandMean(lam, raw, SORET) - offset, bandMean(lam, raw, Q) - offset
    lam, values = asArrays(feature.linearBaselineCorrected(spectrum, (NEAR, window)))
    return bandMean(lam, values, SORET), bandMean(lam, values, Q)


def cohensD(a, b):
    a, b = np.asarray(a), np.asarray(b)
    pooled = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2.0)
    return abs(a.mean() - b.mean()) / pooled if pooled else float("inf")


def main():
    print("Archive: %d sets, %d runs.  Soret %s  Q %s  near anchor %s"
          % (len(SETS), sum(len(p) for _, _, p in SETS), SORET, Q, NEAR))
    print("⚠ r_Q refitted PER ANCHOR on Kiendler, exactly as `pedestal_correction.py` does for the shipped one.\n")

    measured = {}
    for label, window in ANCHORS:
        measured[label] = {name: [bands(p, window) for p in paths] for name, _, paths in SETS}

    print("=== 1  THE REFIT — straight-line test  B_Soret = M_inf * B_Q + k,  r_Q = -k / M_inf")
    print("   %-22s %10s %10s %8s %10s %10s" % ("anchor", "M_inf", "k", "t(k)", "r_Q", "shipped"))
    print("   " + "-" * 76)
    rq = {}
    for label, _ in ANCHORS:
        runs = measured[label]
        names = [n for n, oil, _ in SETS if oil == "Kiendler"]
        x = np.concatenate([[q for _, q in runs[n]] for n in names])
        y = np.concatenate([[s for s, _ in runs[n]] for n in names])
        fit = stats.linregress(x, y)
        t = fit.intercept / fit.intercept_stderr if fit.intercept_stderr else float("nan")
        rq[label] = -fit.intercept / fit.slope if fit.slope else float("nan")
        print("   %-22s %10.3f %10.4f %8.2f %10.4f %10s"
              % (label, fit.slope, fit.intercept, t, rq[label],
                 "%.4f" % plugin.PB_R_Q if label.startswith("620-630") else ""))

    print("\n=== 2  WHAT IT DOES TO THE DENOMINATOR  (B_Q per oil, and the smallest one)")
    print("   %-22s %10s %10s %10s %12s" % ("anchor", "Kiendler", "Steirerkr", "S-Budget", "min B_Q"))
    print("   " + "-" * 68)
    for label, _ in ANCHORS:
        runs = measured[label]
        per = {}
        for oil in ("Kiendler", "Steirerkraft", "S-Budget"):
            names = [n for n, o, _ in SETS if o == oil]
            per[oil] = float(np.mean([q for n in names for _, q in runs[n]]))
        allq = [q for n in runs for _, q in runs[n]]
        print("   %-22s %10.4f %10.4f %10.4f %12.4f"
              % (label, per["Kiendler"], per["Steirerkraft"], per["S-Budget"], min(allq)))

    print("\n=== 3  THE CORRECTED METRIC  M = B_Soret / (B_Q - r_Q),  each anchor with ITS OWN r_Q")
    print("   %-22s %10s %10s %10s %9s %9s" % ("anchor", "Kiendler", "Steirerkr", "S-Budget", "d(g/b)", "CV%"))
    print("   " + "-" * 76)
    for label, _ in ANCHORS:
        runs, r = measured[label], rq[label]
        vals, per = {}, {}
        for oil in ("Kiendler", "Steirerkraft", "S-Budget"):
            names = [n for n, o, _ in SETS if o == oil]
            v = [s / (q - r) for n in names for s, q in runs[n]]
            vals[oil] = v
            per[oil] = float(np.mean(v))
        green = vals["Kiendler"] + vals["Steirerkraft"]
        cv = float(np.mean([np.std(vals[o], ddof=1) / abs(np.mean(vals[o])) * 100
                            for o in vals]))
        print("   %-22s %10.3f %10.3f %10.3f %9.2f %9.1f"
              % (label, per["Kiendler"], per["Steirerkraft"], per["S-Budget"],
                 cohensD(green, vals["S-Budget"]), cv))

    print("\n=== 4  ⭐ THE OUT-OF-SAMPLE DILUTION TEST  (BillaClever, k = 1.25, settled runs)")
    print("   ⚠ NOT in the refit set — a different oil, five days later, on the widened ROI.")
    print("   %-22s %11s %11s %10s %11s" % ("anchor", "A (10 mL)", "B (8 mL)", "shift", "uncorrected"))
    print("   " + "-" * 70)
    for label, window in ANCHORS:
        r = rq[label]
        sa, qa = bands(DILUTION[0], window)
        sb, qb = bands(DILUTION[1], window)
        ca, cb = sa / (qa - r), sb / (qb - r)
        ua, ub = sa / qa, sb / qb
        print("   %-22s %11.3f %11.3f %9.1f%% %10.1f%%"
              % (label, ca, cb, 100 * (cb - ca) / ca, 100 * (ub - ua) / ua))

    print("\n⚠ Reminder: every r_Q above is fitted on ONE oil (Kiendler) on ONE rig state, and §16.19 shows")
    print("   the constant does not survive a mechanical rebuild. This ranks GEOMETRIES, not constants.")


if __name__ == "__main__":
    main()
