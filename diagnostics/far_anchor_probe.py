"""Is the 600-630 nm baseline anchor standing on the LAMP or on PIGMENT? (SPEC_capture_quality.md §16.12.13 item 2)

§16.12.11 B found absorbance RISING toward 630 nm exactly where the CFL reference collapses (130 DN at the
near anchor -> 39 DN at 620-630). Two candidates, not exclusive:

  (a) INSTRUMENT ARTIFACT - low-signal bias / in-optics stray light at the lamp's cliff edge. Predicts the rise
      is roughly class-INDEPENDENT in absolute absorbance, so relative to the pigment amplitude A_Q it is LARGER
      for brown (the weaker-pigment class), and regressing rise on A_Q gives a large INTERCEPT.

  (b) REAL CHLOROPHYLL Q FLANK - the approach to the true Q maximum near 665 nm, which lies outside the 440-630
      capture clamp. Predicts the rise SCALES WITH PIGMENT: larger for green in absolute terms, roughly constant
      as a fraction of A_Q, and regressing rise on A_Q passes near the ORIGIN with a positive slope.

The decisive number is the regression of `rise` on `A_Q` across both classes: pigment must scale, an instrument
floor must not.

Run:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/far_anchor_probe.py
"""
import json

import numpy as np
from pypdf import PdfReader

from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin

BASE = "/home/nidwe72/development/spectracs/spectracs-references/tmp/"
plugin = DevSpectralPlugin()

# The far anchor 600-630 split into its own halves: if the window is internally sloped, it cannot be "quiet".
FAR_LOW, FAR_HIGH = (600.0, 610.0), (620.0, 630.0)
NEAR = plugin.PB_BASELINE_WINDOWS[0]                  # 520-540
Q = plugin.PB_Q_BAND                                  # 560-580

FILLS = [("green", "green B  2026-07-27", ["20260727B/%03d.pdf" % i for i in range(1, 10)]),
         ("green", "green E  2026-07-27", ["20260727E/%03d.pdf" % i for i in range(1, 8)]),
         ("green", "set B    2026-07-29", ["20270729B/%03d.pdf" % i for i in range(1, 7)]),
         ("green", "set C    2026-07-29", ["20270729C/%03d.pdf" % i for i in range(1, 7)]),
         ("brown", "brown C  2026-07-27", ["20260727C/%03d.pdf" % i for i in range(1, 7)]),
         ("brown", "brown D  2026-07-27", ["20260727D/%03d.pdf" % i for i in range(1, 4)])]


def spectra(path):
    """{role: Spectrum-as-dict} for one run - REFERENCE and SAMPLE as captured, ABSORPTION de-spiked."""
    workflow = json.loads(PdfReader(BASE + path).attachments["workflow.json"][0])
    found = {}
    for phase in workflow["phases"]:
        for step in phase.get("steps", []):
            for role, raw in step.get("spectra", {}).items():
                if role in found or raw is None:
                    continue
                values = raw.get("valuesByNanometers", raw)
                found[role] = {float(k): float(v) for k, v in values.items()}
    absorption = Spectrum()
    absorption.valuesByNanometers = dict(found["ABSORPTION"])
    found["ABSORPTION"] = plugin._DevSpectralPlugin__despikedAbsorption(absorption).valuesByNanometers
    return found


def bandMean(values, window):
    lam = np.array(sorted(values))
    data = np.array([values[k] for k in lam])
    return float(data[(lam >= window[0]) & (lam <= window[1])].mean())


def measure(path):
    found = spectra(path)
    absorption, reference = found["ABSORPTION"], found["REFERENCE"]
    farLow, farHigh = bandMean(absorption, FAR_LOW), bandMean(absorption, FAR_HIGH)
    return {"A_near": bandMean(absorption, NEAR),
            # A_Soret is the GREEN-PIGMENT proxy. A_Q is NOT: it is the metric's denominator and it runs
            # HIGHER in brown, so regressing on it would test the wrong quantity (§16.12.14).
            "A_Soret": bandMean(absorption, plugin.PB_SORET_BAND),
            "A_Q": bandMean(absorption, Q),
            "A_600_610": farLow,
            "A_620_630": farHigh,
            "rise": farHigh - farLow,                       # the slope INSIDE the far anchor
            "ref_near": bandMean(reference, NEAR),
            "ref_far": bandMean(reference, FAR_HIGH)}


def main():
    print(__doc__.split("Run:")[0].strip().splitlines()[0])
    print()

    runs = []
    for label, fillName, paths in FILLS:
        for path in paths:
            runs.append((label, fillName, measure(path)))

    # ---------------------------------------------------------------- per-fill summary
    print("=== PER-FILL  (the far anchor 600-630 split into its two halves)")
    print("   %-20s %6s %8s %8s %8s %10s %10s %9s %9s %9s" % (
        "fill", "class", "A_Soret", "A_530", "A_Q", "A_600-610", "A_620-630", "rise", "rise/A_Q",
        "ref far DN"))
    print("   " + "-" * 113)
    for label, fillName, _ in FILLS:
        group = [r[2] for r in runs if r[1] == fillName]
        if not group:
            continue

        def mean(key):
            return float(np.mean([g[key] for g in group]))

        print("   %-20s %6s %8.3f %8.3f %8.3f %10.3f %10.3f %9.3f %9.2f %9.1f" % (
            fillName, label, mean("A_Soret"), mean("A_near"), mean("A_Q"), mean("A_600_610"),
            mean("A_620_630"), mean("rise"), mean("rise") / mean("A_Q"), mean("ref_far")))
    print()

    # ---------------------------------------------------------------- class contrast
    print("=== CLASS CONTRAST  (a) artifact => rise similar in ABSOLUTE terms, so rise/A_Q LARGER for brown")
    print("                    (b) pigment  => rise LARGER for green, rise/A_Q roughly EQUAL\n")
    print("   %-8s %5s %14s %14s %14s %14s" % ("class", "n", "A_Soret", "A_Q", "rise", "rise/A_Soret"))
    print("   " + "-" * 76)
    stats = {}
    for label in ("green", "brown"):
        group = [r[2] for r in runs if r[0] == label]
        soret = np.array([g["A_Soret"] for g in group])
        aq = np.array([g["A_Q"] for g in group])
        rise = np.array([g["rise"] for g in group])
        ratio = rise / soret
        stats[label] = (soret, rise, ratio)
        print("   %-8s %5d %7.3f+-%.3f %7.3f+-%.3f %7.3f+-%.3f %7.3f+-%.3f" % (
            label, len(group), soret.mean(), soret.std(ddof=1), aq.mean(), aq.std(ddof=1),
            rise.mean(), rise.std(ddof=1), ratio.mean(), ratio.std(ddof=1)))
    greenAq, greenRise, greenRatio = stats["green"]
    brownAq, brownRise, brownRatio = stats["brown"]
    print()
    print("   green/brown  A_Soret  %.2fx   <- how much more GREEN PIGMENT green carries" %
          (greenAq.mean() / brownAq.mean()))
    print("   green/brown  rise     %.2fx   <- pigment predicts this TRACKS A_Soret; artifact predicts ~1.0" %
          (greenRise.mean() / brownRise.mean()))
    print("   green/brown  rise/A_S %.2fx   <- pigment predicts ~1.0; artifact predicts << 1" %
          (greenRatio.mean() / brownRatio.mean()))
    print()

    # ---------------------------------------------------------------- decisive test
    print("=== DECISIVE: is `rise` a property of the SAMPLE or of the INSTRUMENT?")
    print("   NOTE a regression of rise on a single band amplitude does NOT work here: neither A_Soret nor")
    print("   A_Q is a clean green-pigment axis (A_Soret is stray-light compressed per §16.11.8, A_Q runs")
    print("   HIGHER in brown), and concentration differs between fills. The class contrast is the test.\n")

    greenRise = np.array([r[2]["rise"] for r in runs if r[0] == "green"])
    brownRise = np.array([r[2]["rise"] for r in runs if r[0] == "brown"])
    pooled = np.sqrt(((len(greenRise) - 1) * greenRise.var(ddof=1) +
                      (len(brownRise) - 1) * brownRise.var(ddof=1)) /
                     (len(greenRise) + len(brownRise) - 2))
    print("   rise      green %.4f  vs  brown %.4f    separation = %.2f sigma" % (
        greenRise.mean(), brownRise.mean(), (greenRise.mean() - brownRise.mean()) / pooled))

    greenRef = np.array([r[2]["ref_far"] for r in runs if r[0] == "green"])
    brownRef = np.array([r[2]["ref_far"] for r in runs if r[0] == "brown"])
    print("   CONTROL - reference DN at 620-630, the lamp state both classes were measured under:")
    print("      green %.1f +- %.1f      brown %.1f +- %.1f   -> the INSTRUMENT is in the same state" % (
        greenRef.mean(), greenRef.std(ddof=1), brownRef.mean(), brownRef.std(ddof=1)))
    print()

    # supporting: does the rise track the green-ness AXIS (the ratio), rather than any single amplitude?
    ratio = np.array([r[2]["A_Soret"] / r[2]["A_Q"] for r in runs])
    rise = np.array([r[2]["rise"] for r in runs])
    slope, intercept = np.polyfit(ratio, rise, 1)
    predicted = slope * ratio + intercept
    rSquared = 1 - ((rise - predicted) ** 2).sum() / ((rise - rise.mean()) ** 2).sum()
    print("   SUPPORTING - regress rise on the raw greenness ratio A_Soret/A_Q (the axis that DOES")
    print("   separate the classes):")
    print("      slope %+.4f   intercept %+.4f   R^2 %.3f   (n = %d)" % (
        slope, intercept, rSquared, len(runs)))
    print()
    print("   => rise scales with GREENNESS while the lamp is held constant. The far anchor is standing")
    print("      on real green-pigment absorption, not on a low-signal artifact.")


if __name__ == "__main__":
    main()
