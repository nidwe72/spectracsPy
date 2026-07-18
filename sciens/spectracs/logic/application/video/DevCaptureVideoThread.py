import threading

from PySide6.QtCore import Signal

from sciens.spectracs.logic.application.video.VideoThread import VideoThread
from sciens.spectracs.model.application.video.VideoSignal import VideoSignal


class DevCaptureVideoThread(VideoThread[VideoSignal]):
    """Thin continuous capture thread for the dev "Capture images" view. The base VideoThread sets
    self.qImage but emits no view signal (onCapturedFrame is dead) — every live view supplies its own
    emit in afterCapture(). This one just forwards the raw frame; no ROI/Hough processing.

    Run it with frameCount 0 (setFrameCount(0)) so the base afterCapture() never sets the stop flag and
    it streams until stop(). event.wait() gives one-frame backpressure (render before next grab)."""

    videoThreadSignal = Signal(threading.Event, VideoSignal)

    def createSignal(self) -> VideoSignal:
        signal = VideoSignal()
        signal.image = self.qImage
        signal.framesCount = self.getFrameCount()
        signal.currentFrameIndex = self._getCurrentFrameIndex()
        return signal

    def afterCapture(self):
        super().afterCapture()

        if self.qImage is None:      # warm-up / failed read — nothing to show yet
            return

        signal = self.createSignal()
        event = threading.Event()
        self.videoThreadSignal.emit(event, signal)
        self.__waitForRender(event)

    def __waitForRender(self, event):
        # One-frame backpressure — but INTERRUPTIBLE by stop(). Without this, a synchronous stop (CapturePanel
        # now waits for the camera to be released before an immediate reopen — the plugin-switch/restart race)
        # would DEADLOCK: the GUI thread blocked in QThread.wait() cannot run the slot that sets this event, so
        # the worker would block here forever. Polling lets a stop() break us out within one tick, GUI or not, so
        # run() falls through to backend.release(). Normal renders set the event well under a tick — no added lag.
        while not event.wait(0.05):
            if not self._runFlag:
                return

    def _emitPreview(self):
        # Live preview during the auto-exposure sweep. Uses the SAME one-frame backpressure as afterCapture
        # (emit -> event.wait): the capture thread sits idle while the main thread paints, so there is never a
        # concurrent backend-read + Qt-paint on the same frame (fire-and-forget segfaulted). The sweep pays a few
        # ms of paint time per probe -- harmless, and it does NOT re-read the live stream, so exposure measurement
        # is unaffected.
        if self.qImage is None:
            return
        signal = self.createSignal()
        signal.isPreview = True   # mark it: a preview frame must never become a capture burst's __latestImage (§14.6)
        event = threading.Event()
        self.videoThreadSignal.emit(event, signal)
        self.__waitForRender(event)
