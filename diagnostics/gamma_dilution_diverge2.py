"""Follow-up to gamma_dilution_diverge.py: the Soret band is NOT on the floor in A/B, so the divergence has
another cause. Tests the three candidates in order:

  A) is it CONCENTRATION only?      -> A(lambda) should scale by ONE factor k at every wavelength
  B) is it an ADDITIVE BASELINE?    -> the deep-red anchor (oil absorbs ~nothing there) should read ~0
  C) is it the REFERENCE?           -> compare the two runs' reference SHAPES (normalized)
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

BANDS = [("Soret 440-460", 440, 460), ("blue-green 460-510", 460, 510), ("clarity 510-540", 510, 540),
         ("Q 560-580", 560, 580), ("red anchor 600-630", 600, 630)]


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


def absorbance(reference, sample):
    parameters = AbsorptionLogicModuleParameters()
    for setter, values in ((parameters.setReference, reference), (parameters.setSample, sample)):
        s = Spectrum()
        s.valuesByNanometers = dict(values)
        setter(s)
    return AbsorptionLogicModule().absorption(parameters).getSpectrum().valuesByNanometers


def mean(values, low, high):
    selected = [v for nm, v in values.items() if low <= nm <= high]
    return float(np.mean(selected)) if selected else float("nan")


def main(names):
    runs = []
    for name in names:
        header, reference, sample = load(name)
        runs.append(dict(name=name, header=header, reference=reference, sample=sample,
                         absorption=absorbance(reference, sample)))

    print("=== (A)+(B) band absorbances — a pure dilution change scales EVERY band by the same factor ===")
    print("%-22s %s" % ("band", "  ".join("%-10s" % r["name"][-1] for r in runs) + "   B/A"))
    for label, low, high in BANDS:
        values = [mean(r["absorption"], low, high) for r in runs]
        factor = values[1] / values[0] if len(values) > 1 and values[0] else float("nan")
        print("%-22s %s   %5.2f" % (label, "  ".join("%-10.4f" % v for v in values), factor))

    print("\n   ^ if these B/A factors are NOT all equal, it is not concentration alone.")
    print("   ^ 'red anchor' should be ~0 for pumpkin oil: whatever it reads is the ADDITIVE baseline.")

    print("\n=== (B) what the ratio becomes once the red-anchor baseline is subtracted ===")
    print("%-22s %-12s %-12s %-12s" % ("run", "ratio raw", "baseline", "ratio debaselined"))
    for run in runs:
        baseline = mean(run["absorption"], 600, 630)
        soret, q = mean(run["absorption"], 440, 460), mean(run["absorption"], 560, 580)
        print("%-22s %-12.3f %-12.4f %-12.3f" % (run["name"], soret / q, baseline,
                                                 (soret - baseline) / (q - baseline)))

    print("\n=== (C) reference SHAPE, normalized to each run's own peak (drift between runs corrupts T) ===")
    print("%-22s %s" % ("band", "  ".join("%-10s" % r["name"][-1] for r in runs) + "   B/A"))
    for label, low, high in BANDS:
        shares = []
        for run in runs:
            peak = max(run["reference"].values())
            shares.append(mean(run["reference"], low, high) / peak)
        factor = shares[1] / shares[0] if len(shares) > 1 and shares[0] else float("nan")
        print("%-22s %s   %5.3f" % (label, "  ".join("%-10.4f" % s for s in shares), factor))

    print("\n=== sample/reference levels in CAMERA DN (is anything near the floor or the ceiling?) ===")
    util = SpectralColorUtil()
    for run in runs:
        decoded = bool(run["header"].get("captureDecode"))
        def dn(value):
            return util.encodeGammaFraction(max(0.0, value) / 255.0) if decoded else value
        print("   %-22s reference peak %6.1f DN | sample min %6.2f DN | sample peak %6.1f DN"
              % (run["name"], dn(max(run["reference"].values())),
                 dn(min(run["sample"].values())), dn(max(run["sample"].values()))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["NowSteirerkraftA", "NowSteirerkraftB"]))
