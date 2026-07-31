"""Where do we stand with set B run 002 excluded? (Edwin, 2026-07-31)

B002 is §16.11.7's largest tilt event, flagged there BEFORE any of the §16.12 work — its per-run tilt slope
is -0.0398 against <= -0.0204 for every other run in the set. This sweep independently finds it anomalous in
three more ways (quiet-window shape ratio 1.019 vs ~0.71; A_far -38.9 %; A_Q -18.7 % while A_Soret is +0.6 %).

⚠ §16.11.11's V2 criterion is "exclusion = documented physical cause only", and an exclusion decided AFTER
seeing that a point is inconvenient is §16.10.16's trap. So everything is reported BOTH WAYS and the reader
decides. Nothing here is adopted.

Note: the DISCRIMINATION scores (LOFO / d / gap) are computed on the 2026-07-27 fills, which contain no B002 —
they are unchanged by this exclusion and are not reprinted.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/without_b002.py
"""
import os

import numpy as np

from baseline_variants import cv, variants
from metric_bench import BASE
from settling_sweep import detrend, measure

SET_B = ["20270729B/%03d.pdf" % i for i in range(1, 7)]
SET_C = ["20270729C/%03d.pdf" % i for i in range(1, 7)]
DROPPED = "20270729B/002.pdf"

METRICS = ["S/Q raw", "S/Q linear base", "A_Soret raw", "A_Q raw", "A_near 520-540", "A_far 600-630"]
VARIANTS = ["raw", "offset NEAR only", "offset FAR only", "linear NEAR+FAR",
            "lin 2win LSQ", "full-range line", "poly2 ex-bands", "AsLS 1e5/0.01"]


def elapsed(paths):
    times = np.array([os.path.getmtime(BASE + p) for p in paths])
    return (times - times.min()) / 60.0


def block(paths, values):
    """(rawCV, residCV, trend, t) for one metric over one set."""
    return detrend(elapsed(paths), values)


def main():
    print(__doc__.split("Run:")[0].strip().splitlines()[0])
    print()

    full = {p: measure(p) for p in SET_B + SET_C}
    keptB = [p for p in SET_B if p != DROPPED]

    # ------------------------------------------------------------------ set B, both ways
    print("=== SET B — all 6 runs vs 5 runs (002 dropped)")
    print("   %-18s %19s   %19s" % ("metric", "ALL 6", "WITHOUT 002"))
    print("   %-18s %8s %5s %5s   %8s %5s %5s" % ("", "CV%", "res%", "t", "CV%", "res%", "t"))
    print("   " + "-" * 66)
    for metric in METRICS:
        a = block(SET_B, [full[p][metric] for p in SET_B])
        b = block(keptB, [full[p][metric] for p in keptB])
        print("   %-18s %8.2f %5.2f %5.2f   %8.2f %5.2f %5.2f" % (
            metric, a[0], a[1], a[3], b[0], b[1], b[3]))
    print("   (t: 4 df needs |t|>2.78 with 6 runs; 3 df needs |t|>3.18 with 5)\n")

    # ------------------------------------------------------------------ pooled
    print("=== POOLED B+C — the §16.12.11 A headline")
    print("   %-18s %10s %10s   %10s %10s" % ("metric", "CV% all", "resid%", "CV% w/o", "resid% w/o"))
    print("   " + "-" * 66)
    for metric in METRICS:
        row = []
        for bPaths in (SET_B, keptB):
            rawParts, residParts, count = [], [], 0
            for paths in (bPaths, SET_C):
                times = elapsed(paths)
                values = np.array([full[p][metric] for p in paths])
                mean = values.mean()
                slope, intercept = np.polyfit(times, values, 1)
                rawParts.append((values - mean) / mean)
                residParts.append((values - (slope * times + intercept)) / mean)
                count += len(values)
            row.append(float(np.sqrt((np.concatenate(rawParts) ** 2).sum() / (count - 2))) * 100)
            row.append(float(np.sqrt((np.concatenate(residParts) ** 2).sum() / (count - 4))) * 100)
        print("   %-18s %10.2f %10.2f   %10.2f %10.2f" % (metric, row[0], row[1], row[2], row[3]))
    print()

    # ------------------------------------------------------------------ variants
    print("=== BASELINE VARIANTS — post-rebuild CV %, and the B→C dilution step")
    variantValues = {p: variants(p) for p in SET_B + SET_C}
    print("   %-18s %19s   %19s" % ("variant", "ALL 6", "WITHOUT 002"))
    print("   %-18s %7s %7s %5s   %7s %7s %5s" % (
        "", "B CV%", "POSTavg", "dil%", "B CV%", "POSTavg", "dil%"))
    print("   " + "-" * 68)
    cCv = None
    for variant in VARIANTS:
        cValues = [variantValues[p][variant] for p in SET_C]
        cCv = cv(cValues)
        out = []
        for bPaths in (SET_B, keptB):
            bValues = [variantValues[p][variant] for p in bPaths]
            out.append(cv(bValues))
            out.append(np.mean([cv(bValues), cCv]))
            out.append((np.mean(cValues) / np.mean(bValues) - 1) * 100)
        print("   %-18s %7.2f %7.2f %+5.1f   %7.2f %7.2f %+5.1f" % (
            variant, out[0], out[1], out[2], out[3], out[4], out[5]))
    print()

    # ------------------------------------------------------------------ the budget
    print("=== §16.11.9's ERROR BUDGET — the `jar` arm predicted 2.98 %")
    for label, bPaths in (("all 6", SET_B), ("without 002", keptB)):
        bValues = [variantValues[p]["linear NEAR+FAR"] for p in bPaths]
        observed = cv(bValues)
        _, residual, _, _ = block(bPaths, [full[p]["S/Q linear base"] for p in bPaths])
        print("   set B %-12s observed CV %5.2f %%   detrended %5.2f %%   "
              "jar-arm 2.98 %% is %s" % (
                  label, observed, residual,
                  "MATCHED" if abs(observed - 2.98) < 0.5 else "OVER-predicting"))
    print()

    # §16.12.14's headline: the linear baseline's GAIN over raw, pre vs post rebuild.
    print("=== §16.12.14's HEADLINE re-checked — the baseline's gain over raw")
    for label, bPaths in (("all 6", SET_B), ("without 002", keptB)):
        rawCv = np.mean([cv([variantValues[p]["raw"] for p in bPaths]),
                         cv([variantValues[p]["raw"] for p in SET_C])])
        baseCv = np.mean([cv([variantValues[p]["linear NEAR+FAR"] for p in bPaths]),
                          cv([variantValues[p]["linear NEAR+FAR"] for p in SET_C])])
        print("   POST gain (%-11s) = %5.2f / %5.2f = %.2fx   vs PRE-rebuild 1.27x" % (
            label, rawCv, baseCv, rawCv / baseCv))


if __name__ == "__main__":
    main()
