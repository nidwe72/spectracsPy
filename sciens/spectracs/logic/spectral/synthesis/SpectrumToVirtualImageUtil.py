import math

import numpy
from PySide6.QtGui import QImage

from sciens.base.Singleton import Singleton
from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil


class SpectrumToVirtualImageUtil(Singleton):
    # Faithful SPD -> full-resolution grayscale ROI-strip encoder: the inverse of
    # ImageSpectrumAcquisitionLogicModule's read-back. For each ROI column x it maps x -> nm via the SAME
    # calibration cubic the reader uses, linearly resamples the SPD onto that nm, and writes an 8-bit gray
    # that the reader decodes back to `value / vmax`. REFERENCE and SAMPLE share ONE vmax (they model a
    # -- SPEC_capture_quality.md §15 INVARIANT: this writes NEUTRAL gray (Format_Grayscale8, R=G=B=v), so
    #    max(v,v,v) == qGray(v,v,v) == v. The virtual round-trip is therefore IDENTICAL under either reduction;
    #    switching the reader qGray->max needed NO change here. --
    # -- SPEC_capture_quality.md §17: it is NO LONGER a no-op, though. The reader gamma-DECODES, so this
    #    encoder must gamma-ENCODE: gray = 255*(value/vmax)^(1/gamma). The two are inverse halves of ONE
    #    transform and must always ship together (§17.7/21) — with only one half in place every virtual
    #    capture comes back as value^gamma (or value^(1/gamma)), silently, and the DEV bench, the plugin
    #    round-trip and the doc screencasts all run on this path. Bonus: the virtual device now models what a
    #    real camera actually does, and gamma encoding gives the DARK end more code levels. --
    # single camera + light source shooting both), so T = SAMPLE/REFERENCE and the absorption plot stay on
    # a true scale. (SPEC_pumpkin_integration.md A.2 / D6 / D11 / D12)

    def encode(self, spectrumReference, spectrumSample, calibrationProfile, imageWidth, imageHeight):
        # Returns (imageReference, imageSample) — both must be produced together so they share a vmax.
        polynomial = numpy.poly1d([calibrationProfile.interpolationCoefficientA,
                                   calibrationProfile.interpolationCoefficientB,
                                   calibrationProfile.interpolationCoefficientC,
                                   calibrationProfile.interpolationCoefficientD])
        x1 = int(calibrationProfile.regionOfInterestX1)
        x2 = int(calibrationProfile.regionOfInterestX2)
        y1 = int(calibrationProfile.regionOfInterestY1)
        y2 = int(calibrationProfile.regionOfInterestY2)
        yLow, yHigh = min(y1, y2), max(y1, y2)  # ROI is stored inverted (Y1 > Y2) — paint the real band

        vmax = max(self.__peak(spectrumReference), self.__peak(spectrumSample))
        if vmax <= 0.0:
            vmax = 1.0

        imageReference = self.__encodeOne(spectrumReference, polynomial, x1, x2, yLow, yHigh,
                                          imageWidth, imageHeight, vmax)
        imageSample = self.__encodeOne(spectrumSample, polynomial, x1, x2, yLow, yHigh,
                                       imageWidth, imageHeight, vmax)
        return imageReference, imageSample

    def __encodeOne(self, spectrum, polynomial, x1, x2, yLow, yHigh, width, height, vmax):
        array = numpy.zeros((height, width), dtype=numpy.uint8)  # black outside the ROI band
        values = spectrum.valuesByNanometers
        for x in range(max(0, x1), min(width, x2)):
            nanometer = float(polynomial(x))
            value = self.__interpolate(values, nanometer)
            gray = int(round(SpectralColorUtil().encodeGammaFraction(max(0.0, value) / vmax)))
            array[yLow:yHigh, x] = min(255, max(0, gray))
        buffer = array.tobytes()
        return QImage(buffer, width, height, width, QImage.Format_Grayscale8).copy()

    def __peak(self, spectrum):
        values = spectrum.valuesByNanometers
        return max(values.values()) if values else 0.0

    def __interpolate(self, values, nanometer):
        # Linear interpolation over the integer-nm synth grid; 0 outside the sampled range.
        low = math.floor(nanometer)
        high = math.ceil(nanometer)
        if low in values and high in values:
            if high == low:
                return values[low]
            fraction = nanometer - low
            return values[low] * (1.0 - fraction) + values[high] * fraction
        return values.get(int(round(nanometer)), 0.0)
