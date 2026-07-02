from PySide6.QtCore import Qt, QPointF, QRectF, QSize
from PySide6.QtGui import QPainter, QPolygonF, QColor
from PySide6.QtWidgets import QWidget

from sciens.spectracs.logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule


class StepBarWidget(QWidget):
    # A generic horizontal step indicator: right-pointing chevron segments, ALL steps visible at once, the
    # current step filled in the app PRIMARY colour and the rest in a SECONDARY/gray background. Knows
    # nothing about workflows — just setSteps([labels]) + setCurrentIndex(i). Reusable anywhere.

    __ARROW_DEPTH = 12
    __HEIGHT = 34
    __ACTIVE_TEXT = QColor("#FFFFFF")
    __INACTIVE_TEXT = QColor("#FFFFFF")  # inactive phases: white-on-(secondary) gray

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__steps = []
        self.__currentIndex = 0
        self.setFixedHeight(self.__HEIGHT)

    def setSteps(self, steps):
        self.__steps = list(steps)
        self.update()

    def setCurrentIndex(self, index):
        self.__currentIndex = index
        self.update()

    def getSteps(self):
        return self.__steps

    def getCurrentIndex(self):
        return self.__currentIndex

    def sizeHint(self):
        return QSize(max(1, len(self.__steps)) * 150, self.__HEIGHT)

    def __primaryColor(self):
        color = ApplicationStyleLogicModule().getPrimaryColor()
        return color if isinstance(color, QColor) else QColor(color)

    def __inactiveColor(self):
        # Match the inactive QTabBar tab (the app secondary gray, #404040) so the bar reads as one surface.
        color = ApplicationStyleLogicModule().getSecondaryColor()
        return color if isinstance(color, QColor) else QColor(color)

    def paintEvent(self, event):
        if not self.__steps:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width = self.width()
        height = self.height()
        count = len(self.__steps)
        depth = self.__ARROW_DEPTH
        segmentWidth = (width + (count - 1) * depth) / count
        activeColor = self.__primaryColor()
        inactiveColor = self.__inactiveColor()

        for index, label in enumerate(self.__steps):
            isLast = index == count - 1
            x0 = index * (segmentWidth - depth)
            x1 = x0 + segmentWidth
            polygon = QPolygonF()
            polygon.append(QPointF(x0, 0))
            if isLast:
                polygon.append(QPointF(x1, 0))        # flat right edge (no arrow on the final step)
                polygon.append(QPointF(x1, height))
            else:
                polygon.append(QPointF(x1 - depth, 0))
                polygon.append(QPointF(x1, height / 2.0))     # right-pointing tip
                polygon.append(QPointF(x1 - depth, height))
            polygon.append(QPointF(x0, height))
            if index > 0:
                polygon.append(QPointF(x0 + depth, height / 2.0))  # left notch (interlocks with previous tip)

            painter.setPen(Qt.NoPen)
            painter.setBrush(activeColor if index == self.__currentIndex else inactiveColor)
            painter.drawPolygon(polygon)

            painter.setPen(self.__ACTIVE_TEXT if index == self.__currentIndex else self.__INACTIVE_TEXT)
            font = painter.font()
            font.setBold(index == self.__currentIndex)
            painter.setFont(font)
            left = x0 + (depth if index > 0 else 6)
            right = x1 if isLast else x1 - depth
            painter.drawText(QRectF(left, 0, max(1.0, right - left), height), Qt.AlignCenter, label)
        painter.end()
