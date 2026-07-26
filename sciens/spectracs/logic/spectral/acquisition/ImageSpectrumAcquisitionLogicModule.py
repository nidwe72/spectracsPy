from typing import Dict

import numpy as np
from PySide6.QtGui import QColor, QImage
from numpy import poly1d

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil
from sciens.spectracs.logic.spectral.acquisition.RobustReductionLogicModule import RobustReductionLogicModule
from sciens.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModuleParameters import \
    ImageSpectrumAcquisitionLogicModuleParameters
from sciens.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModuleResult import \
    ImageSpectrumAcquisitionLogicModuleResult
from sciens.spectracs.model.signal.SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal import \
    SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal
from sciens.spectracs.model.spectral.SpectralVideoThreadSignal import SpectralVideoThreadSignal
from sciens.spectracs.model.spectral.Spectrum import Spectrum


class ImageSpectrumAcquisitionLogicModule:

    # Drift tripwire (SPEC_capture_quality.md §4.9): remember which (frame,ROI) mismatches we've already warned about,
    # so a resolution/calibration mismatch warns ONCE per unique shape instead of 150x per burst.
    _warnedRoiMismatch = set()

    # SPEC §6 (M2): fraction of the ROI band height dropped at the TOP and BOTTOM before the per-column reduction.
    # The edge rows bleed the dark border outside the slit and carry the worst smile-λ error. Tunable; finalize
    # on the rig (M2.4). The measurement is broadband, so a generous central band helps and smile barely matters.
    __INSET_FRACTION = 0.2

    def execute(self,moduleParameters:ImageSpectrumAcquisitionLogicModuleParameters)->ImageSpectrumAcquisitionLogicModuleResult:

        # print('ImageSpectrumAcquisitionLogicModule.execute()')

        result=ImageSpectrumAcquisitionLogicModuleResult()

        videoSignal = moduleParameters.getVideoSignal()
        image= videoSignal.image
        imageWidth=image.width()

        spectrum = moduleParameters.spectrum
        if spectrum is None:
            spectrum=Spectrum()

        result.spectrum=spectrum

        colorsByPixelIndices: Dict[int, QColor]={}

        if isinstance(videoSignal,SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal):

            y1 = videoSignal.model.regionOfInterestY1
            y2 = videoSignal.model.regionOfInterestY2

            y= int(y1 + (y2 - y1) / 2.0)

            valuesByNanometers={}

            for pixelIndex in range(1,imageWidth):
                pixelColor = image.pixelColor(pixelIndex, y)
                # SPEC_capture_quality.md §15: max-channel (radiometric) reduction, was qGray (blue-suppressing).
                # DELIBERATELY NOT gamma-decoded (§17.6/4) — this branch feeds wavelength LINE DETECTION, which
                # needs peak POSITIONS (invariant under any monotone map) and raw hues, but selects by
                # prominence RANK. Decoding compresses dim peaks relative to bright ones, so the blue Hg 436
                # line §15 just rescued would lose prominence against `prominence = 0.01*peak` — real risk, zero
                # benefit. This branch stays in DN; only the measurement branch below linearizes.
                valuesByNanometers[pixelIndex]=SpectralColorUtil().toGrayMaximum(pixelColor)
                if moduleParameters.getAcquireColors():
                    colorsByPixelIndices[pixelIndex]=pixelColor

            spectrum.setValuesByNanometers(valuesByNanometers)
            spectrum.addToCapturedValuesByNanometers(valuesByNanometers)

        elif isinstance(videoSignal,SpectralVideoThreadSignal):

            spectrometerProfile = ApplicationContextLogicModule().getApplicationSettings().getSpectrometerProfile()

            calibrationProfile = spectrometerProfile.spectrometerCalibrationProfile
            polynomial = poly1d(
                [calibrationProfile.interpolationCoefficientA,
                 calibrationProfile.interpolationCoefficientB,
                 calibrationProfile.interpolationCoefficientC,
                 calibrationProfile.interpolationCoefficientD])

            y1= calibrationProfile.regionOfInterestY1
            y2= calibrationProfile.regionOfInterestY2

            x1= calibrationProfile.regionOfInterestX1
            x2= calibrationProfile.regionOfInterestX2

            # Drift tripwire (SPEC_capture_quality.md §4.9): the calibration ROI must fit inside the captured frame.
            # If capture resolution ever drifts below the calibration resolution (firmware/USB/cv2 change), the px->nm
            # cubic mis-maps and eval bands fall off-frame — the exact silent regression the probe found. Warn once
            # per unique mismatch and clamp the reads so we never sample outside the frame.
            imageHeight = image.height()
            if x2 > imageWidth or y2 > imageHeight:
                key = (imageWidth, imageHeight, int(x2), int(y2))
                if key not in ImageSpectrumAcquisitionLogicModule._warnedRoiMismatch:
                    ImageSpectrumAcquisitionLogicModule._warnedRoiMismatch.add(key)
                    print("WARNING ImageSpectrumAcquisitionLogicModule: calibration ROI (x2=%d,y2=%d) exceeds the "
                          "captured frame (%dx%d) — capture resolution likely does not match the calibration "
                          "(SPEC_capture_quality.md §4.9); spectrum will be clipped/mis-mapped." % (x2, y2, imageWidth, imageHeight))
            x2 = min(x2, imageWidth)
            y2 = min(y2, imageHeight)

            # M2 spatial reduction (SPEC §6): a robust per-column estimate over an INSET band of rows, replacing the
            # single-centre-row read — so a hot/dead pixel or a smile-blurred edge row can't skew the spectrum.
            reduced = self.__reducedLinearColumnValues(image, x1, x2, y1, y2)
            valuesByNanometers={}      # LINEAR light on a 0..255 scale (gamma-decoded, §17) — NOT camera DN
            for offset, pixelIndex in enumerate(range(x1, x2)):
                valuesByNanometers[polynomial(pixelIndex)] = float(reduced[offset])

            spectrum.setValuesByNanometers(valuesByNanometers)
            spectrum.addToCapturedValuesByNanometers(valuesByNanometers)

        if moduleParameters.getAcquireColors():
            spectrum.setColorsByPixelIndices(colorsByPixelIndices)

        return result

    def __reducedLinearColumnValues(self, image, x1, x2, y1, y2):
        """One robust max-channel value per column x1..x2, in LINEAR light, reduced over an INSET band of rows
        (SPEC §6, §15, §17). Saturated (any channel==255) and dead (all channels==0) pixels are masked to NaN
        BEFORE the reduction — saturation is a per-channel fact — then Tukey-biweight per column. An all-masked
        column falls back to its plain median (so a fully-clipped column still reports a value). §15: the
        reduction is max-channel (radiometric), not qGray (photometric, blue-suppressing); the mask was already
        max-channel, so the two are consistent.

        §17: pixels are GAMMA-DECODED first, per channel, before anything combines them. `max` and `median` are
        order statistics and commute with the decode exactly, but the two AVERAGES here (Tukey across rows, and
        the sigma-clipped mean across frames downstream) do not — so decode-first is mandatory by concept, and
        free. The decode is scale-preserving (0->0, 255->255), which is what lets the mask below keep its exact
        meaning. The returned values are LINEAR on a 0..255 scale — the name says so on purpose, because
        `Spectrum` carries no unit and the calibration branch above is still in DN (§17.7/19)."""
        inset = int(round((y2 - y1) * self.__INSET_FRACTION))
        yLo = max(0, int(y1) + inset)
        yHi = max(yLo + 1, min(int(y2) - inset, image.height()))

        img = image.convertToFormat(QImage.Format.Format_RGB888)
        width = img.width()
        frame = np.frombuffer(img.constBits(), np.uint8).reshape(img.height(), img.bytesPerLine())
        # LUT decode on the uint8 ROI slice — this REPLACES the old .astype(np.float32) (the LUT is float32),
        # and it sits AFTER the slice so we decode ~0.7 Mpx, not the whole 5 Mpx frame (§17.7/14).
        frame = SpectralColorUtil().decodeGammaArray(
            frame[:, :width * 3].reshape(img.height(), width, 3)[yLo:yHi, int(x1):int(x2), :])

        r, g, b = frame[:, :, 0], frame[:, :, 1], frame[:, :, 2]
        gray = SpectralColorUtil().toGrayMaximumArray(r, g, b)  # §15: max-channel reduction (== the saturation mask)
        valid = (gray < 255.0) & (gray > 0.0)

        reduced = RobustReductionLogicModule().tukeyBiweightPerColumn(np.where(valid, gray, np.nan))
        fallback = np.median(gray, axis=0)                     # all-clipped/dead column -> plain median (keeps 255/0)
        return np.where(np.isnan(reduced), fallback, reduced)

