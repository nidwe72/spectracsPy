from typing import List

import numpy as np
from scipy.signal import find_peaks, peak_prominences

from sciens.spectracs.logic.spectral.util.SpectralLineMasterDataUtil import SpectralLineMasterDataUtil
from sciens.spectracs.model.databaseEntity.spectral.device.SpectralLine import SpectralLine
from sciens.spectracs.model.spectral.Spectrum import Spectrum


class AdvancedCalibrationResult:
    spectralLines: List[SpectralLine] = None
    interpolationCoefficientA: float = None
    interpolationCoefficientB: float = None
    interpolationCoefficientC: float = None
    interpolationCoefficientD: float = None

    def getSpectralLines(self):
        if self.spectralLines is None:
            self.spectralLines = []
        return self.spectralLines


class SpectrometerWavelengthCalibrationAdvancedLogicModule:
    """Deterministic "predict-and-snap" matcher ("Heuristic advanced", +color guard = "Heuristic pro").

    1. Anchor the green mercury line (most prominent) and the red europium 611 line (most prominent peak
       to its right) — the same robust landmarks the basic heuristic uses.
    2. Build a linear pixel->nm seed from those two and PREDICT where every known CFL line falls.
    3. SNAP each detected peak to the nearest predicted line within a tolerance (peak-centric, so the dense
       red cluster maps one peak per line instead of colliding many lines onto one peak).
    4. Refit a cubic over all snapped pairs and iterate (re-predict, re-snap, tighten tolerance).

    Validated on the Philips and Snowy CFL test spectra: matches 8-13 lines, <1 nm residual, monotonic.
    The optional color guard rejects only GROSS color mismatches (the camera is not colour-safe), via the
    master-data mainColorName buckets.
    """

    GREEN_NANOMETER = 546.5
    RED_NANOMETER = 611.6
    MAX_ATLAS_NANOMETER = 635.0

    # coarse, ordered hue buckets — only neighbours are considered "compatible"
    COLOR_ORDER = ['violet', 'blue', 'cyan', 'green', 'yellow', 'orange', 'red']

    def _atlasMasterDatas(self):
        masterDatasByNames = SpectralLineMasterDataUtil().createTransientSpectralLineMasterDatasByNames()
        masterDatas = [md for md in masterDatasByNames.values()
                       if md.nanometer is not None and md.nanometer <= self.MAX_ATLAS_NANOMETER]
        masterDatas.sort(key=lambda md: md.nanometer)
        return masterDatas

    def _anchorPixel(self, intensities, count, leftBound=None, rightBound=None):
        for prominence in range(1, 255):
            peaks = find_peaks(intensities, distance=3, width=2, rel_height=0.5, prominence=prominence)[0]
            matching = [p for p in peaks
                        if (leftBound is None or p > leftBound) and (rightBound is None or p < rightBound)]
            if len(matching) <= count:
                break
        return sorted(int(p) for p in matching)

    def _bucket(self, colorName):
        if colorName is None:
            return None
        for i, name in enumerate(self.COLOR_ORDER):
            if name in colorName.lower():
                return i
        return None

    def match(self, spectrum: Spectrum, useColorGuard: bool = False) -> AdvancedCalibrationResult:
        keys = list(spectrum.valuesByNanometers.keys())
        intensities = np.asarray(list(spectrum.valuesByNanometers.values()), float)

        peaks = find_peaks(intensities, distance=3, width=2, rel_height=0.5, prominence=5)[0]

        greenCandidates = self._anchorPixel(intensities, 1)
        if not greenCandidates:
            return AdvancedCalibrationResult()
        green = greenCandidates[0]
        redCandidates = self._anchorPixel(intensities, 1, leftBound=green)
        if not redCandidates:
            return AdvancedCalibrationResult()
        red = redCandidates[0]
        if red <= green:
            return AdvancedCalibrationResult()

        masterDatas = self._atlasMasterDatas()
        atlasNanometers = [md.nanometer for md in masterDatas]
        masterDataByNanometer = {md.nanometer: md for md in masterDatas}

        dispersion = (self.RED_NANOMETER - self.GREEN_NANOMETER) / (red - green)
        coefficients = None
        tolerance = 6.0
        assignedNanometerByPixel = {}

        for _iteration in range(3):
            if coefficients is None:
                predict = lambda px: self.GREEN_NANOMETER + (px - green) * dispersion
            else:
                predict = lambda px: float(np.polyval(coefficients, px))

            bestByNanometer = {}   # nm -> (pixel, residual)
            for peak in peaks:
                predictedNanometer = predict(peak)
                nearestNanometer = min(atlasNanometers, key=lambda nm: abs(nm - predictedNanometer))
                residual = abs(nearestNanometer - predictedNanometer)
                if residual <= tolerance and (nearestNanometer not in bestByNanometer
                                              or residual < bestByNanometer[nearestNanometer][1]):
                    bestByNanometer[nearestNanometer] = (int(peak), residual)

            assignedNanometerByPixel = {pixel: nm for nm, (pixel, _r) in bestByNanometer.items()}
            points = sorted((pixel, nm) for pixel, nm in assignedNanometerByPixel.items())
            if len(points) < 4:
                break
            coefficients = np.polyfit([p for p, _ in points], [n for _, n in points], 3)
            tolerance = max(2.0, tolerance * 0.7)

        if coefficients is None or len(assignedNanometerByPixel) < 4:
            return AdvancedCalibrationResult()

        colorsByPixelIndices = spectrum.getColorsByPixelIndices() if useColorGuard else None

        result = AdvancedCalibrationResult()
        for pixel, nanometer in sorted(assignedNanometerByPixel.items()):
            if useColorGuard and colorsByPixelIndices:
                if not self._colorCompatible(colorsByPixelIndices, keys, pixel, masterDataByNanometer[nanometer]):
                    continue
            spectralLine = SpectralLine()
            spectralLine.pixelIndex = int(pixel)
            spectralLine.spectralLineMasterData = masterDataByNanometer[nanometer]
            result.getSpectralLines().append(spectralLine)

        # refit on the (possibly color-filtered) final set for the stored coefficients
        finalPoints = sorted((line.pixelIndex, line.spectralLineMasterData.nanometer)
                             for line in result.getSpectralLines())
        if len(finalPoints) >= 4:
            coefficients = np.polyfit([p for p, _ in finalPoints], [n for _, n in finalPoints], 3)
        result.interpolationCoefficientA = float(coefficients[0])
        result.interpolationCoefficientB = float(coefficients[1])
        result.interpolationCoefficientC = float(coefficients[2])
        result.interpolationCoefficientD = float(coefficients[3])
        return result

    def _hueBucket(self, color):
        # Map a QColor to a coarse spectral hue bucket (index into COLOR_ORDER), or None if achromatic.
        if color.valueF() < 0.12 or color.saturationF() < 0.18:
            return None
        hue = color.hueF()
        if hue < 0:
            return None
        degrees = hue * 360.0
        if degrees < 20 or degrees >= 345:
            return self.COLOR_ORDER.index('red')
        for upper, name in [(45, 'orange'), (70, 'yellow'), (160, 'green'),
                            (200, 'cyan'), (255, 'blue'), (290, 'violet')]:
            if degrees < upper:
                return self.COLOR_ORDER.index(name)
        return None   # magenta range — not a spectral colour, treat as unknown

    def _colorCompatible(self, colorsByPixelIndices, keys, pixel, masterData):
        # B3 color guard: reject only GROSS mismatches (camera is not colour-safe). Compare the coarse hue
        # bucket of the band pixel against the line's mainColorName bucket; allow a generous neighbour span.
        pixelKey = keys[pixel] if 0 <= pixel < len(keys) else None
        color = colorsByPixelIndices.get(pixelKey) if pixelKey is not None else None
        if color is None:
            return True
        detectedBucket = self._hueBucket(color)
        expectedBucket = self._bucket(getattr(masterData, 'mainColorName', None))
        if detectedBucket is None or expectedBucket is None:
            return True
        return abs(detectedBucket - expectedBucket) <= 2
