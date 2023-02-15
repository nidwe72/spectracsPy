from typing import Dict

from PySide6.QtGui import qGray, QColor

from logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModuleParameters import \
    ImageSpectrumAcquisitionLogicModuleParameters
from logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModuleResult import \
    ImageSpectrumAcquisitionLogicModuleResult
from model.application.video.VideoSignal import VideoSignal
from model.signal.SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal import \
    SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal
from model.spectral.Spectrum import Spectrum


class ImageSpectrumAcquisitionLogicModule:

    def execute(self,moduleParameters:ImageSpectrumAcquisitionLogicModuleParameters)->ImageSpectrumAcquisitionLogicModuleResult:

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

            for x in range(1,imageWidth):
                valuesByNanometers[x]=qGray(image.pixel(x,y))
                if moduleParameters.getAcquireColors():
                    colorsByPixelIndices[x]=image.pixelColor(x,y)

            spectrum.setValuesByNanometers(valuesByNanometers)
            spectrum.addToCapturedValuesByNanometers(valuesByNanometers)

        if moduleParameters.getAcquireColors():
            spectrum.setColorsByPixelIndices(colorsByPixelIndices)

        return result

