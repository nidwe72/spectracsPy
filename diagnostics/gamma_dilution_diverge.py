"""Why do two dilutions of the SAME oil give diverging pigment ratios? (Edwin 2026-07-27, A=8ml+2drops,
B=6ml+2drops.) Replays the archived report PDFs and asks the questions in order:

  1. which decode model produced each run (the §17.6/8 captureDecode stamp — is this pre- or post-§17 data?)
  2. how dark does the SAMPLE actually get in the Soret band, in CAMERA DN — the units that decide whether
     absorbance is measurement or censored noise
  3. how many bins are lost outright (S<=0 -> AbsorptionLogicModule drops the bin; T>1 -> negative A)
  4. the band means and the ratio, and how the ratio moves if the Soret band is placed higher

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python diagnostics/gamma_dilution_diverge.py [runName ...]
"""
import json
import os
import sys

import numpy as np
import pypdf

from sciens.spectracs.logic.spectral.absorption.AbsorptionLogicModule import AbsorptionLogicModule
from sciens.spectracs.logic.spectral.absorption.AbsorptionLogicModuleParameters import AbsorptionLogicModuleParameters
from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil
from sciens.spectracs.model.spectral.Spectrum import Spectrum

REPORTS = os.path.join(
    os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")),
    "spectracs-references", "tmp")

SORET = (440.0, 460.0)      # the pigment numerator band (SPEC_pumpkin_peak_ratio_eval.md §1b)
Q = (560.0, 580.0)          # the denominator band
ALTERNATIVES = [(440, 460), (445, 465), (450, 470), (455, 475), (460, 480)]


def load(name):
    reader = pypdf.PdfReader(os.path.join(REPORTS, "measurement_report_%s.pdf" % name))
    workflow = json.loads(reader.attachments["workflow.json"][0])
    reference = sample = None
    for phase in workflow["phases"]:
        for step in phase.get("steps", []):
            spectra = step.get("spectra") or {}
            if "REFERENCE" in spectra and reference is None:
                reference = {float(k): float(v) for k, v in spectra["REFERENCE"].items()}
            if "SAMPLE" in spectra and sample is None:
                sample = {float(k): float(v) for k, v in spectra["SAMPLE"].items()}
    return workflow.get("header", {}), reference, sample


def spectrum(values):
    s = Spectrum()
    s.valuesByNanometers = dict(values)
    return s


def absorbance(reference, sample):
    parameters = AbsorptionLogicModuleParameters()
    parameters.setReference(spectrum(reference))
    parameters.setSample(spectrum(sample))
    return AbsorptionLogicModule().absorption(parameters).getSpectrum().valuesByNanometers


def toDn(value, decoded):
    # Report intensities in CAMERA DN. A linearized run must be mapped back through the decode's inverse;
    # a pre-§17 run already IS in DN.
    if not decoded:
        return value
    return SpectralColorUtil().encodeGammaFraction(max(0.0, value) / 255.0)


def band(values, low, high):
    return [v for nm, v in values.items() if low <= nm <= high]


def report(name):
    header, reference, sample = load(name)
    decoded = bool(header.get("captureDecode"))
    absorption = absorbance(reference, sample)

    sampleSoret = [(nm, v) for nm, v in sample.items() if SORET[0] <= nm <= SORET[1]]
    referenceSoret = [v for nm, v in reference.items() if SORET[0] <= nm <= SORET[1]]
    sampleDn = [toDn(v, decoded) for _nm, v in sampleSoret]
    referenceDn = [toDn(v, decoded) for v in referenceSoret]

    zeros = sum(1 for _nm, v in sampleSoret if v <= 0.0)
    dropped = sum(1 for nm, _v in sampleSoret if nm not in absorption)
    soret = band(absorption, *SORET)
    q = band(absorption, *Q)
    ratio = (np.mean(soret) / np.mean(q)) if soret and q else float("nan")

    print("=== %s%s" % (name, "   [captureDecode=%s]" % header["captureDecode"] if decoded else "   [pre-§17, DN]"))
    print("   SAMPLE in Soret 440-460 : min %.2f DN, median %.2f DN, max %.2f DN   (%d bins)"
          % (min(sampleDn), float(np.median(sampleDn)), max(sampleDn), len(sampleDn)))
    print("   REFERENCE same band     : min %.1f DN, median %.1f DN" % (min(referenceDn), float(np.median(referenceDn))))
    print("   bins at/below 1 DN: %d | exactly 0 (A undefined -> DROPPED): %d | missing from A: %d"
          % (sum(1 for v in sampleDn if v <= 1.0), zeros, dropped))
    print("   A(Soret) mean %.3f   A(Q) mean %.3f   RATIO %.3f" % (np.mean(soret), np.mean(q), ratio))
    return dict(name=name, decoded=decoded, absorption=absorption, sampleDn=sampleDn, ratio=ratio,
                sample=sample, reference=reference)


def main(names):
    runs = [report(name) for name in names]
    if len(runs) < 2:
        return 0

    print("\n--- ratio vs Soret band placement (does moving off the floor reconcile them?) ---")
    print("%-14s %s" % ("band", "  ".join("%-12s" % run["name"] for run in runs) + "   spread"))
    for low, high in ALTERNATIVES:
        ratios = []
        for run in runs:
            soret = band(run["absorption"], low, high)
            q = band(run["absorption"], *Q)
            ratios.append(np.mean(soret) / np.mean(q) if soret and q else float("nan"))
        spread = (max(ratios) - min(ratios)) / np.mean(ratios) * 100.0
        print("%-14s %s   %5.1f%%" % ("%d-%d" % (low, high),
                                      "  ".join("%-12.3f" % r for r in ratios), spread))

    print("\n--- minimum sample DN per band (why the low bands can't be trusted) ---")
    for low, high in ALTERNATIVES:
        line = []
        for run in runs:
            dn = [toDn(v, run["decoded"]) for nm, v in run["sample"].items() if low <= nm <= high]
            line.append("%-12.2f" % min(dn))
        print("%-14s %s" % ("%d-%d" % (low, high), "  ".join(line)))

    print("\n--- is a global normalization the answer? (a ratio of two band means is ALREADY scale-free) ---")
    for run in runs:
        absorption = run["absorption"]
        peak = max(absorption.values())
        normalized = {nm: v / peak for nm, v in absorption.items()}
        raw = np.mean(band(absorption, *SORET)) / np.mean(band(absorption, *Q))
        norm = np.mean(band(normalized, *SORET)) / np.mean(band(normalized, *Q))
        print("   %-14s ratio raw %.6f   ratio peak-normalized %.6f   (difference %.2e)"
              % (run["name"], raw, norm, abs(raw - norm)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["NowSteirerkraftA", "NowSteirerkraftB", "NowSteirerkraft"]))
