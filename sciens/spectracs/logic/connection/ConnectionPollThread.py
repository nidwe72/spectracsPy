import sys

from PySide6.QtCore import QThread, Signal


class ConnectionPollThread(QThread):
    """§12 (5b-connect): poll a REAL spectrometer's USB presence OFF the GUI thread and report changes.

    Given a pre-resolved VID/PID (resolved once on the GUI thread at login), it loops `usb.core.find`
    every `intervalSeconds` and emits `presenceChanged(bool)` whenever presence flips (edge-triggered; the
    first check always emits, so the initial state is reported). It touches neither the DB nor the session
    — only the USB syscall — so a slow bus enumerate can never hitch the UI. Stop with `stop()` (interruptible
    within ~100 ms). pyusb is desktop-only; if missing, or if it has no backend, it reports absent once and exits.
    On Windows it polls the MSMF camera enumeration instead of the USB bus (SPEC_windows_build.md §6.1, W1.2).
    """

    presenceChanged = Signal(bool)

    def __init__(self, vendorId: str, modelId: str, intervalSeconds: float = 2.0, parent=None):
        super().__init__(parent)
        self.__vendorId = vendorId
        self.__modelId = modelId
        self.__intervalSeconds = intervalSeconds
        self.__running = True
        self.__lastPresent = None

    def stop(self):
        self.__running = False

    def run(self):
        if sys.platform == "win32":
            self.__pollCameraEnumeration()
            return
        try:
            import usb.core
        except ImportError:
            self.presenceChanged.emit(False)
            return

        vendorId = int('0x' + self.__vendorId, base=16)
        modelId = int('0x' + self.__modelId, base=16)

        while self.__running:
            try:
                present = usb.core.find(idVendor=vendorId, idProduct=modelId) is not None
            except usb.core.NoBackendError:
                # No libusb backend (Windows, SPEC_windows_build.md U4): it will never appear, and every further
                # find() would log a traceback ⇒ report absent once and stop polling.
                self.presenceChanged.emit(False)
                return
            except Exception:
                present = False
            if present != self.__lastPresent:
                self.__lastPresent = present
                self.presenceChanged.emit(present)
            # Interruptible sleep so stop() is responsive.
            for _ in range(int(self.__intervalSeconds * 10)):
                if not self.__running:
                    break
                self.msleep(100)

    def __pollCameraEnumeration(self):
        # Windows: presence = "is a camera with this VID/PID in the MSMF enumeration" — the lookup the capture
        # index comes from, so the light and the capture cannot disagree. The resolver never raises (it says absent).
        from sciens.spectracs.logic.application.video.capture.SensorCaptureIndexResolver import \
            SensorCaptureIndexResolver
        from types import SimpleNamespace
        resolver = SensorCaptureIndexResolver()
        sensor = SimpleNamespace(vendorId=self.__vendorId, modelId=self.__modelId)
        while self.__running:
            present = resolver.isPresent(sensor)
            if present != self.__lastPresent:
                self.__lastPresent = present
                self.presenceChanged.emit(present)
            for _ in range(int(self.__intervalSeconds * 10)):
                if not self.__running:
                    break
                self.msleep(100)
