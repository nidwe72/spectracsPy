from PySide6.QtGui import QPixmap

from PySide6.QtCore import Qt

from chromos.spectracs.model.application.video.VideoSignal import VideoSignal
from view.application.widgets.video.BaseVideoViewModule import BaseVideoViewModule

class VideoViewModule(BaseVideoViewModule[VideoSignal]):

    def handleVideoThreadSignal(self, videoSignal:VideoSignal):
        image = videoSignal.image
        scene=self.videoWidget.scene()
        somePixmap = QPixmap.fromImage(image)
        self.imageItem.setPixmap(somePixmap)

        self.videoWidget.fitInView(self.imageItem, Qt.AspectRatioMode.KeepAspectRatio)










