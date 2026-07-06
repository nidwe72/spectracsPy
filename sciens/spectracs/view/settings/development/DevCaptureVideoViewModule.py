from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from sciens.spectracs.model.application.video.VideoSignal import VideoSignal
from sciens.spectracs.view.application.widgets.video.BaseVideoViewModule import BaseVideoViewModule


class DevCaptureVideoViewModule(BaseVideoViewModule[VideoSignal]):
    """Plain preview sink for the dev capture view — just paints each frame, no overlays."""

    def handleVideoThreadSignal(self, videoSignal: VideoSignal):
        image = videoSignal.image
        if image is None:
            return
        self.imageItem.setPixmap(QPixmap.fromImage(image))
        self.videoWidget.fitInView(self.imageItem, Qt.AspectRatioMode.KeepAspectRatio)
