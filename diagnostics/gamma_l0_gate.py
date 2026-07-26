"""L0 gate (SPEC_capture_quality.md §17.6/1, §17.7): does gamma linearization move the PERCEIVED hue,
i.e. the axis PumpkinOilPlugin's 47/66 verdict bands live on? Off-line replay from the report PDFs.

Also answers §17.6/3: how much of the spectral window the 1%-of-peak reference floor eats once it is
read in the LINEAR domain.
"""
import glob
import json
import os
import sys

import numpy as np
import pypdf

from sciens.spectracs.logic.spectral.transmission.TransmissionLogicModule import TransmissionLogicModule
from sciens.spectracs.logic.spectral.transmission.TransmissionLogicModuleParameters import TransmissionLogicModuleParameters
from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.plugin_sdk.util.EvaluationColorUtil import EvaluationColorUtil
from sciens.spectracs.plugin_sdk.ops.VerdictOp import VerdictOp

GAMMA = 2.2
REPORTS = os.path.join(
    os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")),
    "spectracs-references", "tmp")


def decode(values):
    # The shipped LUT semantics: f(v) = 255*(v/255)^gamma — scale-preserving, monotone.
    return {nm: 255.0 * (max(0.0, v) / 255.0) ** GAMMA for nm, v in values.items()}


def spectrum(values):
    s = Spectrum()
    s.valuesByNanometers = dict(values)
    return s


def transmission(reference, sample, floorFraction=None):
    parameters = TransmissionLogicModuleParameters()
    parameters.setReference(spectrum(reference))
    parameters.setSample(spectrum(sample))
    if floorFraction is not None:
        parameters.setReferenceFloorFraction(floorFraction)
    return TransmissionLogicModule().transmission(parameters).getSpectrum()


def load(path):
    reader = pypdf.PdfReader(path)
    if "workflow.json" not in reader.attachments:
        return None
    workflow = json.loads(reader.attachments["workflow.json"][0])
    reference = sample = None
    for phase in workflow["phases"]:
        for step in phase.get("steps", []):
            spectra = step.get("spectra") or {}
            if "REFERENCE" in spectra and reference is None:
                reference = {float(k): float(v) for k, v in spectra["REFERENCE"].items()}
            if "SAMPLE" in spectra and sample is None:
                sample = {float(k): float(v) for k, v in spectra["SAMPLE"].items()}
    if not reference or not sample:
        return None
    return reference, sample


def hueOf(spectrumObject):
    _rgb, hue = EvaluationColorUtil().spectrumToRgbAndHue(spectrumObject)
    return hue


def main():
    paths = sorted(glob.glob(os.path.join(REPORTS, "measurement_report_*.pdf")))
    rows = []
    for path in paths:
        loaded = load(path)
        if loaded is None:
            continue
        reference, sample = loaded

        asIs = transmission(reference, sample)
        # "naive" = the PRE-§17 floor constant (1% of peak) read in linear light — what the window would have
        # looked like had L3 been skipped. "fixed" = the shipped default. Pass both explicitly so this stays a
        # demonstration of the difference rather than a comparison of the default with itself.
        decoded = transmission(decode(reference), decode(sample), floorFraction=0.01)
        fixed = transmission(decode(reference), decode(sample))

        hueAsIs, hueDecoded = hueOf(asIs), hueOf(fixed)
        verdictAsIs = VerdictOp().verdict(hueAsIs)
        verdictDecoded = VerdictOp().verdict(hueDecoded)

        peak = max(reference.values())
        nms = sorted(reference)
        edgeLow = reference[nms[0]] / peak * 100.0
        edgeHigh = reference[nms[-1]] / peak * 100.0
        below = sum(1 for v in reference.values() if v < 0.123 * peak)     # would be cut by the linear floor

        rows.append(dict(name=os.path.basename(path)[19:-4],
                         hueAsIs=hueAsIs, hueDecoded=hueDecoded, delta=hueDecoded - hueAsIs,
                         verdictAsIs=verdictAsIs.value, verdictDecoded=verdictDecoded.value,
                         binsAsIs=len(asIs.valuesByNanometers),
                         binsDecodedNaive=len(decoded.valuesByNanometers),
                         binsDecodedFixed=len(fixed.valuesByNanometers),
                         edgeLow=edgeLow, edgeHigh=edgeHigh, wouldCut=below))

    print("%-16s %8s %8s %8s  %-14s %-14s  %6s %6s %6s  %6s %6s" % (
        "run", "hue", "hue(g)", "delta", "verdict", "verdict(g)",
        "bins", "naive", "fixed", "440%", "630%"))
    for row in rows:
        print("%-16s %8.2f %8.2f %+8.2f  %-14s %-14s  %6d %6d %6d  %6.1f %6.1f" % (
            row["name"], row["hueAsIs"], row["hueDecoded"], row["delta"],
            row["verdictAsIs"], row["verdictDecoded"],
            row["binsAsIs"], row["binsDecodedNaive"], row["binsDecodedFixed"],
            row["edgeLow"], row["edgeHigh"]))

    deltas = np.array([row["delta"] for row in rows])
    flips = [row["name"] for row in rows if row["verdictAsIs"] != row["verdictDecoded"]]
    narrowed = [row["name"] for row in rows if row["binsDecodedNaive"] < row["binsAsIs"]]
    print("\nruns=%d  hue delta: mean %+.2f deg, min %+.2f, max %+.2f, |max| %.2f"
          % (len(rows), deltas.mean(), deltas.min(), deltas.max(), np.abs(deltas).max()))
    print("VERDICT FLIPS (as-is -> decoded): %s" % (", ".join(flips) if flips else "NONE"))
    print("window NARROWED by the naive floor: %d of %d runs%s"
          % (len(narrowed), len(rows), (" -> " + ", ".join(narrowed[:8])) if narrowed else ""))
    print("window restored by floor=0.01^g: %s"
          % ("YES, all runs" if all(r["binsDecodedFixed"] == r["binsAsIs"] for r in rows) else "NO"))


if __name__ == "__main__":
    sys.exit(main())
