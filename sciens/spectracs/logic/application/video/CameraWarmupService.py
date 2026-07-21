import time

from sciens.base.Singleton import Singleton
from sciens.spectracs.logic.application.video.CameraLease import CameraLease
from sciens.spectracs.logic.application.video.CameraWarmupVideoThread import CameraWarmupVideoThread

# Bounded wait for the warm-keeper to release the device on pause() — must return BEFORE the consumer opens (§16.6
# #1). Normally sub-second (the loop checks the stop flag each fast read); the bound guards a wedged cv2 read.
_PAUSE_WAIT_MS = 3000

# Stuck warm-keeper threads (blocked in a cv2 call past the bound) are parked here so they are not GC'd mid-run
# (the "QThread destroyed while running" abort) and can finish on their own — mirrors CapturePanel._STUCK_CAPTURE_THREADS.
_STUCK_WARMKEEPERS = []


def _retireStuckWarmKeeper(thread):
    _STUCK_WARMKEEPERS.append(thread)
    thread.finished.connect(
        lambda: _STUCK_WARMKEEPERS.remove(thread) if thread in _STUCK_WARMKEEPERS else None)


class CameraWarmupService(Singleton):
    """Idle warm-keeper (SPEC_capture_quality.md §16.6): streams the real camera whenever no consumer holds it, so the
    sensor stays at thermal equilibrium and every measurement's Reference is captured warm (R and S then share the
    sensor state → the responsivity tilt cancels in S/R). Registered with CameraLease: PAUSE (stop + bounded wait for
    the device to be released) when a consumer acquires, RESUME when the last releases. Tracks `warmSince` for the
    warming indicator. Lifecycle is driven by device presence (start when present post-login, stop when unplugged)."""

    def __init__(self):
        if getattr(self, "_initialised", False):
            return
        self._initialised = True
        self.__thread = None
        self.__deviceId = None
        self.__exposure = None
        self.__running = False
        self.__warmSince = None
        CameraLease().registerWarmKeeper(self.__pause, self.__resume)

    # --- lifecycle (driven by the connection indicator on device presence) ---

    def start(self, deviceId, exposure=None):
        if self.__running and self.__deviceId == deviceId:
            return
        self.stop()
        self.__deviceId = deviceId
        self.__exposure = exposure
        self.__running = True
        self.__warmSince = time.monotonic()      # warmth begins now; persists through lease handoffs
        if CameraLease().activeCount() == 0:      # if a consumer is already streaming, it keeps it warm
            self.__startThread()

    def stop(self):
        self.__running = False
        self.__warmSince = None
        self.__deviceId = None
        self.__stopThread()

    # --- warming indicator queries (called from the GUI thread) ---

    def isWarming(self, warmupSeconds):
        if not self.__running or self.__warmSince is None:
            return False
        return (time.monotonic() - self.__warmSince) < warmupSeconds

    def warmupElapsedSeconds(self):
        if self.__warmSince is None:
            return None
        return time.monotonic() - self.__warmSince

    # --- CameraLease callbacks (called under the lease lock, from a consumer thread) ---

    def __pause(self):
        self.__stopThread()                       # release the device BEFORE the consumer opens

    def __resume(self):
        if self.__running and self.__deviceId is not None:
            self.__startThread()

    # --- warm-keeper thread control ---

    def __startThread(self):
        if self.__thread is not None:
            return
        thread = CameraWarmupVideoThread()
        thread.setIsVirtual(False)
        thread.setDeviceId(self.__deviceId)
        if self.__exposure is not None:
            thread.setExposure(self.__exposure)
        thread.setFrameCount(0)                   # continuous stream
        self.__thread = thread
        thread.start()

    def __stopThread(self):
        thread = self.__thread
        self.__thread = None
        if thread is not None:
            thread.stop()
            if not thread.wait(_PAUSE_WAIT_MS):
                _retireStuckWarmKeeper(thread)    # can't guarantee release — parked; the consumer open may EBUSY (rare)
