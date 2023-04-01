from typing import Dict

from PySide6.QtGui import qGray, QColor
from numpy import poly1d

from chromos.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from chromos.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModuleParameters import \
    ImageSpectrumAcquisitionLogicModuleParameters
from chromos.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModuleResult import \
    ImageSpectrumAcquisitionLogicModuleResult
from chromos.spectracs.model.signal.SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal import \
    SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal
from chromos.spectracs.model.spectral.SpectralVideoThreadSignal import SpectralVideoThreadSignal
from chromos.spectracs.model.spectral.Spectrum import Spectrum


class ImageSpectrumAcquisitionLogicModule:

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

