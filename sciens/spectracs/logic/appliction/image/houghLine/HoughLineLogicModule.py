import math
from typing import List
import cv2
import numpy as np
from PySide6.QtCore import QLine, QPoint
from PySide6.QtGui import QImage


from sciens.spectracs.logic.spectral.video.SpectralImageLogicModule import SpectralImageLogicModule


class HoughLineLogicModule:

    def auto_canny(self,image, sigma=0.33):
        # compute the median of the single channel pixel intensities

        # kernel = np.ones((5, 5), np.float32) / 25
        # image = cv2.filter2D(image, -1, kernel)


        threshold = 40
        assignValue = 255  # Value to assign the pixel if the threshold is met
        threshold_method = cv2.THRESH_BINARY
        _,image = cv2.threshold(image, threshold, assignValue, threshold_method)

        image = cv2.convertScaleAbs(image, 10, -10)
        image = cv2.bilateralFilter(image, 9, 75, 75)

        v = np.median(image)
        # apply automatic Canny edge detection using the computed median
        lower = int(max(0, (1.0 - sigma) * v))
        upper = int(min(255, (1.0 + sigma) * v))
        edged = cv2.Canny(image, lower, upper)
        # return the edged image
        return edged

    def getBoundingLines(self,img, lines)->List[QLine]:
        result=[]

        shape=img.shape
        width = shape[1]
        height = shape[0]

        lowestMidpoint=height
        highestMidpoint=0

        for line in lines:
            for x1, y1, x2, y2 in line:
                midpointX=x1+(x2-x1)/2.0

                angle = math.atan2(y2 - y1, x2 - x1) * 180.0 / math.pi

                if abs(angle)>1:
                    continue

                intersectMidpoint = self.get_intersect((midpointX, 0), (midpointX, height), (x1, y1), (x2, y2))
                intersectMidpointY=intersectMidpoint[1]

                if not intersectMidpointY==float('inf'):

                    if intersectMidpointY>highestMidpoint:
                        highestMidpoint=intersectMidpointY

                    if intersectMidpointY<lowestMidpoint:
                        lowestMidpoint=intersectMidpointY

                #debugPurpose: show Hough Lines
                # someLine = QLine()
                # someLine.setP1(QPoint(x1, y1))
                # someLine.setP2(QPoint(x2,y2))
                # result.append(someLine)
                # time.sleep(2)

        lowerLine = QLine()
        lowerLine.setP1(QPoint(0, lowestMidpoint))
        lowerLine.setP2(QPoint(width, lowestMidpoint))


        upperLine = QLine()
        upperLine.setP1(QPoint(0, highestMidpoint))
        upperLine.setP2(QPoint(width, highestMidpoint))

        result.append(upperLine)
        result.append(lowerLine)

        return result



    def getHoughLines(self,image:QImage)->List[QLine]:

        spectralImageLogicModule = SpectralImageLogicModule()
        src=spectralImageLogicModule.convertQImageToNumpyArray(image)
        src = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
        # Check if image is loaded fine

        #src = cv2.Canny(src, 50, 200, None, 3)


        src=self.auto_canny(src)

        #debugPurpose
        #cv2.imwrite('/tmp/autoCanny.jpg', src)

        # Copy edges to the images that will display the results in BGR

        lines = cv2.HoughLines(src, 1, np.pi / 180, 150, None, 0, 0)

        #lines = cv2.HoughLines(src, 1, np.pi / 180, 150, None, 0, 0)


        rho = 3
        theta = np.pi / 180
        threshold = 15
        #min_line_len = 300
        min_line_len = 20
        max_line_gap = 60
        lines = cv2.HoughLinesP(src, rho, theta, threshold, None, minLineLength=min_line_len,
                               maxLineGap=max_line_gap)

        src = spectralImageLogicModule.convertQImageToNumpyArray(image)

        # self.draw_lines(src,lines)
        # cv2.imwrite('test2.jpg', src)

        result=self.getBoundingLines(src,lines)


        return result

    def get_intersect(self,a1, a2, b1, b2):
        """
        Returns the point of intersection of the lines passing through a2,a1 and b2,b1.
        a1: [x, y] a point on the first line
        a2: [x, y] another point on the first line
        b1: [x, y] a point on the second line
        b2: [x, y] another point on the second line
        """
        s = np.vstack([a1, a2, b1, b2])  # s for stacked
        h = np.hstack((s, np.ones((4, 1))))  # h for homogeneous
        l1 = np.cross(h[0], h[1])  # get first line
        l2 = np.cross(h[2], h[3])  # get second line
        x, y, z = np.cross(l1, l2)  # point of intersection
        if z == 0:  # lines are parallel
            return (float('inf'), float('inf'))
        return (x / z, y / z)

    def draw_lines(self,img, lines, color=[255, 0, 0], thickness=2):

        shape=img.shape
        width = shape[1]
        height = shape[0]

        lowestMidpoint=height
        highestMidpoint=0

        for line in lines:
            for x1, y1, x2, y2 in line:
                midpointX=x1+(x2-x1)/2.0

                intersectLeftBorder = self.get_intersect((x1, y1), (x2, y2), (0, 0), (0, height))
                intersectRightBorder = self.get_intersect((x1, y1), (x2, y2), (width, 0), (width, height))

                intersectMidpoint = self.get_intersect((midpointX, 0), (midpointX, height), (x1, y1), (x2, y2))
                intersectMidpointY=intersectMidpoint[1]

                if intersectMidpointY>highestMidpoint:
                    highestMidpoint=intersectMidpointY

                if intersectMidpointY<lowestMidpoint:
                    lowestMidpoint=intersectMidpointY

        boundingLines = self.getBoundingLines(img, lines)

        point1=np.array([boundingLines[0].p1().x(), boundingLines[0].p1().y()], dtype=np.int32)
        point2 = np.array([boundingLines[0].p2().x(), boundingLines[0].p2().y()], dtype=np.int32)
        cv2.line(img,point1,point2, color, thickness)

        point1=np.array([boundingLines[1].p1().x(), boundingLines[1].p1().y()], dtype=np.int32)
        point2 = np.array([boundingLines[1].p2().x(), boundingLines[1].p2().y()], dtype=np.int32)
        cv2.line(img,point1,point2, color, thickness)




