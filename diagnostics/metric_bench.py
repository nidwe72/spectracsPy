"""Bench-compare candidate discriminators on the 2026-07-27 runs (SPEC_capture_quality.md §16.10).

Diagnostic only — commits to nothing. Scores every candidate the same way, on the same de-spiked
absorbance the plugin uses, so the comparison is like-for-like.

The scoring that matters is LEAVE-ONE-FILL-OUT, not leave-one-run-out: runs within a fill share a
seating state, so holding out a single run leaves its near-twins in training and inflates the score.
Four fills today — green B, green E, brown C, brown D.

Run:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/metric_bench.py
"""
import json
import numpy as np
from pypdf import PdfReader
from scipy.signal import savgol_filter

from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.plugin_sdk.util.EvaluationColorUtil import EvaluationColorUtil
from sciens.spectracs.plugin_sdk.util.SpectrumFeatureUtil import SpectrumFeatureUtil
from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin

BASE = "/home/nidwe72/development/spectracs/spectracs-references/tmp/"
plugin, feature, colour = DevSpectralPlugin(), SpectrumFeatureUtil(), EvaluationColorUtil()
SORET, Q, WINDOWS = plugin.PB_SORET_BAND, plugin.PB_Q_BAND, plugin.PB_BASELINE_WINDOWS

FILLS = [("green", "green B", ["20260727B/%03d.pdf" % i for i in range(1, 10)]),
         ("green", "green E", ["20260727E/%03d.pdf" % i for i in range(1, 8)]),
         ("brown", "brown C", ["20260727C/%03d.pdf" % i for i in range(1, 7)]),
         ("brown", "brown D", ["20260727D/%03d.pdf" % i for i in range(1, 4)])]


def despikedAbsorption(path):
    workflow = json.loads(PdfReader(BASE + path).attachments["workflow.json"][0])
    for phase in workflow["phases"]:
        for step in phase.get("steps", []):
            raw = step.get("spectra", {}).get("ABSORPTION")
            if raw is not None:
                spectrum = Spectrum()
                spectrum.valuesByNanometers = {float(k): float(v) for k, v in
                                               raw.get("valuesByNanometers", raw).items()}
                return plugin._DevSpectralPlugin__despikedAbsorption(spectrum)
    raise KeyError(path)


def candidates(spectrum):
    """Every candidate metric for one run, as {name: value}."""
    corrected = feature.linearBaselineCorrected(spectrum, WINDOWS)
    lam = np.array(sorted(spectrum.valuesByNanometers))
    raw = np.array([spectrum.valuesByNanometers[k] for k in lam])
    fixed = np.array([corrected.valuesByNanometers[k] for k in lam])

    def band(values, window):
        return values[(lam >= window[0]) & (lam <= window[1])]

    out = {}
    # --- the two we already have
    out["S/Q raw"] = band(raw, SORET).mean() / band(raw, Q).mean()
    out["S/Q linear base"] = band(fixed, SORET).mean() / band(fixed, Q).mean()
    # --- amplitude, but integrated rather than averaged
    out["area ratio"] = (np.trapz(band(fixed, SORET), band(lam, SORET)) /
                         np.trapz(band(fixed, Q), band(lam, Q)))
    # --- POSITION / SHAPE: immune to any multiplicative scaling, and to offset+slope after correction
    weight = np.clip(fixed, 0.0, None)                    # negative weights would make a centroid meaningless
    out["centroid nm"] = float((lam * weight).sum() / weight.sum())
    qWindow = (lam >= 555.0) & (lam <= 600.0)
    out["Q lambda-max"] = float(lam[qWindow][np.argmax(fixed[qWindow])])
    # --- 2nd derivative: annihilates ANY linear baseline exactly, without choosing windows
    second = savgol_filter(raw, window_length=31, polyorder=3, deriv=2)
    out["2nd-deriv ratio"] = abs(band(second, SORET).mean()) / max(abs(band(second, Q).mean()), 1e-9)
    # --- colour: chromaticity of the absorbance, invariant to A -> kA by construction
    hue, saturation, lightness = colour.spectrumToHsl(spectrum, converter="sRGB",
                                                      ceiling=EvaluationColorUtil.RELATIVE)
    out["absorbed hue"] = float(hue)
    return out


def bestThreshold(values, labels):
    """Threshold + direction minimising training errors. Returns (threshold, greenIsHigh, errors)."""
    order = sorted(set(values))
    cuts = [(a + b) / 2 for a, b in zip(order, order[1:])] or [order[0]]
    best = None
    for cut in cuts:
        for greenIsHigh in (True, False):
            wrong = sum(1 for value, label in zip(values, labels)
                        if ((value > cut) == greenIsHigh) != (label == "green"))
            if best is None or wrong < best[2]:
                best = (cut, greenIsHigh, wrong)
    return best


def main():
    runs = []          # (label, fillName, {metric: value})
    for label, fillName, paths in FILLS:
        for path in paths:
            runs.append((label, fillName, candidates(despikedAbsorption(path))))
    names = list(runs[0][2].keys())

    print("=== PER-CLASS VALUES (25 runs: 16 green, 9 brown)\n")
    print("   %-18s %-26s %-26s %6s %9s" % ("metric", "green (n=16)", "brown (n=9)", "d", "gap"))
    print("   " + "-" * 92)
    summary = {}
    for name in names:
        green = np.array([r[2][name] for r in runs if r[0] == "green"])
        brown = np.array([r[2][name] for r in runs if r[0] == "brown"])
        pooled = np.sqrt(((len(green)-1)*green.var(ddof=1) + (len(brown)-1)*brown.var(ddof=1)) /
                         (len(green)+len(brown)-2))
        d = (green.mean() - brown.mean()) / pooled if pooled else 0.0
        clean = green.min() > brown.max() or brown.min() > green.max()
        gap = (green.min() - brown.max()) if green.min() > brown.max() else (brown.min() - green.max())
        summary[name] = abs(d)
        print("   %-18s %-26s %-26s %6.2f %9s" % (
            name, "%8.3f [%8.3f..%8.3f]" % (green.mean(), green.min(), green.max()),
            "%8.3f [%8.3f..%8.3f]" % (brown.mean(), brown.min(), brown.max()),
            d, ("+%.3f" % gap) if clean else "OVERLAP"))

    print("\n=== SCORING")
    print("   in-sample = threshold fitted on all 25 runs (optimistic; a threshold always fits its own data)")
    print("   LOFO      = leave-one-FILL-out, threshold fitted on 3 fills and tested on the 4th\n")
    print("   %-18s %12s %12s %8s" % ("metric", "in-sample", "LOFO", "|d|"))
    print("   " + "-" * 54)
    scored = []
    for name in names:
        values = [r[2][name] for r in runs]
        labels = [r[0] for r in runs]
        _, _, inSample = bestThreshold(values, labels)
        lofo = 0
        for _, fillName, _ in FILLS:
            trainValues = [r[2][name] for r in runs if r[1] != fillName]
            trainLabels = [r[0] for r in runs if r[1] != fillName]
            cut, greenIsHigh, _ = bestThreshold(trainValues, trainLabels)
            lofo += sum(1 for r in runs if r[1] == fillName and
                        ((r[2][name] > cut) == greenIsHigh) != (r[0] == "green"))
        scored.append((lofo, inSample, name))
        print("   %-18s %9d/25 %9d/25 %8.2f" % (name, inSample, lofo, summary[name]))

    print("\n=== RANKING by leave-one-fill-out errors (ties broken by |d|)")
    for lofo, inSample, name in sorted(scored, key=lambda s: (s[0], -summary[s[2]])):
        print("   %2d/25 LOFO   %-18s (|d| %.2f)" % (lofo, name, summary[name]))


if __name__ == "__main__":
    main()
