from typing import Dict

from PySide6.QtGui import qGray, QColor
from numpy import poly1d

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
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
                valuesByNanometers[pixelIndex]=qGray(image.pixel(pixelIndex,y))
                if moduleParameters.getAcquireColors():
                    colorsByPixelIndices[pixelIndex]=image.pixelColor(pixelIndex,y)

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
            y= int(y1 + (y2 - y1) / 2.0)

            x1= calibrationProfile.regionOfInterestX1
            x2= calibrationProfile.regionOfInterestX2

            # print(f"x1:{x1};x2:{x2}")

            # Drift tripwire (SPEC_capture_quality.md §4.9): the calibration ROI must fit inside the captured frame.
            # If capture resolution ever drifts below the calibration resolution (firmware/USB/cv2 change), the px->nm
            # cubic mis-maps and eval bands fall off-frame — the exact silent regression the probe found. Warn once
            # per unique mismatch and clamp the reads so we never sample outside the frame (undefined QImage.pixel).
            imageHeight = image.height()
            if x2 > imageWidth or y2 > imageHeight or y >= imageHeight:
                key = (imageWidth, imageHeight, int(x2), int(y2))
                if key not in ImageSpectrumAcquisitionLogicModule._warnedRoiMismatch:
                    ImageSpectrumAcquisitionLogicModule._warnedRoiMismatch.add(key)
                    print("WARNING ImageSpectrumAcquisitionLogicModule: calibration ROI (x2=%d,y2=%d) exceeds the "
                          "captured frame (%dx%d) — capture resolution likely does not match the calibration "
                          "(SPEC_capture_quality.md §4.9); spectrum will be clipped/mis-mapped." % (x2, y2, imageWidth, imageHeight))
            y = min(y, imageHeight - 1)
            x2 = min(x2, imageWidth)

            valuesByNanometers={}
            for pixelIndex in range(x1,x2):
                nanometer=polynomial(pixelIndex)
                gray = qGray(image.pixel(pixelIndex, y))
                # print(f"gray:{gray}")
                valuesByNanometers[nanometer]= gray
                # if moduleParameters.getAcquireColors():
                #     colorsByPixelIndices[pixelIndex]=image.pixelColor(pixelIndex,y)

            spectrum.setValuesByNanometers(valuesByNanometers)
            spectrum.addToCapturedValuesByNanometers(valuesByNanometers)

            # print(f"valuesByNanometers:{valuesByNanometers}")

            pass

        if moduleParameters.getAcquireColors():
            spectrum.setColorsByPixelIndices(colorsByPixelIndices)

        return result

