"""Does the BLANK's own spectral tilt predict a run's metric error? (SPEC_capture_quality.md §16.10)

The mechanism in §16.10.1 says a re-seated jar steers the beam, which shows up as a tilt. The blank is
measured every run through the same geometry — so if the mechanism is right, R's own tilt should carry a
fingerprint of that run's seating, and the metric's within-class deviation should track it.

Three questions, in order of what they'd buy:
  Q1  does R-tilt correlate with the RAW ratio's deviation?      -> tests the mechanism
  Q2  does it correlate LESS with the LINEAR-BASELINE residual?  -> tests that the fix works as claimed
  Q3  does regressing it out improve separation further?         -> tests whether it is worth using

Diagnostic only. Run:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/reference_tilt_covariate.py
"""
import json
import numpy as np
from pypdf import PdfReader

from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.plugin_sdk.util.SpectrumFeatureUtil import SpectrumFeatureUtil
from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin

BASE = "/home/nidwe72/development/spectracs/spectracs-references/tmp/"
plugin, feature = DevSpectralPlugin(), SpectrumFeatureUtil()
SORET, Q, WINDOWS = plugin.PB_SORET_BAND, plugin.PB_Q_BAND, plugin.PB_BASELINE_WINDOWS_LEGACY_600   # 600-630 — the anchor this script's published numbers were measured on (§16.20)

FILLS = [("green", "green B", ["20260727B/%03d.pdf" % i for i in range(1, 10)]),
         ("green", "green E", ["20260727E/%03d.pdf" % i for i in range(1, 8)]),
         ("brown", "brown C", ["20260727C/%03d.pdf" % i for i in range(1, 7)]),
         ("brown", "brown D", ["20260727D/%03d.pdf" % i for i in range(1, 4)])]


def spectra(path):
    """The de-spiked ABSORPTION plus the run's own REFERENCE (blank)."""
    workflow = json.loads(PdfReader(BASE + path).attachments["workflow.json"][0])
    found = {}
    for phase in workflow["phases"]:
        for step in phase.get("steps", []):
            for role in ("ABSORPTION", "REFERENCE"):
                raw = step.get("spectra", {}).get(role)
                if raw is not None and role not in found:
                    spectrum = Spectrum()
                    spectrum.valuesByNanometers = {float(k): float(v) for k, v in
                                                   raw.get("valuesByNanometers", raw).items()}
                    found[role] = spectrum
    return (plugin._DevSpectralPlugin__despikedAbsorption(found["ABSORPTION"]), found["REFERENCE"])


def referenceTilt(reference):
    """A scalar for the blank's SHAPE: the slope of log10(R) across the working range, per 100 nm.

    log, not linear: a throughput change scales R and would shift a linear slope, whereas in log space a
    pure scaling is a constant offset and leaves the slope alone. So this reads SHAPE, not brightness --
    which is what a beam-steering tilt actually changes."""
    lam = np.array(sorted(reference.valuesByNanometers))
    values = np.array([reference.valuesByNanometers[k] for k in lam])
    keep = (lam >= 440.0) & (lam <= 630.0) & (values > 1.0)      # >1 DN: below that it is noise, not signal
    slope = np.polyfit(lam[keep], np.log10(values[keep]), 1)[0]
    return slope * 100.0


def metrics(absorption):
    lam = np.array(sorted(absorption.valuesByNanometers))
    raw = np.array([absorption.valuesByNanometers[k] for k in lam])
    corrected = feature.linearBaselineCorrected(absorption, WINDOWS)
    fixed = np.array([corrected.valuesByNanometers[k] for k in lam])

    def band(values, window):
        return values[(lam >= window[0]) & (lam <= window[1])].mean()

    return band(raw, SORET) / band(raw, Q), band(fixed, SORET) / band(fixed, Q)


def centreWithinClass(values, labels):
    """Deviation from the run's OWN class mean, as a fraction -- so the green/brown difference is removed
    and only the run-to-run error remains."""
    values, out = np.array(values), np.zeros(len(values))
    for label in set(labels):
        mask = np.array([l == label for l in labels])
        out[mask] = values[mask] / values[mask].mean() - 1.0
    return out


def report(name, tilt, deviation):
    correlation = np.corrcoef(tilt, deviation)[0, 1]
    n = len(tilt)
    t = abs(correlation) * np.sqrt((n - 2) / max(1e-12, 1 - correlation ** 2))
    print("   %-24s r = %+.3f   t = %4.2f (n=%d)   %s"
          % (name, correlation, t, n, "SIGNIFICANT" if t > 2.07 else "not significant (needs |t|>2.07)"))
    return correlation


def main():
    rows = []
    for label, fill, paths in FILLS:
        for path in paths:
            absorption, reference = spectra(path)
            rawRatio, linearRatio = metrics(absorption)
            rows.append((label, fill, path, referenceTilt(reference), rawRatio, linearRatio))

    labels = [r[0] for r in rows]
    tilt = np.array([r[3] for r in rows])
    rawDeviation = centreWithinClass([r[4] for r in rows], labels)
    linDeviation = centreWithinClass([r[5] for r in rows], labels)

    print("=== THE BLANK'S OWN TILT, per fill   (slope of log10 R, per 100 nm)\n")
    for _, fill, _ in [(f[0], f[1], f[2]) for f in FILLS]:
        group = [r[3] for r in rows if r[1] == fill]
        print("   %-9s n=%d   mean %+.4f   spread %+.4f .. %+.4f"
              % (fill, len(group), np.mean(group), min(group), max(group)))
    print("   %-9s        ALL runs span %+.4f .. %+.4f" % ("", tilt.min(), tilt.max()))

    print("\n=== Q1/Q2  does the blank's tilt predict the metric's within-class error?\n")
    rawR = report("S/Q raw", tilt, rawDeviation)
    linR = report("S/Q linear base", tilt, linDeviation)
    print("\n   variance of the metric error explained by the blank's tilt:")
    print("      raw            %5.1f %%" % (100 * rawR ** 2))
    print("      linear base    %5.1f %%" % (100 * linR ** 2))

    print("\n=== Q3  would regressing it out help?\n")
    for name, values, deviation in (("S/Q raw", [r[4] for r in rows], rawDeviation),
                                    ("S/Q linear base", [r[5] for r in rows], linDeviation)):
        values = np.array(values)
        slope, intercept = np.polyfit(tilt, deviation, 1)
        corrected = values / (1.0 + (slope * tilt + intercept))
        for tag, series in (("before", values), ("after ", corrected)):
            green = series[np.array([l == "green" for l in labels])]
            brown = series[np.array([l == "brown" for l in labels])]
            pooled = np.sqrt(((len(green)-1)*green.var(ddof=1) + (len(brown)-1)*brown.var(ddof=1)) /
                             (len(green)+len(brown)-2))
            gap = green.min() - brown.max()
            print("   %-16s %s  d = %5.2f   gap %+7.3f %s"
                  % (name if tag == "before" else "", tag, (green.mean()-brown.mean())/pooled, gap,
                     "" if gap > 0 else "(OVERLAP)"))
        print()


if __name__ == "__main__":
    main()
