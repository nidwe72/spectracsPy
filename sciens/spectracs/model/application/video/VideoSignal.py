from PySide6.QtGui import QImage


# ⚠ DELIBERATELY NOT A QObject. This is a pure data carrier, and it travels over a CROSS-THREAD (queued)
# connection: `videoThreadSignal = Signal(threading.Event, VideoSignal)`. As a QObject, Qt marshalled it as a
# raw QObject* while the only Python reference was a local in DevCaptureVideoThread.afterCapture(). On the STOP
# path `__waitForRender` returns early (`if not self._runFlag: return`), so that local died before the GUI thread
# delivered the queued event — the wrapper was freed, C++ deleted the object, and the stale pointer was then
# resolved to whatever had since taken the address. In practice that was the CameraWarmupVideoThread which
# CameraLease RESUME constructs at exactly that moment, so the slot received a *thread* and blew up on
# `videoSignal.isPreview`. As a plain Python class PySide marshals it as PyObject and holds a reference for the
# queued delivery, so it cannot be freed early. `threading.Event` in the same signature has always worked for
# precisely this reason. Do not re-add QObject; nothing here needs one (no signals, no parent, no deleteLater).
class VideoSignal:
    image:QImage
    currentFrameIndex:int
    framesCount:int
    # True only for frames emitted DURING the auto-exposure sweep (live preview). Consumers that feed a capture
    # burst must NOT treat these as the latest capturable frame (SPEC_capture_quality.md §14.6 drop logic).
    isPreview:bool = False



