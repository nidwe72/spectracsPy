"""Pool EVERY within-oil dilution pair already on disk, and fit the log-log slope.
   (SPEC_capture_quality.md 16.10.8 / 16.14 -- the dilution-invariance question, answered from the archive)

16.11.6 tested dilution invariance on ONE pair (sets B/C) spanning only 1.17x, and 16.10.8 called the
result a power failure. But three within-oil dilution pairs exist across the archive, two of them
spanning 1.5x. Pooling them is free and gives a far tighter bound on the log-log slope s, where s = 0
means perfect dilution invariance.

CAVEAT, and it is the important one: each pair is a different FILL as well as a different dilution, so
the fitted slope contains fill-to-fill scatter. It is therefore an UPPER bound on the true dilution
dependence -- which is the conservative direction.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/dilution_pooled.py
"""
import numpy as np
from metric_walkthrough import walk

# same oil, two deliberate dilutions, 4 runs each (UC2/UC3, 2026-07-21, PRE-rebuild)
PAIRS = [
    ("green K/L (pre-rebuild)", 2.0, ["measurement_report_oilK_%03d.pdf" % i for i in (1,2,3,4)],
                                3.0, ["measurement_report_oilL_%03d.pdf" % i for i in (1,2,3,4)]),
    ("brown N/M (pre-rebuild)", 2.0, ["measurement_report_oilN_%03d.pdf" % i for i in (1,2)],
                                3.0, ["measurement_report_oilM_%03d.pdf" % i for i in (1,2,3,4)]),
    ("green B/C (post-rebuild)", 0.197, ["20270729B/%03d.pdf" % i for i in range(1,7)],
                                 0.230, ["20270729C/%03d.pdf" % i for i in range(1,7)]),
]

print("%-26s %6s %8s %8s %8s %9s" % ("pair", "span", "lo mean", "hi mean", "change", "slope s"))
print("-"*72)
slopes, weights = [], []
for label, cLo, lo, cHi, hi in PAIRS:
    try:
        vLo = np.array([walk(p)[0]["S/Q lin"] for p in lo])
        vHi = np.array([walk(p)[0]["S/Q lin"] for p in hi])
    except Exception as e:
        print("%-26s  SKIPPED (%s)" % (label, type(e).__name__)); continue
    span = cHi/cLo
    s = np.log(vHi.mean()/vLo.mean()) / np.log(span)
    seLo, seHi = vLo.std(ddof=1)/np.sqrt(len(vLo)), vHi.std(ddof=1)/np.sqrt(len(vHi))
    seRatio = np.sqrt((seLo/vLo.mean())**2 + (seHi/vHi.mean())**2)
    seS = seRatio/np.log(span)
    print("%-26s %6.2fx %8.3f %8.3f %+7.1f%% %6.2f +/- %.2f"
          % (label, span, vLo.mean(), vHi.mean(), 100*(vHi.mean()/vLo.mean()-1), s, seS))
    slopes.append(s); weights.append(1/seS**2)

slopes, weights = np.array(slopes), np.array(weights)
pooled = (slopes*weights).sum()/weights.sum()
sePooled = 1/np.sqrt(weights.sum())
print()
print("POOLED log-log slope  s = %+.3f +/- %.3f   (t = %.2f)" % (pooled, sePooled, pooled/sePooled))
print("   s = 0 means PERFECTLY dilution-invariant.")
print("   95%% CI: %+.3f .. %+.3f" % (pooled-1.96*sePooled, pooled+1.96*sePooled))
print()
for R in (1.5, 2.0, 4.0):
    lo, hi = (pooled-1.96*sePooled), (pooled+1.96*sePooled)
    print("   over a %.1fx dilution change the index moves %+.1f%% (95%% CI %+.1f%% .. %+.1f%%)"
          % (R, 100*(R**pooled-1), 100*(R**lo-1), 100*(R**hi-1)))
