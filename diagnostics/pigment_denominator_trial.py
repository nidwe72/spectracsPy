"""Would a BRIGHTER denominator band give a sturdier pigment ratio? (SPEC_capture_quality.md §16.8 option (b).)

The Q band 560-580 sits in the sensor's green->red filter crossover: fewest photons, the point where max(R,G,B)
switches channel, and the most drift-prone band measured (§16.8). This replays the 32-run Capability-Proof set
through the app's OWN pipeline (AbsorptionOp -> MedianFilterOp(7) -> SpectrumFeatureUtil.bandMean, exactly as
DevSpectralPlugin.__pigmentRatio) and scores each candidate denominator by class separation:

    Cohen's d = (mean_green - mean_brown) / pooled SD          published for 440-460 / 560-580: 10.39

    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python diagnostics/pigment_denominator_trial.py
"""
import json
import os
import sys

import numpy as np
import pypdf

from sciens.spectracs.model.spectral.SpectraContainer import SpectraContainer
from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.plugin_sdk.ops.AbsorptionOp import AbsorptionOp
from sciens.spectracs.plugin_sdk.ops.MedianFilterOp import MedianFilterOp
from sciens.spectracs.plugin_sdk.roles import ABSORPTION, REFERENCE, SAMPLE
from sciens.spectracs.plugin_sdk.util.SpectrumFeatureUtil import SpectrumFeatureUtil

REPORTS = os.path.join(
    os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")),
    "spectracs-references", "tmp")

GREEN_OILS = ["oilK", "oilL", "oilO", "oilP"]        # SPEC_capability_proof.md — the good/green class
BROWN_OILS = ["oilM", "oilN", "oilQ", "oilR"]        # the over-roasted/brown class
SORET = (440.0, 460.0)
CANDIDATES = [("Q 560-580 (current)", 560.0, 580.0),
              ("clarity 500-540", 500.0, 540.0),
              ("green peak 520-545", 520.0, 545.0),
              ("wide green 500-560", 500.0, 560.0),
              ("red 590-620", 590.0, 620.0),
              ("Q widened 555-590", 555.0, 590.0)]


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


def despikedAbsorption(reference, sample):
    # Exactly DevSpectralPlugin's chain: AbsorptionOp then MedianFilterOp(7).
    container = SpectraContainer()
    for role, values in ((REFERENCE, reference), (SAMPLE, sample)):
        spectrum = Spectrum()
        spectrum.valuesByNanometers = dict(values)
        container.addToSpectra(spectrum, role)
    absorption = AbsorptionOp().apply(container)
    return MedianFilterOp(7).apply(absorption).getSpectra()[ABSORPTION]


def cohensD(green, brown):
    green, brown = np.array(green), np.array(brown)
    pooled = np.sqrt(((len(green) - 1) * green.var(ddof=1) + (len(brown) - 1) * brown.var(ddof=1))
                     / (len(green) + len(brown) - 2))
    return abs(green.mean() - brown.mean()) / pooled


def main():
    util = SpectrumFeatureUtil()
    runs = {}
    for oil in GREEN_OILS + BROWN_OILS:
        for index in range(1, 6):
            path = os.path.join(REPORTS, "measurement_report_%s_%03d.pdf" % (oil, index))
            if not os.path.exists(path):
                continue
            loaded = load(path)
            if loaded is None:
                continue
            runs.setdefault(oil, []).append(despikedAbsorption(*loaded))

    total = sum(len(v) for v in runs.values())
    print("loaded %d runs: %s\n" % (total, ", ".join("%s=%d" % (k, len(v)) for k, v in sorted(runs.items()))))

    print("%-22s %-16s %-16s %8s %8s %8s" % ("denominator band", "green (mean±SD)", "brown (mean±SD)",
                                             "gap", "d", "vs 10.39"))
    baseline = None
    for label, low, high in CANDIDATES:
        green, brown = [], []
        for oil, spectra in runs.items():
            target = green if oil in GREEN_OILS else brown
            for spectrum in spectra:
                soret = util.bandMean(spectrum, *SORET)
                denominator = util.bandMean(spectrum, low, high)
                if soret is None or denominator in (None, 0):
                    continue
                target.append(soret / denominator)
        if not green or not brown:
            continue
        d = cohensD(green, brown)
        baseline = baseline if baseline is not None else d
        print("%-22s %6.3f ± %-7.3f %6.3f ± %-7.3f %8.3f %8.2f %8s"
              % (label, np.mean(green), np.std(green, ddof=1), np.mean(brown), np.std(brown, ddof=1),
                 abs(np.mean(green) - np.mean(brown)), d,
                 "%+.0f%%" % ((d / baseline - 1) * 100) if baseline else ""))

    print("\n(relative SD — how reproducible each ratio is within its own class)")
    print("%-22s %10s %10s" % ("denominator band", "green CV", "brown CV"))
    for label, low, high in CANDIDATES:
        green, brown = [], []
        for oil, spectra in runs.items():
            target = green if oil in GREEN_OILS else brown
            for spectrum in spectra:
                soret = util.bandMean(spectrum, *SORET)
                denominator = util.bandMean(spectrum, low, high)
                if soret is None or denominator in (None, 0):
                    continue
                target.append(soret / denominator)
        print("%-22s %9.1f%% %9.1f%%" % (label,
                                         np.std(green, ddof=1) / np.mean(green) * 100,
                                         np.std(brown, ddof=1) / np.mean(brown) * 100))
    return 0


if __name__ == "__main__":
    sys.exit(main())
