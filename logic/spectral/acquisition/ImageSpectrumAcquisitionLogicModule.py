from PySide6.QtGui import qGray

from model.application.video.VideoSignal import VideoSignal
from model.signal.SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal import \
    SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal
from model.spectral.Spectrum import Spectrum


class ImageSpectrumAcquisitionLogicModule:

    def acquire(self,videoSignal:VideoSignal):

        image=videoSignal.image
        imageWidth=image.width()

        spectrum = Spectrum()

        if isinstance(videoSignal,SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal):

            y1 = videoSignal.model.regionOfInterestY1
            y2 = videoSignal.model.regionOfInterestY2

            y= int(y1 + (y2 - y1) / 2.0)

            valuesByNanometers={}

            for x in range(1,imageWidth):
                valuesByNanometers[x]=qGray(image.pixel(x,y))

            spectrum.setValuesByNanometers(valuesByNanometers)
        return spectrum

