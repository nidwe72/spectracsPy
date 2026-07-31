"""Is the within-set scatter the DILUTION SETTLING or the seating? (SPEC_capture_quality.md §16.12.6)

Two analyses over the same loaded runs, no rig time — both read PDFs already on disk.

  A - DETREND.  A CV discards run order, so a monotone settling trend masquerades as repeatability.
      Fit `metric = a + b*t + residual` against ELAPSED TIME and report raw CV vs residual CV.
      Residual CV collapsing => set B was settling, not seating, and §16.11.9's budget closure is
      two similar numbers meeting by coincidence (§16.12.5).

  B - LAMBDA^-n BASELINE.  Scattering goes as lambda^-n (n~4 for particles << lambda). The shipped
      LINEAR baseline cannot follow that curve and leaks ~0.50*s into the Soret band while leaking
      -0.04*s into Q - opposite signs, so it survives the ratio (§16.12.4). Fit `A = s*(530/lam)^n`
      through the same two oil-quiet windows, subtract that instead, and ask whether the time series
      collapses onto its settled value.

Run:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/settling_sweep.py
"""
import json
import os

import numpy as np
from pypdf import PdfReader
from scipy.optimize import curve_fit

from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.plugin_sdk.util.SpectrumFeatureUtil import SpectrumFeatureUtil
from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin

BASE = "/home/nidwe72/development/spectracs/spectracs-references/tmp/"
plugin, feature = DevSpectralPlugin(), SpectrumFeatureUtil()
SORET, Q, WINDOWS = plugin.PB_SORET_BAND, plugin.PB_Q_BAND, plugin.PB_BASELINE_WINDOWS
PIVOT = 530.0                       # the amplitude `s` is quoted AT this wavelength (§16.12.4's table)

# The rig-rebuild sets of 2026-07-29 (§16.11). Directory names carry a 2027 typo on disk; the mtimes
# are the real capture times and are what the elapsed-time axis is built from - `timestampIso` is
# None in every embedded workflow.json, so there is no in-band clock to prefer.
SETS = [("set B  green, 6 re-seats of one fill", ["20270729B/%03d.pdf" % i for i in range(1, 7)]),
        ("set C  green, 6 re-seats of one fill", ["20270729C/%03d.pdf" % i for i in range(1, 7)])]


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


def asArrays(spectrum):
    lam = np.array(sorted(spectrum.valuesByNanometers))
    return lam, np.array([spectrum.valuesByNanometers[k] for k in lam])


def bandMean(lam, values, window):
    return float(values[(lam >= window[0]) & (lam <= window[1])].mean())


def quietMask(lam):
    mask = np.zeros_like(lam, dtype=bool)
    for window in WINDOWS:
        mask |= (lam >= window[0]) & (lam <= window[1])
    return mask


def powerLawBaseline(lam, raw):
    """Fit `A = s*(PIVOT/lam)**n` through both oil-quiet windows. Returns (baseline, s, n).

    n is allowed to go NEGATIVE. Pinning it at 0 would hide the answer: the question is what the
    quiet windows actually contain, and 'it rises with wavelength' is a legitimate outcome.
    """
    x, y = lam[quietMask(lam)], raw[quietMask(lam)]

    def model(wavelength, amplitude, exponent):
        return amplitude * (PIVOT / wavelength) ** exponent

    try:
        (amplitude, exponent), _ = curve_fit(model, x, y, p0=[max(y.mean(), 1e-4), 4.0],
                                             bounds=([0.0, -4.0], [np.inf, 8.0]), maxfev=20000)
    except RuntimeError:
        return np.zeros_like(lam), float("nan"), float("nan")
    return model(lam, amplitude, exponent), float(amplitude), float(exponent)


def offsetPlusScatter(lam, raw):
    """Fit `A = c + s*(PIVOT/lam)**n`, so a flat floor cannot masquerade as n -> 0. Returns (c, s, n).

    ⚠ Poorly conditioned by construction: both windows lie inside 520-630 nm, and over so short a
    span a power law is nearly indistinguishable from offset+slope. Read the SHAPE RATIO below in
    preference to these three numbers - it is model-free.
    """
    x, y = lam[quietMask(lam)], raw[quietMask(lam)]

    def model(wavelength, floor, amplitude, exponent):
        return floor + amplitude * (PIVOT / wavelength) ** exponent

    try:
        (floor, amplitude, exponent), _ = curve_fit(
            model, x, y, p0=[y.min(), max(y.ptp(), 1e-4), 4.0],
            bounds=([-np.inf, 0.0, 0.0], [np.inf, np.inf, 8.0]), maxfev=40000)
    except RuntimeError:
        return float("nan"), float("nan"), float("nan")
    return float(floor), float(amplitude), float(exponent)


def measure(path):
    """Every quantity this sweep needs, for one run."""
    spectrum = despikedAbsorption(path)
    lam, raw = asArrays(spectrum)
    linear = feature.linearBaselineCorrected(spectrum, WINDOWS)
    _, linearValues = asArrays(linear)
    baseline, amplitude, exponent = powerLawBaseline(lam, raw)
    powerValues = raw - baseline
    floor, floorAmplitude, floorExponent = offsetPlusScatter(lam, raw)

    # MODEL-FREE shape diagnostic: what the two quiet windows actually do across 530 -> 615 nm.
    # lambda^-4 (Rayleigh, particles << lambda) predicts 1.81; lambda^-2 predicts 1.35;
    # 1.00 means WAVELENGTH-FLAT, i.e. particles LARGER than the wavelength (Mie/geometric) - or a
    # plain offset that is not scattering at all.
    near, far = bandMean(lam, raw, WINDOWS[0]), bandMean(lam, raw, WINDOWS[1])

    return {"quiet 530/615": near / far if far else float("nan"),
            "A_near 520-540": near,          # the baseline's NEAR anchor, as a quantity in its own right
            "A_far 600-630": far,            # the FAR anchor - the third measuring region (§2.1a)
            "quiet A@530": near,
            "A_Soret raw": bandMean(lam, raw, SORET),
            "A_Q raw": bandMean(lam, raw, Q),
            "S/Q raw": bandMean(lam, raw, SORET) / bandMean(lam, raw, Q),
            "A_Soret linear": bandMean(lam, linearValues, SORET),
            "A_Q linear": bandMean(lam, linearValues, Q),
            "S/Q linear base": bandMean(lam, linearValues, SORET) / bandMean(lam, linearValues, Q),
            "S/Q power base": bandMean(lam, powerValues, SORET) / bandMean(lam, powerValues, Q),
            "scatter s @530": amplitude,
            "scatter n": exponent,
            "3par floor c": floor,
            "3par s": floorAmplitude,
            "3par n": floorExponent}


def detrend(times, values):
    """(rawCV%, residualCV%, trendOverSet%, tStatistic) - is there a trend, and does removing it help?"""
    values = np.asarray(values, dtype=float)
    times = np.asarray(times, dtype=float)
    mean = values.mean()
    rawCv = values.std(ddof=1) / abs(mean) * 100.0
    slope, intercept = np.polyfit(times, values, 1)
    residual = values - (slope * times + intercept)
    # two parameters were fitted, so the residual SD carries n-2 degrees of freedom
    residualSd = float(np.sqrt((residual ** 2).sum() / (len(values) - 2)))
    # t = slope / se(slope); with n=6 that is 4 df, so |t| > 2.78 is p < 0.05 two-sided
    spread = float(((times - times.mean()) ** 2).sum())
    standardError = residualSd / np.sqrt(spread) if spread else float("inf")
    tStatistic = slope / standardError if standardError else 0.0
    span = times.max() - times.min()
    return rawCv, residualSd / abs(mean) * 100.0, slope * span / abs(mean) * 100.0, tStatistic


def main():
    print(__doc__.split("Run:")[0].strip().splitlines()[0])
    print()

    loaded = []
    for name, paths in SETS:
        runs = []
        for path in paths:
            stamp = os.path.getmtime(BASE + path)
            runs.append((stamp, path, measure(path)))
        start = runs[0][0]
        runs = [((stamp - start) / 60.0, path, values) for stamp, path, values in runs]
        loaded.append((name, runs))

    # ---------------------------------------------------------------- per-run table
    for name, runs in loaded:
        print("=== %s" % name)
        print("   %-9s %6s %8s %8s %13s %12s %9s %10s" % (
            "run", "t/min", "A_Soret", "A_Q", "S/Q lin base", "S/Q pow base", "A@530",
            "530/615"))
        print("   " + "-" * 84)
        for elapsed, path, v in runs:
            print("   %-9s %6.1f %8.3f %8.3f %13.3f %12.3f %9.4f %10.3f" % (
                os.path.basename(path), elapsed, v["A_Soret raw"], v["A_Q raw"],
                v["S/Q linear base"], v["S/Q power base"], v["quiet A@530"], v["quiet 530/615"]))
        print()

    # ---------------------------------------------------------------- A: detrend
    print("=== A - DETREND  (§16.12.5: does removing the time trend collapse the CV?)")
    print("   raw CV = spread about the mean, order-blind.  resid CV = spread about the fitted line.")
    print("   trend  = what the fitted line alone sweeps across the set, as %% of the mean.\n")
    metrics = ["S/Q raw", "S/Q linear base", "S/Q power base",
               "A_Soret raw", "A_Q raw", "A_near 520-540", "A_far 600-630"]
    for name, runs in loaded:
        times = [r[0] for r in runs]
        print("   %s" % name)
        print("      %-18s %9s %9s %9s %8s %8s" % ("metric", "raw CV%", "resid CV%", "trend%",
                                                   "t", "p<0.05"))
        print("      " + "-" * 68)
        for metric in metrics:
            values = [r[2][metric] for r in runs]
            rawCv, residualCv, trend, tStatistic = detrend(times, values)
            print("      %-18s %9.2f %9.2f %9.2f %8.2f %8s" % (
                metric, rawCv, residualCv, trend, tStatistic,
                "YES" if abs(tStatistic) > 2.78 else "-"))       # 4 df, two-sided
        print()

    # ---------------------------------------------------------------- pooled
    print("   POOLED B+C  (each set centred on its own mean, then residuals pooled - §16.12.6)")
    print("      %-18s %9s %9s %8s" % ("metric", "raw CV%", "resid CV%", "n"))
    print("      " + "-" * 48)
    for metric in metrics:
        rawParts, residualParts, count = [], [], 0
        for name, runs in loaded:
            times = np.array([r[0] for r in runs])
            values = np.array([r[2][metric] for r in runs])
            mean = values.mean()
            slope, intercept = np.polyfit(times, values, 1)
            rawParts.append((values - mean) / mean)
            residualParts.append((values - (slope * times + intercept)) / mean)
            count += len(values)
        rawCv = float(np.sqrt((np.concatenate(rawParts) ** 2).sum() / (count - len(loaded)))) * 100
        residualCv = float(np.sqrt((np.concatenate(residualParts) ** 2).sum() /
                                   (count - 2 * len(loaded)))) * 100
        print("      %-18s %9.2f %9.2f %8d" % (metric, rawCv, residualCv, count))
    print()

    # ---------------------------------------------------------------- B: scatter fit
    print("=== B - LAMBDA^-n FIT  (§16.12.6: is there scatter, and are the droplets growing?)")
    print("   MODEL-FREE first. The 530/615 ratio is what the quiet windows actually do:")
    print("      1.81 => lambda^-4, Rayleigh, particles MUCH SMALLER than lambda (ouzo nanodroplets)")
    print("      1.35 => lambda^-2")
    print("      1.00 => WAVELENGTH-FLAT: particles LARGER than lambda (Mie), or a plain offset\n")
    for name, runs in loaded:
        times = [r[0] for r in runs]
        ratios = [r[2]["quiet 530/615"] for r in runs]
        exponents = [r[2]["scatter n"] for r in runs]
        amplitudes = [r[2]["scatter s @530"] for r in runs]
        threeParN = [r[2]["3par n"] for r in runs]
        threeParS = [r[2]["3par s"] for r in runs]
        print("   %s" % name)
        print("      530/615    %s   (slope %+.5f /min)  <- MODEL-FREE" %
              (" ".join("%5.3f" % r for r in ratios), np.polyfit(times, ratios, 1)[0]))
        print("      2-par n    %s   (slope %+.4f /min)" %
              (" ".join("%5.2f" % e for e in exponents), np.polyfit(times, exponents, 1)[0]))
        print("      2-par s    %s   (slope %+.5f /min)" %
              (" ".join("%5.3f" % a for a in amplitudes), np.polyfit(times, amplitudes, 1)[0]))
        print("      3-par n    %s   (offset+scatter; ill-conditioned, see docstring)" %
              " ".join("%5.2f" % e for e in threeParN))
        print("      3-par s    %s" % " ".join("%5.3f" % a for a in threeParS))
        print()


if __name__ == "__main__":
    main()
