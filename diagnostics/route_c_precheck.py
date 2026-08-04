"""Route C pre-check — does a smooth baseline EAT the Qy flank? (SPEC_metric_research.md §7.6)

Route C proposes replacing the two-anchor chord with a whole-range smooth baseline (convex hull,
low-order polynomial, or ALS). Its selling point, repeated four times in this research and never
examined, is that it "assumes only SMOOTHNESS, never QUIETNESS" -- so it needs no window to be
pigment-free, which is the assumption every other construction here leans on.

⛔ THE RUBBER DUCK'S OBJECTION, and it is a design-killer if it holds. A smooth baseline separates
background from signal BY SCALE: background varies slowly, bands quickly. The pedestal is broad and
smooth, so far so good. But the Qy flank rises MONOTONICALLY from ~610 nm to the 629.8 nm cut-off --
over 20 nm, with no turning point, because its maximum lies outside our range (§3.1). To any smoothing
operator that is indistinguishable from a slowly-rising background.

⇒ V3's DENOMINATOR is exactly the band most at risk. Route C could clean the numerator and destroy the
denominator. That is measurable rather than arguable, and this script measures it.

THE TEST. Fit each candidate baseline, then ask what it does across 620-630:
  * how much of the far-red band does it absorb?
  * does the fitted baseline RISE there (tracking the flank) or stay flat (leaving it alone)?
  * and does it eat the far band CLASS-DEPENDENTLY, which would be worse than eating it uniformly?

Parameter-free methods first, per the duck: a convex hull has ZERO free parameters, a fixed-order
polynomial has one integer. ALS's two continuous parameters are exactly what §6.4 rule 3 forbids
tuning, so ALS is only worth reaching for if a parameter-free method survives this check.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/route_c_precheck.py
"""
import numpy as np

from metric_research_overview import load

FULL = (440.0, 629.8)          # the duck's fix: fit over the FULL range, not 500-630
FAR = (620.0, 629.8)           # V3's denominator -- the band at risk
Q = (566.0, 582.0)             # V3's numerator
OILS = ("Kiendler", "Steirerkraft", "S-Budget")


def hullBaseline(x, y):
    """Convex hull from below -- the remote-sensing continuum. ZERO free parameters."""
    points = [0]
    for index in range(1, len(x)):
        while len(points) >= 2:
            a, b = points[-2], points[-1]
            # drop b if it lies above the chord a->index (i.e. the hull is not convex there)
            chord = y[a] + (y[index] - y[a]) * (x[b] - x[a]) / (x[index] - x[a])
            if y[b] >= chord:
                points.pop()
            else:
                break
        points.append(index)
    return np.interp(x, x[points], y[points])


def polynomialBaseline(x, y, order, iterations=30):
    """Iterative lower-envelope polynomial: fit, clip anything above the fit, refit. One integer."""
    working = y.copy()
    for _ in range(iterations):
        fit = np.polyval(np.polyfit(x, working, order), x)
        working = np.minimum(working, fit)
    return np.polyval(np.polyfit(x, working, order), x)


def main():
    grid, runs = load()
    mask = (grid >= FULL[0]) & (grid <= FULL[1])
    x = grid[mask]
    far = (x >= FAR[0]) & (x <= FAR[1])
    q = (x >= Q[0]) & (x <= Q[1])

    methods = [("convex hull (0 params)", lambda x, y: hullBaseline(x, y)),
               ("polynomial order 3", lambda x, y: polynomialBaseline(x, y, 3)),
               ("polynomial order 5", lambda x, y: polynomialBaseline(x, y, 5)),
               ("polynomial order 7", lambda x, y: polynomialBaseline(x, y, 7))]

    print("=== DOES THE FITTED BASELINE RISE THROUGH THE Qy FLANK?\n")
    print("   The measured flank rises at about +0.0064 A/nm across 620-630 (§7.2).")
    print("   A baseline that TRACKS it is eating signal; one near 0 is leaving it alone.\n")
    print("   %-24s %14s %14s %14s" % ("method", "baseline slope", "as % of flank", "far band left"))
    print("   " + "-" * 70)
    for label, method in methods:
        slopes, retained, byOil = [], [], {}
        for name, oil, values in runs:
            y = values[mask]
            base = method(x, y)
            slopes.append(np.polyfit(x[far], base[far], 1)[0])
            raw = y[far].mean() - np.polyval(np.polyfit(x[far], base[far], 1), x[far]).mean()
            measured = np.polyfit(x[far], y[far], 1)[0]
            retained.append(raw)
            byOil.setdefault(oil, []).append(raw)
        measuredSlope = np.mean([np.polyfit(x[far], v[mask][far], 1)[0] for _, _, v in runs])
        print("   %-24s %+13.5f %13.0f %% %13.4f A"
              % (label, np.mean(slopes), 100 * np.mean(slopes) / measuredSlope, np.mean(retained)))

    # ---- the class-dependence question: eating the band uniformly is survivable, eating it
    # class-dependently is not, because that is signal destruction that varies with the answer.
    print("\n=== WHAT SURVIVES IN EACH BAND, PER OIL  (the chord's numbers are §7.4.1's)\n")
    for label, method in methods:
        print("   %s" % label)
        print("      %-14s %12s %12s %12s" % ("oil", "Q left", "far left", "V3 = Q/far"))
        rows = {}
        for name, oil, values in runs:
            y = values[mask]
            base = method(x, y)
            excess = y - base
            rows.setdefault(oil, []).append((excess[q].mean(), excess[far].mean()))
        for oil in OILS:
            pairs = np.array(rows[oil])
            ratio = pairs[:, 0] / pairs[:, 1]
            print("      %-14s %12.4f %12.4f %8.3f ± %.3f"
                  % (oil, pairs[:, 0].mean(), pairs[:, 1].mean(), ratio.mean(), ratio.std(ddof=1)))
        allPairs = {oil: np.array(rows[oil]) for oil in OILS}
        greens = np.concatenate([allPairs["Kiendler"][:, 0] / allPairs["Kiendler"][:, 1],
                                 allPairs["Steirerkraft"][:, 0] / allPairs["Steirerkraft"][:, 1]])
        brown = allPairs["S-Budget"][:, 0] / allPairs["S-Budget"][:, 1]
        pooled = np.sqrt(((len(greens) - 1) * greens.var(ddof=1) + (len(brown) - 1) * brown.var(ddof=1))
                         / (len(greens) + len(brown) - 2))
        print("      => V3 after this baseline:  class d = %.2f    (raw V3 = 3.54, M = 6.91)\n"
              % (abs(greens.mean() - brown.mean()) / pooled))


if __name__ == "__main__":
    main()
