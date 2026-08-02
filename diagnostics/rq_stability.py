"""Does `r_Q` drift under ORDINARY re-seating? (SPEC_capture_quality.md §16.16.10)

Edwin's observation, 2026-08-02: *every* run already contains the disturbance — the reference is taken
on pure alcohol, the oil sample is then inserted, the jar is seated and the camera sits above it. So
the within-set run-to-run scatter ALREADY carries whatever re-seating does, and no new rig time is
needed to bound it. This script extracts that bound from data already on disk.

THE METHOD — the DIRECTION of the scatter identifies its cause.

Within one set the true pigment concentration is fixed, so run-to-run movement in the (B_Q, B_Soret)
plane points in a direction that says what moved:

    dB_Soret/dB_Q = 0              B_Q moves ALONE            -> r_Q drift (or B_Q-only noise)
    dB_Soret/dB_Q = M_inf (~10)    movement along the line    -> how much pigment is in the beam
    dB_Soret/dB_Q = M     (~13)    movement along origin ray  -> pure throughput scaling

Only the first is a threat to the pedestal correction, and it is the one the geometry can reject.

⚠ WHAT THIS DOES AND DOES NOT COVER. It covers WITHIN-SESSION re-seating, which is what Edwin's
routine contains. It says nothing about BETWEEN-SESSION stability — a different evening, the camera
lifted off and replaced — which is the case a multi-year history graph actually depends on, and which
no data on disk can answer (Kiendler and Steirerkraft differ in oil AND session, so their r_Q
difference confounds the two).

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/rq_stability.py
"""
import numpy as np
from scipy import stats

from settling_sweep import measure

R_Q = -0.0246                                   # DOC_pedestal_correction.md §6 / §16.15.6
M_INF = 9.998                                   # the same fit's slope

# Post-rebuild sets only, and only those with enough runs to fit a within-set direction.
SETS = [("Kiendler A", ["20260801A/%03d.pdf" % i for i in range(1, 7)]),
        ("Steirerkraft B", ["20270729B/%03d.pdf" % i for i in range(1, 7)]),
        ("Steirerkraft C", ["20270729C/%03d.pdf" % i for i in range(1, 7)]),
        ("S-Budget D", ["20260731A/%03d.pdf" % i for i in range(1, 7)])]


def main():
    print(__doc__.split("THE METHOD")[0].strip())
    print()

    runs = {name: [measure(p) for p in paths] for name, paths in SETS}

    def bands(name):
        return (np.array([r["A_Q linear"] for r in runs[name]]),
                np.array([r["A_Soret linear"] for r in runs[name]]))

    print("=== PER SET — the within-set scatter direction")
    print("   %-16s %4s %10s %16s %11s %11s" % (
        "set", "n", "M (ray)", "within slope", "vs 0", "vs M_inf"))
    print("   " + "-" * 74)
    deltasX, deltasY = [], []
    for name, _ in SETS:
        x, y = bands(name)
        fit = stats.linregress(x, y)
        deltasX.append(x - x.mean())
        deltasY.append(y - y.mean())
        print("   %-16s %4d %10.2f %9.2f +/-%-5.2f %8.1f s %8.1f s" % (
            name, len(x), y.mean() / x.mean(), fit.slope, fit.stderr,
            abs(fit.slope / fit.stderr), abs((fit.slope - M_INF) / fit.stderr)))
    print("   (individual sets are weak — the pooled figure below is the usable one)")
    print()

    x = np.concatenate(deltasX)
    y = np.concatenate(deltasY)
    fit = stats.linregress(x, y)
    print("=== POOLED within-set, set means removed   (n = %d)" % len(x))
    print("   slope = %.2f +/- %.2f      r^2 = %.2f" % (fit.slope, fit.stderr, fit.rvalue ** 2))
    for target, label in ((0.0, "0     — pure r_Q drift          THE THREAT"),
                          (M_INF, "M_inf — pigment in the beam"),
                          (13.0, "13    — throughput / origin ray")):
        print("      vs %-34s %5.1f sigma away" % (label, abs((fit.slope - target) / fit.stderr)))
    print()

    residual = (y - fit.slope * x).std(ddof=2)
    ceiling = residual / fit.slope
    print("=== THE BOUND")
    print("   residual scatter about the co-movement line : %.4f A" % residual)
    print("   implied CEILING on run-to-run r_Q drift     : %.4f A" % ceiling)
    print("   r_Q itself                                  : %.4f A" % abs(R_Q))
    print("   ⇒ run-to-run drift is at most %.0f %% of r_Q." % (100 * ceiling / abs(R_Q)))
    print()
    print("   ⚠ This is a CEILING, not an estimate. The residual also contains ordinary measurement")
    print("     noise, and all of it was attributed to r_Q drift — the maximally pessimistic split.")
    print("     The true drift is somewhere below this, possibly far below.")
    print()
    print("   ⚠ WITHIN-SESSION only. Between-session stability is untested and untestable from the")
    print("     archive; see §16.16.11 item 2'.")


if __name__ == "__main__":
    main()
