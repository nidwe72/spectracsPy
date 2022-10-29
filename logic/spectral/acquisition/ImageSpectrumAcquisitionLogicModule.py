from PySide6.QtGui import QImage
from PySide6.QtGui import qGray

from model.spectral.Spectrum import Spectrum

class ImageSpectrumAcquisitionLogicModule:

    def acquire(self,image:QImage):
        y=392
        imageWidth=image.width()

        spectrum=Spectrum()
        valuesByNanometers={}

        for x in range(1,imageWidth):
            valuesByNanometers[x]=qGray(image.pixel(x,y))

        spectrum.setValuesByNanometers(valuesByNanometers)
        return spectrum

