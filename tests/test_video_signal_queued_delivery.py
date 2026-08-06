"""`VideoSignal` must NOT be a QObject — the queued cross-thread delivery is a use-after-free if it is.

The bug, seen on the rig 2026-08-06 (`CapturePanel.py:413`):

    AttributeError: 'CameraWarmupVideoThread' object has no attribute 'isPreview'

`videoThreadSignal = Signal(threading.Event, VideoSignal)` crosses threads, so Qt QUEUES it. While `VideoSignal`
was a QObject, Qt marshalled it as a raw `QObject*` and the only Python reference was a local in
`DevCaptureVideoThread.afterCapture()`. On the STOP path `__waitForRender` returns early
(`if not self._runFlag: return`), so that local died before the GUI thread delivered the queued event: the
wrapper was freed, C++ deleted the object, and the stale pointer was later resolved to whatever had taken the
address — in practice the `CameraWarmupVideoThread` that CameraLease RESUME constructs at exactly that moment,
because stopping the capture releases the lease. Hence a *thread* arriving where a *signal* should be.

⚠ The AttributeError was the mild outcome. Reproduced against the old definition, this test SEGFAULTS the
interpreter — which is why the guard is a test and not just a comment on the class.

The fix is that `VideoSignal` is a plain Python class: PySide then marshals it as PyObject and holds a
reference for the queued delivery, so it cannot be freed early. (`threading.Event`, in the same signature, has
always worked for exactly this reason.)

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python -m pytest tests/test_video_signal_queued_delivery.py -q
"""
import gc
import threading
import unittest

from PySide6.QtCore import QCoreApplication, QObject, QThread, QTimer, Signal

from sciens.spectracs.model.application.video.VideoSignal import VideoSignal
from sciens.spectracs.model.signal.SpectrometerCalibrationProfileHoughLinesVideoSignal import \
    SpectrometerCalibrationProfileHoughLinesVideoSignal
from sciens.spectracs.model.spectral.SpectralVideoThreadSignal import SpectralVideoThreadSignal

FRAMES = 60


class _Worker(QThread):
    # The SAME declaration as DevCaptureVideoThread — a Python type in a Qt signal signature.
    videoThreadSignal = Signal(threading.Event, VideoSignal)

    def run(self):
        for index in range(FRAMES):
            signal = VideoSignal()
            signal.image = None
            signal.framesCount = 0
            signal.currentFrameIndex = index
            signal.isPreview = (index % 2 == 0)
            self.videoThreadSignal.emit(threading.Event(), signal)
            # THE BUG PATH: abandon the local WITHOUT waiting for the render — exactly what __waitForRender
            # does when stop() flips _runFlag — then force collection so the race is deterministic.
            del signal
            gc.collect()


class VideoSignalQueuedDeliveryTest(unittest.TestCase):

    def test_video_signal_is_not_a_qobject(self):
        # The structural guard. If someone re-adds QObject, this fails before the slower race test runs.
        self.assertFalse(issubclass(VideoSignal, QObject),
                         "VideoSignal must stay a plain Python class — see this module's docstring")
        for subclass in (SpectralVideoThreadSignal, SpectrometerCalibrationProfileHoughLinesVideoSignal):
            self.assertFalse(issubclass(subclass, QObject), "%s inherits the same constraint" % subclass.__name__)

    def test_queued_delivery_survives_the_sender_dropping_its_reference(self):
        application = QCoreApplication.instance() or QCoreApplication([])
        received = []

        class Panel(QObject):
            def onSignal(self, event, videoSignal):
                # The exact access that raised on the rig (CapturePanel.handleVideoThreadSignal).
                received.append((type(videoSignal).__name__, videoSignal.isPreview, videoSignal.currentFrameIndex))

        panel = Panel()
        worker = _Worker()
        worker.videoThreadSignal.connect(panel.onSignal)          # cross-thread => queued
        worker.finished.connect(lambda: QTimer.singleShot(200, application.quit))
        worker.start()
        QTimer.singleShot(30000, application.quit)                 # never hang the suite
        application.exec()
        worker.wait(3000)

        self.assertEqual(FRAMES, len(received), "every queued signal must arrive")
        self.assertEqual({"VideoSignal"}, {name for name, _, _ in received},
                         "a foreign type here means the payload was freed and its address reused")
        self.assertEqual(list(range(FRAMES)), [index for _, _, index in received], "payload must stay intact")
        self.assertEqual([index % 2 == 0 for index in range(FRAMES)], [preview for _, preview, _ in received])


if __name__ == "__main__":
    unittest.main()
