import threading

from PySide6.QtCore import Signal

from chromos.spectracs.logic.appliction.video.VideoThread import VideoThread
from chromos.spectracs.model.signal.SpectrometerCalibrationProfileHoughLinesVideoSignal import \
    SpectrometerCalibrationProfileHoughLinesVideoSignal


class SpectrometerCalibrationProfileHoughLinesVideoThread(
    VideoThread[SpectrometerCalibrationProfileHoughLinesVideoSignal]):
    videoThreadSignal = Signal(threading.Event, SpectrometerCalibrationProfileHoughLinesVideoSignal)

    def createSignal(self) -> SpectrometerCalibrationProfileHoughLinesVideoSignal:
        super().createSignal()

        spectrometerCalibrationProfileHoughLinesVideoSignal = SpectrometerCalibrationProfileHoughLinesVideoSignal()
        spectrometerCalibrationProfileHoughLinesVideoSignal.image = self.qImage

        spectrometerCalibrationProfileHoughLinesVideoSignal.framesCount = self.getFrameCount()
        spectrometerCalibrationProfileHoughLinesVideoSignal.currentFrameIndex = self._getCurrentFrameIndex()

        return spectrometerCalibrationProfileHoughLinesVideoSignal

    def onStart(self):
        super().onStart()

    def afterCapture(self):
        super().afterCapture()

        signal = self.createSignal()

        event = threading.Event()
        self.videoThreadSignal.emit(event, signal)
        event.wait()
