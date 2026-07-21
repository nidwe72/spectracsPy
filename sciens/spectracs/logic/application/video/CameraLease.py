import threading

from sciens.base.Singleton import Singleton


class CameraLease(Singleton):
    """Coordinates exclusive access to the single camera device (/dev/videoN) between the idle warm-keeper and the
    real capture consumers — measurement, both calibration threads, dev-capture, spectral-job (SPEC_capture_quality.md
    §16.6). Every real consumer `acquire()`s before `backend.open()` and `release()`s after (in `VideoThread.run`'s
    finally); the warm-keeper is exempt (it IS the idle-holder).

    First `acquire()` → `onBusy()`: the warm-keeper PAUSES and releases the device BEFORE the consumer opens (so the
    two never both hold it → no EBUSY). Last `release()` → `onIdle()`: the warm-keeper resumes. Thread-safe: `acquire`
    and `release` run on different consumer worker threads."""

    def __init__(self):
        if getattr(self, "_initialised", False):
            return
        self._initialised = True
        self.__lock = threading.RLock()
        self.__count = 0
        self.__onBusy = None
        self.__onIdle = None

    def registerWarmKeeper(self, onBusy, onIdle):
        with self.__lock:
            self.__onBusy = onBusy
            self.__onIdle = onIdle

    def acquire(self):
        # Called from a consumer's VideoThread.run BEFORE backend.open(). Blocks (via onBusy) until the warm-keeper
        # has released the device.
        with self.__lock:
            self.__count += 1
            if self.__count == 1 and self.__onBusy is not None:
                self.__onBusy()

    def release(self):
        # Called from the same consumer thread AFTER backend.release(), in a finally.
        with self.__lock:
            if self.__count <= 0:
                return
            self.__count -= 1
            if self.__count == 0 and self.__onIdle is not None:
                self.__onIdle()

    def activeCount(self):
        with self.__lock:
            return self.__count
