from PyQt6 import QtGui
from PyQt6.QtWidgets import QWidget, QGraphicsLineItem
from PyQt6.QtWidgets import QGraphicsView
from PyQt6.QtWidgets import QGraphicsScene
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QGraphicsPixmapItem
from PyQt6.QtGui import QImage
from PyQt6.QtGui import QPixmap
from PyQt6.QtGui import QPen
from PyQt6.QtGui import QBrush
from PyQt6.QtGui import QColor

from PyQt6.QtCore import Qt

from logic.appliction.video.VideoThread import VideoThread

from model.application.video.VideoSignal import VideoSignal
from view.application.widgets.graphicsScene.BaseGraphicsLineItem import BaseGraphicsLineItem
from view.application.widgets.graphicsScene.BaseGraphicsPixmapItem import BaseGraphicsPixmapItem
from view.application.widgets.graphicsScene.BaseGraphicsScene import BaseGraphicsScene
from view.application.widgets.video.BaseVideoViewModule import BaseVideoViewModule

class VideoViewModule(BaseVideoViewModule[VideoSignal]):

    def handleVideoSignal(self,videoSignal:VideoSignal):
        image = videoSignal.image
        scene=self.videoWidget.scene()
        somePixmap = QPixmap.fromImage(image)
        self.imageItem.setPixmap(somePixmap)

        self.videoWidget.fitInView(self.imageItem.setPixmap, Qt.AspectRatioMode.KeepAspectRatio)










