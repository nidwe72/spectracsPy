"""Every intermediate quantity of the DEV plugin's metric chain, for DOC_metric_algebra.md.

Runs the SHIPPED code paths (SpectrumFeatureUtil / MedianFilterOp via DevSpectralPlugin) rather than
re-implementing them, so the numbers in the document cannot drift from the numbers in the app. Two
datasets, chosen because they are the cleanest post-rebuild pair on record:

    20270729C   green oil, 6 re-seats of one fill  (SPEC_capture_quality.md §16.11.3)
    20260731A   BROWN oil, 6 re-seats of one fill  (§16.13, series D)

Prints, per class: the band means before and after the linear baseline, the fitted baseline line
itself, both S/Q ratios, and the three-region expansion's predicted-vs-actual check.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/metric_walkthrough.py
"""
import json
import os

import numpy as np
from pypdf import PdfReader

from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.plugin_sdk.util.SpectrumFeatureUtil import SpectrumFeatureUtil
from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin

BASE = "/home/nidwe72/development/spectracs/spectracs-references/tmp/"
GREEN = ["20270729C/%03d.pdf" % i for i in range(1, 7)]
BROWN = ["20260731A/%03d.pdf" % i for i in range(1, 7)]

plugin, feature = DevSpectralPlugin(), SpectrumFeatureUtil()
SORET, Q, CLARITY = plugin.PB_SORET_BAND, plugin.PB_Q_BAND, plugin.GREEN_BAND

# ---------------------------------------------------------------- which far anchor the document describes
# `DOC_metric_algebra.md` chapters 4-5 are written on the SHIPPED anchor, so that is the default. The
# superseded 600-630 window stays reachable because §5a quotes the before/after side by side, and because
# §5.9's 607 nm question only exists while the line is INSIDE the anchor.
#     METRIC_ANCHOR=600 ./venv/bin/python diagnostics/metric_walkthrough.py
ANCHOR = os.environ.get("METRIC_ANCHOR", "620")
WINDOWS = (plugin.PB_BASELINE_WINDOWS if ANCHOR == "620" else plugin.PB_BASELINE_WINDOWS_LEGACY_600)
NEAR, FAR = WINDOWS


def absorption(path, despike=True):
    """The ABSORPTION spectrum from the report's embedded workflow JSON, de-spiked as the plugin does."""
    workflow = json.loads(PdfReader(BASE + path).attachments["workflow.json"][0])
    for phase in workflow["phases"]:
        for step in phase.get("steps", []):
            raw = step.get("spectra", {}).get("ABSORPTION")
            if raw is not None:
                spectrum = Spectrum()
                spectrum.valuesByNanometers = {float(k): float(v)
                                               for k, v in raw.get("valuesByNanometers", raw).items()}
                return plugin._DevSpectralPlugin__despikedAbsorption(spectrum) if despike else spectrum
    raise KeyError("no ABSORPTION in " + path)


def centroid(spectrum, window):
    """Mean wavelength of the points actually inside a window — the lever arm the expansion uses."""
    lam = [nm for nm in spectrum.valuesByNanometers if window[0] <= nm <= window[1]]
    return float(np.mean(lam)), len(lam)


def fittedLine(spectrum):
    """Re-derive the weighted least-squares baseline line (slope, intercept) the shipped code fits."""
    points = sorted((nm, v) for nm, v in spectrum.valuesByNanometers.items() if v is not None)
    anchors, weights = [], []
    for low, high in WINDOWS:
        inWindow = [(nm, v) for nm, v in points if low <= nm <= high]
        anchors.extend(inWindow)
        weights.extend([1.0 / len(inWindow)] * len(inWindow))
    nanometers = np.array([nm for nm, _ in anchors])
    values = np.array([v for _, v in anchors])
    return np.polyfit(nanometers, values, 1, w=np.sqrt(np.array(weights)))


def walk(path):
    """Every quantity of the chain for one run."""
    despiked = absorption(path)
    baselined = feature.linearBaselineCorrected(despiked, WINDOWS)
    slope, intercept = fittedLine(despiked)
    row = {
        "A_Soret": feature.bandMean(despiked, *SORET),
        "A_Q": feature.bandMean(despiked, *Q),
        "A_clarity": feature.bandMean(despiked, *CLARITY),
        "A_near": feature.bandMean(despiked, *NEAR),
        "A_far": feature.bandMean(despiked, *FAR),
        "B_Soret": feature.bandMean(baselined, *SORET),
        "B_Q": feature.bandMean(baselined, *Q),
        "slope": slope, "intercept": intercept,
    }
    row["S/Q raw"] = row["A_Soret"] / row["A_Q"]
    row["S/Q clarity"] = row["A_Soret"] / row["A_clarity"]
    row["S/Q lin"] = row["B_Soret"] / row["B_Q"]
    return row, despiked


def main():
    print(__doc__.split("Run:")[0].strip().splitlines()[0])
    print("    far anchor: %s  (METRIC_ANCHOR=%s)" % (FAR, ANCHOR))
    print()

    _, sample = walk(GREEN[0])
    print("=== GEOMETRY — window centroids and point counts (they set the expansion's coefficients)")
    for name, window in (("Soret", SORET), ("Q", Q), ("clarity", CLARITY), ("near", NEAR), ("far", FAR)):
        centre, count = centroid(sample, window)
        print("   %-8s %s  centroid %7.2f nm   %4d points" % (name, window, centre, count))
    nearC, _ = centroid(sample, NEAR)
    farC, _ = centroid(sample, FAR)
    soretC, _ = centroid(sample, SORET)
    qC, _ = centroid(sample, Q)
    print()
    print("   the baseline under a band at centroid c is the line read at c; with equal window weight")
    print("   the line passes through (near_c, A_near) and (far_c, A_far), so")
    for name, bandC in (("Soret", soretC), ("Q", qC)):
        t = (bandC - nearC) / (farC - nearC)
        print("     %-6s t = (%.2f - %.2f)/(%.2f - %.2f) = %+.4f  ->  B_%s = A_%s - [%+.3f*A_near %+.3f*A_far]"
              % (name, bandC, nearC, farC, nearC, t, name, name, -(1 - t), -t))
    print()

    collected = {}
    for label, paths in (("GREEN  20270729C", GREEN), ("BROWN  20260731A", BROWN)):
        rows = [walk(p)[0] for p in paths]
        collected[label.split()[0]] = rows
        print("=== %s" % label)
        print("   %-5s %8s %7s %8s %7s %7s | %8s %7s | %7s %7s %8s" % (
            "run", "A_Soret", "A_Q", "A_clar", "A_near", "A_far",
            "B_Soret", "B_Q", "S/Q", "S/Qclar", "S/Q_lin"))
        print("   " + "-" * 100)
        for path, row in zip(paths, rows):
            print("   %-5s %8.4f %7.4f %8.4f %7.4f %7.4f | %8.4f %7.4f | %7.3f %7.3f %8.3f" % (
                path[-7:-4], row["A_Soret"], row["A_Q"], row["A_clarity"], row["A_near"], row["A_far"],
                row["B_Soret"], row["B_Q"], row["S/Q raw"], row["S/Q clarity"], row["S/Q lin"]))
        mean = {k: float(np.mean([r[k] for r in rows])) for k in rows[0]}
        sd = {k: float(np.std([r[k] for r in rows], ddof=1)) for k in rows[0]}
        print("   " + "-" * 100)
        print("   %-5s %8.4f %7.4f %8.4f %7.4f %7.4f | %8.4f %7.4f | %7.3f %7.3f %8.3f" % (
            "mean", mean["A_Soret"], mean["A_Q"], mean["A_clarity"], mean["A_near"], mean["A_far"],
            mean["B_Soret"], mean["B_Q"], mean["S/Q raw"], mean["S/Q clarity"], mean["S/Q lin"]))
        print("   %-5s %8s %7s %8s %7s %7s | %8s %7s | %7s %7s %8s" % (
            "CV%%", "%.2f" % (100 * sd["A_Soret"] / mean["A_Soret"]),
            "%.2f" % (100 * sd["A_Q"] / mean["A_Q"]),
            "%.2f" % (100 * sd["A_clarity"] / mean["A_clarity"]),
            "%.2f" % (100 * sd["A_near"] / mean["A_near"]),
            "%.2f" % (100 * sd["A_far"] / mean["A_far"]),
            "%.2f" % (100 * sd["B_Soret"] / mean["B_Soret"]),
            "%.2f" % (100 * sd["B_Q"] / mean["B_Q"]),
            "%.2f" % (100 * sd["S/Q raw"] / mean["S/Q raw"]),
            "%.2f" % (100 * sd["S/Q clarity"] / mean["S/Q clarity"]),
            "%.2f" % (100 * sd["S/Q lin"] / mean["S/Q lin"])))
        print("   fitted baseline, mean over the set:  slope %+.3e A/nm   intercept %+.4f A" % (
            mean["slope"], mean["intercept"]))
        print("   baseline VALUE under each band:      Soret %.4f    Q %.4f" % (
            mean["slope"] * soretC + mean["intercept"], mean["slope"] * qC + mean["intercept"]))
        print()

        # three-region expansion check (SPEC_capability_proof §2.1a)
        tS = (soretC - nearC) / (farC - nearC)
        tQ = (qC - nearC) / (farC - nearC)
        errors = []
        for row in rows:
            numerator = row["A_Soret"] - (1 - tS) * row["A_near"] - tS * row["A_far"]
            denominator = row["A_Q"] - (1 - tQ) * row["A_near"] - tQ * row["A_far"]
            errors.append(100 * ((numerator / denominator) - row["S/Q lin"]) / row["S/Q lin"])
        print("   three-region expansion vs the shipped code: max |error| %.2f %%  (coeffs %.3f / %.3f"
              " near, %.3f / %.3f far)" % (max(abs(e) for e in errors), 1 - tS, 1 - tQ, tS, tQ))
        print()

    discrimination(collected)
    naiveVsFitted(collected, nearC, farC, soretC, qC)


def cohensD(green, brown):
    """Equal-n RMS pooled SD -- the convention DOC_metric_algebra Appendix B.2 declares and uses."""
    g, b = np.array(green), np.array(brown)
    pooled = float(np.sqrt((g.std(ddof=1) ** 2 + b.std(ddof=1) ** 2) / 2))
    return (float(g.mean()) - float(b.mean())) / pooled, pooled


def discrimination(collected):
    """§5.4 and §5.8 -- what each quantity separates, and how the index's margins fall."""
    green, brown = collected["GREEN"], collected["BROWN"]
    print("=== §5.4  WHAT EACH QUANTITY SEPARATES")
    print("   %-16s %9s %9s %9s %8s" % ("quantity", "green", "brown", "green/brown", "d"))
    print("   " + "-" * 58)
    for key in ("A_Q", "B_Q", "B_Soret", "S/Q lin"):
        g = [r[key] for r in green]
        b = [r[key] for r in brown]
        d, _ = cohensD(g, b)
        print("   %-16s %9.4f %9.4f %9.3f %8.2f"
              % (key, np.mean(g), np.mean(b), np.mean(g) / np.mean(b), d))
    print()

    print("=== §5.8  PERFORMANCE of the index, and its margins")
    g = [r["S/Q lin"] for r in green]
    b = [r["S/Q lin"] for r in brown]
    d, pooled = cohensD(g, b)
    gap = float(np.mean(g)) - float(np.mean(b))
    print("   green  mean %.4f  sd %.4f   (n=%d)" % (np.mean(g), np.std(g, ddof=1), len(g)))
    print("   brown  mean %.4f  sd %.4f   (n=%d)" % (np.mean(b), np.std(b, ddof=1), len(b)))
    print("   gap %.4f = %.1f %% of the brown mean;  pooled sd %.4f;  Cohen's d %.2f"
          % (gap, 100 * gap / float(np.mean(b)), pooled, d))
    # The threshold belongs to the anchor: 12.5 was DERIVED on 620-630 (§16.20.4); 10.6 was the
    # 600-630 gauge's line and does not transfer.
    threshold = 12.5 if ANCHOR == "620" else 10.6
    for name, values in (("green", g), ("brown", b)):
        sd = float(np.std(values, ddof=1))
        print("   %s margin to T = %.1f: %+.2f sigma"
              % (name, threshold, abs(float(np.mean(values)) - threshold) / sd))
    print()


def naiveVsFitted(collected, nearC, farC, soretC, qC):
    """§5.5's caveat -- the real least-squares line is steeper than the two-centroid chord, and the
    extra steepness pivots near the Q band, which is why the identity survives as an approximation."""
    print("=== §5.5  THE REAL FIT vs THE TWO-CENTROID CHORD")
    weighted = (nearC + farC) / 2.0          # equal window weight => the midpoint of the two centroids
    print("   anchor centroids  near %.2f nm   far %.2f nm   -> weighted centroid %.2f nm"
          % (nearC, farC, weighted))
    print("   Q band centroid %.2f nm  -> the extra steepness pivots %.1f nm from Q"
          % (qC, abs(weighted - qC)))
    print("   %-8s %14s %14s %10s" % ("class", "chord slope", "fitted slope", "steeper by"))
    print("   " + "-" * 52)
    for name, rows in (("green", collected["GREEN"]), ("brown", collected["BROWN"])):
        chord = float(np.mean([(r["A_far"] - r["A_near"]) / (farC - nearC) for r in rows]))
        fitted = float(np.mean([r["slope"] for r in rows]))
        print("   %-8s %14.3e %14.3e %9.1f %%"
              % (name, chord, fitted, 100 * (fitted / chord - 1)))
    print()


if __name__ == "__main__":
    main()
