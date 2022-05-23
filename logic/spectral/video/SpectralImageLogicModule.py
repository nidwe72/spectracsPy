import numpy.typing
from PyQt6.QtGui import QImage
from PyQt6.QtGui import qGray
from PyQt6.QtGui import QColor
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

    def convertQImageToNumpyArray(self,qtimg):

        """
        Read an image using QT's QImage.load
        """
        arrayptr = qtimg.bits()
        # QT may pad the image, so we need to use bytesPerLine, not width for
        # the conversion to a numpy array
        bytesPerPixel = qtimg.depth() // 8
        pixelsPerLine = qtimg.bytesPerLine() // bytesPerPixel
        img_size = pixelsPerLine * qtimg.height() * bytesPerPixel
        arrayptr.setsize(img_size)
        img = np.array(arrayptr)
        # Reshape and trim down to correct dimensions
        if bytesPerPixel > 1:
            img = img.reshape((qtimg.height(), pixelsPerLine, bytesPerPixel))
            img = img[:, :qtimg.width(), :]
        else:
            img = img.reshape((qtimg.height(), pixelsPerLine))
            img = img[:, :qtimg.width()]
        # Strip qt's false alpha channel if needed
        # and reorder color axes as required
        if bytesPerPixel == 4 and not qtimg.hasAlphaChannel():
            img = img[:, :, 2::-1]
        elif bytesPerPixel == 4:
            img[:, :, 0:3] = img[:, :, 2::-1]
        return img

    def convertNumpyArrayToQImage(self,img:numpy.ndarray):
        w,h,ch = img.shape
        # Convert resulting image to pixmap
        result = QImage(img.data, h, w, 3*h, QImage.Format.Format_RGB888)
        return result