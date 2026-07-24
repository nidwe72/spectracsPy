from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPixmap, QPen, QBrush

from sciens.spectracs.logic.application.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from sciens.spectracs.model.application.video.VideoSignal import VideoSignal
from sciens.spectracs.view.application.widgets.graphicsScene.BaseGraphicsRectItem import BaseGraphicsRectItem
from sciens.spectracs.view.application.widgets.video.BaseVideoViewModule import BaseVideoViewModule


class DevCaptureVideoViewModule(BaseVideoViewModule[VideoSignal]):
    """Preview sink for the dev capture view — paints each frame and, optionally, a read-only ROI box.

    The ROI box is drawn only when the parent view supplies it (setRoi) — i.e. when the current
    SpectrometerSetup has a profile assigned whose calibration carries the region-of-interest corners
    (SPEC_dev_capture_view.md §11). Corners are full-frame sensor pixels; the pixmap sits at scene
    origin unscaled, so scene coords == image pixels and no manual scaling is needed."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__roiItem = None
        self.__cropToRoi = False

    def setCropToRoi(self, cropped):
        # SPEC_simplified_plugin_navigation.md §5 (Change A): show ONLY the cropped ROI strip instead of the whole
        # frame + a dotted box. Because scene coords == image pixels, fitting the ROI rect IS the crop (no pixel
        # copy). Applied from the next painted frame.
        self.__cropToRoi = cropped

    def handleVideoThreadSignal(self, videoSignal: VideoSignal):
        image = videoSignal.image
        if image is None:
            return
        self.imageItem.setPixmap(QPixmap.fromImage(image))
        if self.__cropToRoi and self.__roiItem is not None:
            self.__roiItem.setVisible(False)  # the box is redundant once cropped
            # Fill the view with the ROI strip (IgnoreAspectRatio) so there are no black letterbox margins
            # around it (Edwin, rig cosmetic) — the strip's vertical axis is redundant, so the stretch is fine.
            self.videoWidget.fitInView(self.__roiItem, Qt.AspectRatioMode.IgnoreAspectRatio)
        else:
            self.videoWidget.fitInView(self.imageItem, Qt.AspectRatioMode.KeepAspectRatio)

    def setRoi(self, x1, y1, x2, y2):
        # Corners aren't ordered top-left/bottom-right (X1=left, X2=right, but Y1=lower/Y2=upper Hough
        # line — SPEC_dev_capture_view.md §11.2), so normalise via min/max before building the rect.
        left, top = min(x1, x2), min(y1, y2)
        rect = QRectF(left, top, abs(x2 - x1), abs(y2 - y1))
        if self.__roiItem is None:
            self.__roiItem = BaseGraphicsRectItem()
            pen = QPen(QBrush(ApplicationStyleLogicModule().getPrimaryColor()), 2)
            pen.setStyle(Qt.PenStyle.DotLine)
            pen.setCosmetic(True)  # constant on-screen width regardless of fitInView zoom
            self.__roiItem.setPen(pen)
            self.scene.addItem(self.__roiItem)  # added after imageItem → painted on top
        self.__roiItem.setRect(rect)
        self.__roiItem.setVisible(True)

    def clearRoi(self):
        if self.__roiItem is not None:
            self.__roiItem.setVisible(False)
