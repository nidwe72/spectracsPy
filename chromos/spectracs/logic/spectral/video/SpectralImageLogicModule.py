import numpy.typing
from PySide6 import QtGui
from PySide6.QtGui import QImage
from PySide6.QtGui import qGray
from PySide6.QtGui import QColor
import numpy as np
import cv2
from skimage import color

class SpectralImageLogicModule:

    def calculateFocalMeasureOfNumpyImage(self,img:numpy.ndarray):
        """Return measure how sharp the image is, the higher the return the sharper"""
        """Put otherwise: a blur detection functionality"""
        # convert RGB image to Gray scale image
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Measure focal measure score (laplacian approach)
        fm = cv2.Laplacian(gray, cv2.CV_64F).var()
        return fm

    def colorizeNumpyArray(self,image:numpy.ndarray, hue):
        """Return image tinted by the given hue based on a grayscale image."""

        image=np.copy(image)
        height=image.shape[0]
        width = image.shape[1]

        newPixelColor = QColor()
        for x in range(0,width):
            for y in range(0, height):
                pixel=image[y,x]
                gray = qGray(pixel[0],pixel[1],pixel[2])
                newPixelColor.setHsv(hue,255,gray)
                image[y,x]=np.array([newPixelColor.red(),newPixelColor.green(),newPixelColor.blue()])
        return image

    def colorizeQImage(self,image:QImage, hue):
        width = image.width()
        height = image.height()

        result=QImage(width, height, image.format())

        # npArray=self.convertQImageToNumpyArray(image)
        # npArray2=self.colorizeNumpyArray(npArray,hue)

        for x in range(0,width):
            for y in range(0,height):
                pixelColor=image.pixelColor(x,y)
                gray=qGray(pixelColor.red(),pixelColor.green(),pixelColor.blue())
                newPixelColor=QColor()
                newPixelColor.setHsv(hue,255,gray)
                result.setPixelColor(x,y,newPixelColor)

        # result2=self.convertNumpyArrayToQImage(npArray2)
        # return result2

        return result

    def convertQImageToNumpyArray(self,incomingImage:QImage):
        '''  Converts a QImage into an opencv MAT format  '''

        incomingImage = incomingImage.convertToFormat(QtGui.QImage.Format.Format_RGB32)

        width = incomingImage.width()
        height = incomingImage.height()

        ptr = incomingImage.constBits()
        arr = np.array(ptr).reshape(height, width, 4)  # Copies the data
        return arr

    def convertNumpyArrayToQImage(self,img:numpy.ndarray):
        w,h,ch = img.shape
        # Convert resulting image to pixmap
        result = QImage(img.data, h, w, 3*h, QImage.Format.Format_RGB888)
        return result