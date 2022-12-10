from PySide6.QtCore import Qt, QSize, QPoint, QRectF, QPointF, Slot, Property
from PySide6.QtGui import QPen, QBrush, QColor, QPaintEvent, QPainter, QFont, QPainterPath
from PySide6.QtWidgets import QCheckBox


class ToggleSwitch(QCheckBox):
    _transparent_pen = QPen(Qt.transparent)
    _light_grey_pen = QPen(Qt.lightGray)
    _black_pen = QPen(Qt.black)

    __checked_color = Qt.white

    def __init__(self,
                 parent=None,
                 bar_color=Qt.gray,
                 checked_color=Qt.white,
                 handle_color=Qt.white):

        super().__init__(parent)

        # Save our properties on the object via self, so we can access them later
        # in the paintEvent.
        self._bar_brush = QBrush(bar_color)
        self._bar_checked_brush = QBrush(QColor(checked_color).lighter())

        self._handle_brush = QBrush(handle_color)
        self._handle_checked_brush = QBrush(QColor(checked_color))

        # Setup the rest of the widget.

        #self.setContentsMargins(8, 0, 8, 0)
        self.setContentsMargins(1, 1, 0, 0)
        self._handle_position = 0
        self._fontSize = 10

        self.stateChanged.connect(self.handle_state_change)

    def sizeHint(self):
        return QSize(58, 45)

    def hitButton(self, pos: QPoint):
        return self.contentsRect().contains(pos)

    def paintEvent(self, e: QPaintEvent):

        self._h_scale=1.0
        self._v_scale = 1.0

        contRect = self.contentsRect()
        width = contRect.width() * self._h_scale
        height = contRect.height() * self._v_scale
        handleRadius = round(0.24 * height)

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        p.setPen(self._transparent_pen)
        #barRect = QRectF(0, 0, width - handleRadius, 0.40 * height)
        barRect = QRectF(0, 0, width, height)
        barRect.moveCenter(contRect.center())

        # the handle will move along this line
        trailLength = contRect.width() * self._h_scale - 2 * handleRadius
        xLeft = contRect.center().x() - (trailLength + handleRadius) / 2
        xPos = xLeft + handleRadius + trailLength * self._handle_position

        outerRectanglePainterPath=QPainterPath()
        outerRectanglePainterPath.addRect(barRect)


        handleRectanglePainterPath=QPainterPath()



        if self.isChecked():
            #p.setBrush(self._bar_checked_brush)
            #p.drawRect(barRect)
            #p.setBrush(self._handle_checked_brush)
            p.setPen(self._light_grey_pen)
            p.drawPath(outerRectanglePainterPath)

            handleRect = QRectF(width-60-10, 10, 60, height-10-10)
            handleRectanglePainterPath.addRect(handleRect)
            p.setPen(QPen(self.__checked_color))
            p.drawPath(handleRectanglePainterPath)

            # p.setFont(QFont('Helvetica', self._fontSize, 75))
            # p.drawText(xLeft + handleRadius / 2, contRect.center().y() +handleRadius / 2, "ON")

        else:
            #p.setBrush(self._bar_brush)
            #p.drawRect(barRect)
            #p.setBrush(self._handle_brush)

            p.setPen(self._light_grey_pen)
            p.drawPath(outerRectanglePainterPath)

            handleRect = QRectF(10, 10, 60+10, height-10-10)
            handleRectanglePainterPath.addRect(handleRect)
            p.drawPath(handleRectanglePainterPath)

            # p.setFont(QFont('Helvetica', self._fontSize, 75))
            # p.drawText(xLeft + handleRadius / 2, contRect.center().y() +handleRadius / 2, "OFF")

        # p.setPen(self._light_grey_pen)
        # p.drawEllipse(QPointF(xPos, barRect.center().y()),handleRadius, handleRadius)

        p.end()

    @Slot(int)
    def handle_state_change(self, value):
        self._handle_position = 1 if value else 0

    @Property(float)
    def handle_position(self):
        return self._handle_position

    @handle_position.setter
    def handle_position(self, pos):
        """change the property
           we need to trigger QWidget.update() method, either by:
           1- calling it here [ what we're doing ].
           2- connecting the QPropertyAnimation.valueChanged() signal to it.
        """
        self._handle_position = pos
        self.update()

    def setH_scale(self, value):
        self._h_scale = value
        self.update()

    def setV_scale(self, value):
        self._v_scale = value
        self.update()

    def setFontSize(self, value):
        self._fontSize = value
        self.update()