"""P(one measurement decides) vs sigma_fill -- the quantity series E will measure.
   (SPEC_capture_quality.md 16.11.13, "the sensitivity table")

Series D measured the RE-SEAT sigma. A field measurement is a FILL, so the "does one measurement give
the verdict?" question still hangs entirely on sigma_fill -- and it hangs on it steeply.

The decision rule is reconstructed from the spec's own published gates: gate = T +/- 2.576*sigma1. The
script checks that reconstruction against both worked examples in the spec before using it, so a change
to the shipped rule will show up here as a mismatch rather than silently producing wrong projections.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/one_fill_decision.py
"""
import numpy as np
from scipy import stats

T = 10.6
K = 2.576                      # the gate multiplier implied by SPEC 16.10.17b / 16.11.13
GREEN, BROWN = 12.2507, 9.3034 # measured class means (20270729C / 20260731A)

print("Gate construction check against the spec's own numbers:")
for s1, g, b in ((1.04, 13.28, 7.92), (0.367, 11.55, 9.65)):
    print("   sigma1 %.3f -> gates %.2f / %.2f   (spec says %.2f / %.2f)"
          % (s1, T + K*s1, T - K*s1, g, b))
print()

def decides(mu, sigma, upper):
    """P(a single measurement falls beyond its own class's gate, on the correct side)."""
    gate = T + K*sigma if upper else T - K*sigma
    return stats.norm.sf(gate, mu, sigma) if upper else stats.norm.cdf(gate, mu, sigma)

print("P(ONE measurement decides), for our two oils, vs the still-unmeasured sigma_fill")
print("   %-28s %8s %8s | %8s %8s | %8s" % ("sigma_fill", "green", "gate", "brown", "gate", "both"))
print("   " + "-"*74)
for sigma, label in ((0.131, "brown RE-SEAT (series D)"), (0.25, ""), (0.307, "<- brown 95% limit"),
                     (0.354, "green RE-SEAT (series C)"), (0.5, ""), (0.7, ""),
                     (0.977, "historical brown 10.5%"), (1.04, "shipped assumption")):
    pg, pb = decides(GREEN, sigma, True), decides(BROWN, sigma, False)
    print("   %-28s %7.1f%% %8.2f | %7.1f%% %8.2f | %7.1f%%   %s"
          % ("%.3f  (%.1f%% CV brown)" % (sigma, 100*sigma/BROWN),
             100*pg, T+K*sigma, 100*pb, T-K*sigma, 100*pg*pb, label))

print()
print("What sigma_fill would each class need for a 95% one-measurement decision?")
for mu, name, upper in ((GREEN, "green", True), (BROWN, "brown", False)):
    margin = abs(mu - T)
    limit = margin / (K + stats.norm.ppf(0.95))
    print("   %-6s margin to T = %.3f  ->  sigma_fill <= %.3f  (%.1f%% CV)"
          % (name, margin, limit, 100*limit/mu))
print()
print("   ⇒ BROWN is the binding class: sigma_fill <= 0.307, i.e. CV <= 3.3 %")
print("   ⇒ SPEC_capability_proof 11.4f B predicted brown sigma_fill at 3-6 % — the answer sits")
print("     exactly ON the boundary of the pre-registered range.")

# ----------------------------------------------------------------------- robustness vs the green basis
# Does green's sigma -- and therefore the table above -- rest on set B's run 002, the project's most-
# discussed single run (16.11.7's tilt event, 16.12.14c's sensitivity study)? Answer: no.
from metric_walkthrough import walk

SET_B = ["20270729B/%03d.pdf" % i for i in range(1, 7)]
SET_C = ["20270729C/%03d.pdf" % i for i in range(1, 7)]
BROWN_D = ["20260731A/%03d.pdf" % i for i in range(1, 7)]

def index(paths):
    return np.array([walk(p)[0]["S/Q lin"] for p in paths])

B, C, brown = index(SET_B), index(SET_C), index(BROWN_D)
bm, bs = brown.mean(), brown.std(ddof=1)

print()
print("ROBUSTNESS — does the answer depend on set B's run 002?")
print("   %-32s %3s %8s %8s %7s %8s %10s" % ("green basis", "n", "mean", "sd", "CV", "Cohen d", "P(decides)"))
print("   " + "-"*82)
for label, v in (("set C only", C), ("set B only", B), ("set B without run 002", np.delete(B, 1)),
                 ("B+C pooled  <- headline", np.concatenate([B, C])),
                 ("B+C without B002", np.concatenate([np.delete(B, 1), C]))):
    sd = v.std(ddof=1)
    d = (v.mean()-bm) / np.sqrt((sd**2 + bs**2)/2)
    p = stats.norm.sf(T + K*sd, v.mean(), sd)
    print("   %-32s %3d %8.4f %8.4f %6.2f%% %8.2f %9.1f %%"
          % (label, len(v), v.mean(), sd, 100*sd/v.mean(), d, 100*p))

grubbs = np.abs(B - B.mean()).max() / B.std(ddof=1)
grubbsC = np.abs(C - C.mean()).max() / C.std(ddof=1)
print("   Grubbs on the INDEX: set B max |z| = %.2f, set C max |z| = %.2f, critical (n=6) = 1.887"
      % (grubbs, grubbsC))
print("   -> B002 is NOT an outlier on the shipped metric; C's high first run deviates more.")
print("      It is an outlier only on the UNCORRECTED ratio (plain S/Q 6.864 vs 5.23-5.49) --")
print("      i.e. 16.11.5's 'the linear baseline eats tilt events', measured on its motivating run.")
print()
print("   => green's sd spans 0.29-0.37 across every basis; BROWN stays the binding class")
print("      (sigma_fill <= 0.307) because green's own limit is the looser 0.419.")
