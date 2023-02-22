from PySide6 import QtGui
from PySide6.QtWidgets import QWidget, QGraphicsLineItem
from PySide6.QtWidgets import QGraphicsView
from PySide6.QtWidgets import QGraphicsScene
from PySide6.QtWidgets import QGridLayout
from PySide6.QtWidgets import QGraphicsPixmapItem
from PySide6.QtGui import QImage
from PySide6.QtGui import QPixmap
from PySide6.QtGui import QPen
from PySide6.QtGui import QBrush
from PySide6.QtGui import QColor

from PySide6.QtCore import Qt

from logic.appliction.video.VideoThread import VideoThread

from model.application.video.VideoSignal import VideoSignal
from view.application.widgets.graphicsScene.BaseGraphicsLineItem import BaseGraphicsLineItem
from view.application.widgets.graphicsScene.BaseGraphicsPixmapItem import BaseGraphicsPixmapItem
from view.application.widgets.graphicsScene.BaseGraphicsScene import BaseGraphicsScene
from view.application.widgets.video.BaseVideoViewModule import BaseVideoViewModule

class VideoViewModule(BaseVideoViewModule[VideoSignal]):

    def handleVideoThreadSignal(self, videoSignal:VideoSignal):
        image = videoSignal.image
        scene=self.videoWidget.scene()
        somePixmap = QPixmap.fromImage(image)
        self.imageItem.setPixmap(somePixmap)

        self.videoWidget.fitInView(self.imageItem, Qt.AspectRatioMode.KeepAspectRatio)










