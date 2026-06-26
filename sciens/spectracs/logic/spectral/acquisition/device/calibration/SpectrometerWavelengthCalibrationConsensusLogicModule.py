from typing import List

import numpy as np
from scipy.signal import find_peaks

from sciens.spectracs.logic.spectral.acquisition.device.calibration.SpectrometerWavelengthCalibrationAdvancedLogicModule import \
    SpectrometerWavelengthCalibrationAdvancedLogicModule
from sciens.spectracs.logic.spectral.acquisition.device.calibration.SpectrometerWavelengthCalibrationLogicModule import \
    SpectrometerWavelengthCalibrationLogicModule
from sciens.spectracs.logic.spectral.acquisition.device.calibration.SpectrometerWavelengthCalibrationLogicModuleParameters import \
    SpectrometerWavelengthCalibrationLogicModuleParameters


class ConsensusCalibrationResult:
    spectralLines: List = None
    uncertainLines: List = None   # list of (nanometer, [reasons])

    def getSpectralLines(self):
        if self.spectralLines is None:
            self.spectralLines = []
        return self.spectralLines

    def getUncertainLines(self):
        if self.uncertainLines is None:
            self.uncertainLines = []
        return self.uncertainLines


class SpectrometerWavelengthCalibrationConsensusLogicModule:
    """Runs the heuristic family and cross-checks the FIVE anchor lines to assess confidence.

    The deliverable is exactly the five lines the simple heuristic detects (405/436/487/546/611) — these
    drive the calibration curve. Confidence in each is raised by independent second opinions:
      * agreement: does the advanced (predict-and-snap) cubic agree that the simple-detected pixel maps to
        that wavelength? (genuinely independent for violet/blue/aqua; for green/red it largely agrees by
        construction because both share the prominence anchors).
      * color: is the band pixel at that line actually the expected colour? (independent evidence for all
        five — coarse only, the camera isn't colour-safe). This is the second opinion for red.
      * doublet (green only): mercury green is a known ~4 nm pair (542 + 546); confirm two close peaks are
        present — the green fingerprint, independent of brightness.

    A line is "confident" only if no check objects. Uncertain lines are reported so the user can re-check.
    """

    GREEN_NANOMETER = 546.5
    RED_NANOMETER = 611.6
    DOUBLET_SPACING_NANOMETER = 4.1   # 546.5 - 542.4
    AGREEMENT_TOLERANCE_NANOMETER = 5.0

    def match(self, videoSignal) -> ConsensusCalibrationResult:
        spectrum = videoSignal.spectrum

        # 1) simple heuristic -> the five anchor lines (the deliverable)
        simple = SpectrometerWavelengthCalibrationLogicModule()
        parameters = SpectrometerWavelengthCalibrationLogicModuleParameters()
        parameters.videoSignal = videoSignal
        simple.moduleParameters = parameters
        simple.execute()
        simpleLines = list(simple.getModuleResult().getSpectralLines())

        # 2) advanced (predict-and-snap) -> an independent global cubic for the agreement check
        advanced = SpectrometerWavelengthCalibrationAdvancedLogicModule()
        advancedResult = advanced.match(spectrum)
        advancedCubic = None
        if advancedResult.interpolationCoefficientA is not None:
            advancedCubic = [advancedResult.interpolationCoefficientA, advancedResult.interpolationCoefficientB,
                             advancedResult.interpolationCoefficientC, advancedResult.interpolationCoefficientD]

        intensities = np.asarray(list(spectrum.valuesByNanometers.values()), float)
        peaks = find_peaks(intensities, distance=3, width=2, rel_height=0.5, prominence=5)[0]
        keys = list(spectrum.valuesByNanometers.keys())
        colorsByPixelIndices = spectrum.getColorsByPixelIndices()

        simpleByNanometer = {round(line.spectralLineMasterData.nanometer, 1): line for line in simpleLines}
        greenLine = simpleByNanometer.get(round(self.GREEN_NANOMETER, 1))
        redLine = simpleByNanometer.get(round(self.RED_NANOMETER, 1))
        dispersion = None
        if greenLine is not None and redLine is not None and redLine.pixelIndex > greenLine.pixelIndex:
            dispersion = (self.RED_NANOMETER - self.GREEN_NANOMETER) / (redLine.pixelIndex - greenLine.pixelIndex)

        result = ConsensusCalibrationResult()
        for line in sorted(simpleLines, key=lambda l: l.pixelIndex):
            nanometer = line.spectralLineMasterData.nanometer
            pixel = line.pixelIndex
            reasons = []

            # agreement: advanced cubic should report ~the same wavelength at the simple-detected pixel
            if advancedCubic is not None:
                predictedNanometer = float(np.polyval(advancedCubic, pixel))
                if abs(predictedNanometer - nanometer) > self.AGREEMENT_TOLERANCE_NANOMETER:
                    reasons.append("methods disagree (advanced says %.0f nm)" % predictedNanometer)

            # color: independent second opinion (gross-only)
            if colorsByPixelIndices and not advanced._colorCompatible(
                    colorsByPixelIndices, keys, pixel, line.spectralLineMasterData):
                reasons.append("colour mismatch")

            # doublet: green fingerprint
            if round(nanometer, 1) == round(self.GREEN_NANOMETER, 1) and dispersion:
                if not self._hasDoublet(peaks, pixel, dispersion):
                    reasons.append("green doublet not found")

            if reasons:
                result.getUncertainLines().append((nanometer, reasons))
            result.getSpectralLines().append(line)

        return result

    def _hasDoublet(self, peaks, greenPixel, dispersion):
        doubletPixels = self.DOUBLET_SPACING_NANOMETER / abs(dispersion)
        low = greenPixel - 2.5 * doubletPixels
        high = greenPixel + 1.0 * doubletPixels
        return sum(1 for p in peaks if low <= p <= high) >= 2
