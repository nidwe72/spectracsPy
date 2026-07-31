"""Baseline-correction variants, scored head to head (Edwin, 2026-07-31).

Two questions in one harness:

  (1) Is the RED anchor still needed after the rig rebuild?  -> §16.12.14
  (2) Would a WHOLE-SPECTRUM baseline beat the two-window line?  -> §16.12.14a

Original framing of (1):

The hypothesis: the far (red) window 600-630 was adopted as a baseline anchor when the rig had much more
mechanical wobble. §16.11 rebuilt it - jar tilt 2.84 % -> 1.34 %. If the red anchor was mostly compensating
that wobble, its advantage should SHRINK on post-rebuild data, and a simpler correction that never touches
the red end might now be enough.

Variants compared (all on the same de-spiked absorbance, all ratios of the SAME two bands):

    raw                  no correction at all
    offset NEAR only     subtract the constant mean(520-540)          <- Edwin's proposal: NO red window
    offset FAR only      subtract the constant mean(600-630)
    linear NEAR+FAR      the shipped metric
    2nd derivative       window-free; annihilates ANY linear baseline exactly

Two datasets, and the contrast between them IS the test:

    PRE-rebuild   2026-07-27, 4 fills, both classes  -> precision AND discrimination
    POST-rebuild  2026-07-29 sets B and C, green     -> precision, settling, dilution (B->C ~17 % apart)

⚠ The 07-29 sets are BOTH GREEN, so they cannot score discrimination. Precision and drift come from
post-rebuild data; class separation is only available pre-rebuild. Stated rather than papered over.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/baseline_variants.py
"""
import os

import numpy as np
from scipy import sparse
from scipy.signal import savgol_filter
from scipy.sparse.linalg import spsolve
from scipy.spatial import ConvexHull

from far_anchor_probe import spectra
from metric_bench import BASE, bestThreshold, feature, plugin
from sciens.spectracs.model.spectral.Spectrum import Spectrum
from settling_sweep import detrend

SORET, Q, WINDOWS = plugin.PB_SORET_BAND, plugin.PB_Q_BAND, plugin.PB_BASELINE_WINDOWS
NEAR, FAR = WINDOWS

PRE = [("green", "green B", ["20260727B/%03d.pdf" % i for i in range(1, 10)]),
       ("green", "green E", ["20260727E/%03d.pdf" % i for i in range(1, 8)]),
       ("brown", "brown C", ["20260727C/%03d.pdf" % i for i in range(1, 7)]),
       ("brown", "brown D", ["20260727D/%03d.pdf" % i for i in range(1, 4)])]
POST = [("set B", ["20270729B/%03d.pdf" % i for i in range(1, 7)]),
        ("set C", ["20270729C/%03d.pdf" % i for i in range(1, 7)])]

VARIANTS = ["raw", "offset NEAR only", "offset FAR only", "linear NEAR+FAR", "2nd derivative",
            "full-range line", "rubber band", "ModPoly ord3", "AsLS 1e5/0.01", "AsLS 1e6/0.001",
            "lin 2win LSQ", "lin ex-bands", "poly2 ex-bands", "poly3 ex-bands", "lin ex-band+carot"]

# --- "fit over more of the spectrum, but anchor ONLY where the oil is quiet" (Edwin, 2026-07-31).
# The shipped correction draws a line through the two window MEANS - two points. These use least squares
# over MANY points, varying how much of the spectrum counts as quiet:
#   2win LSQ      every point inside the SAME two windows (uses within-window slope, not just the means)
#   ex-bands      everything in 440-630 EXCEPT the two measured bands - the widest reading of "quiet"
#   ex-band+carot ALSO excludes 460-510, where the carotenoids absorb, so the mask is a widened version
#                 of the shipped windows rather than "everything else"
CAROTENOID = (460.0, 510.0)


def quietMask(lam, excludeCarotenoids=False):
    mask = ~(((lam >= SORET[0]) & (lam <= SORET[1])) | ((lam >= Q[0]) & (lam <= Q[1])))
    if excludeCarotenoids:
        mask &= ~((lam >= CAROTENOID[0]) & (lam <= CAROTENOID[1]))
    return mask


def windowMask(lam):
    return (((lam >= NEAR[0]) & (lam <= NEAR[1])) | ((lam >= FAR[0]) & (lam <= FAR[1])))


def fittedBaseline(lam, raw, mask, order):
    """Least-squares polynomial of `order` fitted ONLY where `mask` is true, evaluated everywhere."""
    scaled = (lam - lam.min()) / (lam.max() - lam.min())
    return np.polyval(np.polyfit(scaled[mask], raw[mask], order), scaled)


# --------------------------------------------------------------------------- whole-spectrum baselines
# ⚠ Shared limitation: our window is only 440-630 nm and BOTH ENDS SIT ON PIGMENT - the Soret band starts
# at the very left edge and the chlorophyll Q flank rises into the right edge (§16.12.12). A whole-spectrum
# baseline has no genuinely peak-free region to anchor on, which is exactly the condition these algorithms
# assume. Measured anyway rather than argued about.

def asymmetricLeastSquares(y, smoothness, asymmetry, iterations=10):
    """Eilers & Boelens ALS - the standard chemometric whole-spectrum baseline.

    Fits a smooth curve that is pulled UNDER the peaks by weighting positive residuals at `asymmetry`
    and negative ones at `1 - asymmetry`.
    """
    length = len(y)
    differences = sparse.diags([1, -2, 1], [0, -1, -2], shape=(length, length - 2))
    penalty = smoothness * differences.dot(differences.transpose())
    weights = np.ones(length)
    baseline = np.zeros(length)
    for _ in range(iterations):
        weighted = sparse.spdiags(weights, 0, length, length)
        baseline = spsolve(weighted.tocsc() + penalty.tocsc(), weights * y)
        weights = asymmetry * (y > baseline) + (1 - asymmetry) * (y < baseline)
    return baseline


def rubberBand(x, y):
    """Convex hull taken from BELOW, then linearly interpolated - the classic 'rubber band' baseline."""
    points = np.column_stack([x, y])
    hull = ConvexHull(points)
    vertices = np.roll(hull.vertices, -hull.vertices.argmin())
    # walking from the leftmost vertex, the first ascending-x run is the LOWER hull
    lower = vertices[:vertices.argmax() + 1]
    return np.interp(x, x[lower], y[lower])


def modifiedPolynomial(x, y, order=3, iterations=40):
    """ModPoly (Lieber & Mahadevan-Jansen): fit, clip anything above the fit, refit until stable."""
    working = y.copy()
    baseline = np.zeros_like(y)
    for _ in range(iterations):
        baseline = np.polyval(np.polyfit(x, working, order), x)
        updated = np.minimum(working, baseline)
        if np.allclose(updated, working):
            break
        working = updated
    return baseline


def variants(path):
    """{variantName: metricValue} for one run."""
    values = spectra(path)["ABSORPTION"]
    lam = np.array(sorted(values))
    raw = np.array([values[k] for k in lam])

    def band(data, window):
        return float(data[(lam >= window[0]) & (lam <= window[1])].mean())

    def ratio(data):
        return band(data, SORET) / band(data, Q)

    source = Spectrum()
    source.valuesByNanometers = dict(values)
    linear = feature.linearBaselineCorrected(source, WINDOWS)
    linearValues = np.array([linear.valuesByNanometers[k] for k in lam])

    second = savgol_filter(raw, window_length=31, polyorder=3, deriv=2)

    scaled = (lam - lam.min()) / (lam.max() - lam.min())        # conditioning for the polynomial fit
    return {"raw": ratio(raw),
            "offset NEAR only": ratio(raw - band(raw, NEAR)),
            "offset FAR only": ratio(raw - band(raw, FAR)),
            "linear NEAR+FAR": ratio(linearValues),
            "2nd derivative": abs(band(second, SORET)) / max(abs(band(second, Q)), 1e-9),
            "full-range line": ratio(raw - np.polyval(np.polyfit(lam, raw, 1), lam)),
            "rubber band": ratio(raw - rubberBand(lam, raw)),
            "ModPoly ord3": ratio(raw - modifiedPolynomial(scaled, raw, order=3)),
            "AsLS 1e5/0.01": ratio(raw - asymmetricLeastSquares(raw, 1e5, 0.01)),
            "AsLS 1e6/0.001": ratio(raw - asymmetricLeastSquares(raw, 1e6, 0.001)),
            "lin 2win LSQ": ratio(raw - fittedBaseline(lam, raw, windowMask(lam), 1)),
            "lin ex-bands": ratio(raw - fittedBaseline(lam, raw, quietMask(lam), 1)),
            "poly2 ex-bands": ratio(raw - fittedBaseline(lam, raw, quietMask(lam), 2)),
            "poly3 ex-bands": ratio(raw - fittedBaseline(lam, raw, quietMask(lam), 3)),
            "lin ex-band+carot": ratio(raw - fittedBaseline(lam, raw, quietMask(lam, True), 1))}


def cv(values):
    values = np.asarray(values, dtype=float)
    return values.std(ddof=1) / abs(values.mean()) * 100.0


def main():
    print(__doc__.split("Run:")[0].strip().splitlines()[0])
    print()

    pre = [(label, name, [variants(p) for p in paths]) for label, name, paths in PRE]
    post = [(name, paths, [variants(p) for p in paths]) for name, paths in POST]

    # ------------------------------------------------------------------ PRECISION, pre vs post
    print("=== PRECISION — within-fill CV %, the quantity the rebuild was meant to improve")
    print("   %-18s %9s %9s %9s   %9s %9s %9s   %10s" % (
        "variant", "grn B", "grn E", "brn C", "set B", "set C", "POST avg", "PRE avg"))
    print("   " + "-" * 92)
    for variant in VARIANTS:
        preCvs = [cv([r[variant] for r in runs]) for _, _, runs in pre]
        postCvs = [cv([r[variant] for r in runs]) for _, _, runs in post]
        print("   %-18s %9.2f %9.2f %9.2f   %9.2f %9.2f %9.2f   %10.2f" % (
            variant, preCvs[0], preCvs[1], preCvs[2], postCvs[0], postCvs[1],
            np.mean(postCvs), np.mean(preCvs[:3])))
    print("   (brown D omitted from the averages — only 3 runs)\n")

    # ------------------------------------------------------------------ the actual hypothesis
    print("=== ⭐ THE TEST — how much does the correction still BUY, pre vs post rebuild?")
    print("   'gain' = raw CV / variant CV.  If the red anchor was compensating WOBBLE, its gain must")
    print("   FALL after the rebuild. If the gain holds, it is correcting something else.\n")
    print("   %-18s %14s %14s %12s" % ("variant", "PRE gain vs raw", "POST gain vs raw", "change"))
    print("   " + "-" * 62)
    preRaw = np.mean([cv([r["raw"] for r in runs]) for _, _, runs in pre[:3]])
    postRaw = np.mean([cv([r["raw"] for r in runs]) for _, _, runs in post])
    for variant in VARIANTS:
        preOwn = np.mean([cv([r[variant] for r in runs]) for _, _, runs in pre[:3]])
        postOwn = np.mean([cv([r[variant] for r in runs]) for _, _, runs in post])
        preGain, postGain = preRaw / preOwn, postRaw / postOwn
        print("   %-18s %13.2f× %13.2f× %11s" % (
            variant, preGain, postGain,
            "%+.0f %%" % (100 * (postGain / preGain - 1)) if preGain else "-"))
    print()

    # ------------------------------------------------------------------ settling + dilution, POST only
    print("=== POST-REBUILD ONLY — settling trend and the B→C dilution step (~17 % apart)")
    print("   %-18s %11s %11s %11s %13s" % (
        "variant", "B trend%", "C trend%", "pooled CV%", "B→C dilution%"))
    print("   " + "-" * 70)
    for variant in VARIANTS:
        trends, pooled = [], []
        for name, paths, runs in post:
            times = np.array([os.path.getmtime(BASE + p) for p in paths])
            times = (times - times[0]) / 60.0
            values = [r[variant] for r in runs]
            _, _, trend, _ = detrend(times, values)
            trends.append(trend)
            pooled.append(cv(values))
        means = [np.mean([r[variant] for r in runs]) for _, _, runs in post]
        print("   %-18s %+10.2f %+10.2f %11.2f %+12.2f" % (
            variant, trends[0], trends[1], np.mean(pooled), (means[1] / means[0] - 1) * 100))
    print()

    # ------------------------------------------------------------------ discrimination, PRE only
    print("=== DISCRIMINATION — PRE-rebuild only (the 07-29 sets are both green, so they cannot score it)")
    print("   %-18s %9s %8s %10s" % ("variant", "LOFO", "|d|", "gap"))
    print("   " + "-" * 50)
    flat = [(label, name, r) for label, name, runs in pre for r in runs]
    for variant in VARIANTS:
        green = np.array([r[variant] for label, _, r in flat if label == "green"])
        brown = np.array([r[variant] for label, _, r in flat if label == "brown"])
        pooledSd = np.sqrt(((len(green) - 1) * green.var(ddof=1) + (len(brown) - 1) * brown.var(ddof=1)) /
                           (len(green) + len(brown) - 2))
        cohenD = abs(green.mean() - brown.mean()) / pooledSd
        gap = green.min() - brown.max()
        values = [r[variant] for _, _, r in flat]
        labels = [label for label, _, _ in flat]
        lofo = 0
        for _, fillName, _ in PRE:
            trainValues = [r[variant] for label, name, r in flat if name != fillName]
            trainLabels = [label for label, name, _ in flat if name != fillName]
            cut, greenIsHigh, _ = bestThreshold(trainValues, trainLabels)
            lofo += sum(1 for label, name, r in flat if name == fillName and
                        ((r[variant] > cut) == greenIsHigh) != (label == "green"))
        print("   %-18s %6d/%-2d %8.2f %10s" % (
            variant, lofo, len(flat), cohenD, ("+%.3f" % gap) if gap > 0 else "OVERLAP"))


if __name__ == "__main__":
    main()
