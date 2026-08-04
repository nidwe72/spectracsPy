"""T4 — is the pedestal correction NEEDED, or would a curved baseline do the job properly?

(DOC_pedestal_correction.md ch. 13 T4 and Appendix D.6; SPEC_metric_research.md §7.9.)

THE ARGUMENT T4 MAKES. Chapter 4 concludes the entire problem is CURVATURE: a straight chord cannot
follow a curved pedestal, so it over-subtracts at the Q band and leaves `r_Q` behind. The document then
CORRECTS THE CONSEQUENCE (subtract r_Q) rather than MODELLING THE CAUSE. The orthodox remedies do the
opposite -- a curved baseline, or a derivative reading -- and they have the property `r_Q` lacks: they
follow from a stated model of the background that can be inspected and violated, rather than from a
constant fitted on one oil and transferred on an untested assumption (A1).

⇒ T4 is the ONLY test on chapter 13's list that could make the correction UNNECESSARY rather than
merely unproven.

⚠ WHY THIS IS NOT A REPEAT OF §7.6. That section ran the same baselines for V3 and they failed, because
V3's denominator is the far-red band -- a TRUNCATED FLANK whose maximum lies past our 629.8 nm cut-off,
which a smooth baseline cannot distinguish from a rising background. `M`'s denominator is the 560-580
band, which IS properly bracketed: it has a maximum at ~574 nm with measurable ground on both sides.
The methods that died on a flank may work on a real band. That is the whole question here.

⚠ EXPECTATION MANAGEMENT, stated before running. §7.6 measured the convex hull tracking the Qy flank at
101 %. `M`'s chord has its FAR FOOT in that same 620-630 window, so a curved baseline may distort `M`'s
baseline for the same reason -- not through its Q band but through its red anchor.

WHAT IS SCORED. For each baseline: `M` computed above it, then the three questions chapter 13 cares
about -- does it separate the classes, does it survive dilution, and does it need `r_Q` afterwards
(i.e. is there still a residual intercept in the B_Soret-vs-B_Q straight-line test of chapter 6)?

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/t4_curved_baseline.py
"""
import numpy as np
from scipy import stats
from scipy.signal import savgol_filter

from metric_research_overview import load
from metric_features import SORET, NEAR, FAR, chordBaselined, bandMean
from route_c_precheck import hullBaseline, polynomialBaseline

Q = (560.0, 580.0)                      # the SHIPPED Q window -- this is a test of `M`, not of a variant
FULL = (440.0, 629.8)
R_Q = -0.0184
GREENS = ("Kiendler", "Steirerkraft")
# The chord's own B_Soret/B_Q slope on Kiendler. Any baseline landing far from it is no
# longer measuring the same two bands, so its straight-line test is void (see the guard).
REFERENCE_SLOPE = 12.44


def cohenD(a, b):
    a, b = np.asarray(a), np.asarray(b)
    pooled = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1))
                     / (len(a) + len(b) - 2))
    return abs(a.mean() - b.mean()) / pooled if pooled else float("nan")


def main():
    grid, runs = load()
    mask = (grid >= FULL[0]) & (grid <= FULL[1])
    x = grid[mask]
    step = float(np.median(np.diff(grid)))

    def soretAndQ(values, baseline):
        excess = values[mask] - baseline
        return (excess[(x >= SORET[0]) & (x <= SORET[1])].mean(),
                excess[(x >= Q[0]) & (x <= Q[1])].mean())

    # The chord and the corrected chord are the reference rows: everything else must beat them.
    methods = [("chord (SHIPPED)", None),
               ("chord + r_Q (the proposal)", None),
               ("convex hull, 0 params", lambda v: hullBaseline(x, v[mask])),
               ("polynomial order 3", lambda v: polynomialBaseline(x, v[mask], 3)),
               ("polynomial order 5", lambda v: polynomialBaseline(x, v[mask], 5)),
               ("polynomial order 7", lambda v: polynomialBaseline(x, v[mask], 7))]

    print("=== T4  DOES A CURVED BASELINE MAKE THE PEDESTAL CORRECTION UNNECESSARY?\n")
    print("   `M` is B_Soret / B_Q on the SHIPPED windows; only the BASELINE changes.\n")
    print("   %-28s %8s %9s %10s | %9s %8s" % ("baseline", "class d", "d(K|S)", "§2.2 ratio",
                                               "dilution", "still?"))
    print("   " + "-" * 82)

    for label, method in methods:
        perOil, perSet, bands = {}, {}, []
        for name, oil, values in runs:
            if method is None:
                baselined = chordBaselined(grid, values, NEAR, FAR)
                soret, q = bandMean(grid, baselined, SORET), bandMean(grid, baselined, Q)
                if "r_Q" in label:
                    q = q - R_Q
            else:
                soret, q = soretAndQ(values, method(values))
            metric = soret / q
            perOil.setdefault(oil, []).append(metric)
            perSet.setdefault(name, []).append(metric)
            bands.append((oil, soret, q))

        greens = np.array(perOil["Kiendler"] + perOil["Steirerkraft"])
        brown = np.array(perOil["S-Budget"])
        classD = cohenD(greens, brown)
        withinD = cohenD(perOil["Kiendler"], perOil["Steirerkraft"])
        kiendler = [np.mean(perSet[n]) for n in ("Kiendler A", "Kiendler B", "Kiendler C")]
        dilution = 100 * (max(kiendler) - min(kiendler)) / abs(np.mean(kiendler))

        # ⭐ chapter 6's test, re-run on THIS baseline: does a residual intercept remain? If a curved
        # baseline removed the pedestal properly, the B_Soret-vs-B_Q line goes through the ORIGIN and
        # r_Q is not needed. A surviving intercept means the correction is still required.
        rows = [b for b in bands if b[0] == "Kiendler"]
        fit = stats.linregress([r[2] for r in rows], [r[1] for r in rows])
        residual = -fit.intercept / fit.slope
        significant = abs(fit.intercept / fit.intercept_stderr) > 2.0

        # ⛔ THE GUARD, and it exists because the first version of this script drew a WRONG conclusion.
        # A vanishing intercept was read as "this baseline removed the residual". It was not: the hull
        # had removed the SORET BAND. The Soret's peak is at ~432 nm, below our 440 nm edge, so it is a
        # monotonic FLANK -- and a hull hugging the data from below simply follows it down. B_Soret
        # collapsed from ~1.1 A to ~0.02 A and the SLOPE fell 12.4 -> 0.25.
        #
        # With both bands destroyed there is nothing left to carry an intercept, so the test cannot
        # fail. That is weighing nothing on a scale and concluding the scale is unbiased. The slope is
        # the ratio the metric IS, so it is the honest detector: if it has moved far from the chord's
        # ~12.4, this baseline is not measuring the same two bands and its intercept means nothing.
        destroyed = not (0.4 * REFERENCE_SLOPE < fit.slope < 2.5 * REFERENCE_SLOPE)
        if destroyed:
            verdict = "⛔ VOID"
        else:
            verdict = "YES" if significant else "no"

        print("   %-28s %8.2f %9.2f %10.2f | %8.1f %% %8s"
              % (label, classD, withinD, classD / withinD if withinD else float("inf"),
                 dilution, verdict))
        if method is not None:
            print("   %-28s   -> slope %6.2f (chord 12.44), r_Q %+.4f A, t = %.1f%s"
                  % ("", fit.slope, residual, fit.intercept / fit.intercept_stderr,
                     "   ⛔ BANDS DESTROYED — intercept is meaningless" if destroyed else ""))

    print("\n   'still?' = does chapter 6's straight-line test STILL show a residual intercept")
    print("             (t > 2) after this baseline? YES means the correction is still needed.")
    print("   ⛔ VOID  = this baseline destroyed the bands (slope far from the chord's 12.44), so its")
    print("             intercept carries no information. An empty test cannot pass.")


if __name__ == "__main__":
    main()
