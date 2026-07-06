"""P7 scaffold — capture-backend abstraction (DESIGN, mostly deferred).

Real-hardware capture on Android is hardware-gated (no spectrometer on hand; a Raspberry-Pi tier is
an open idea) — see docs/SPEC_android_port.md §6. This module encodes the *platform split* so the
architecture is in place; only the desktop backend is real today. VideoThread is NOT yet routed
through this (that refactor lands with P7 proper, once hardware / the RPi decision exists).

    getCaptureBackend() -> CaptureBackend         # picks the right backend for the platform
    backend.read() -> QImage | None               # one frame (BGR->RGB QImage), None on failure
"""
from PySide6.QtGui import QImage

from sciens.base.PlatformUtil import is_android


class CaptureBackend:
    def open(self, deviceId: int = 0, exposure: int = None) -> None:
        raise NotImplementedError

    def read(self) -> QImage:
        raise NotImplementedError

    def release(self) -> None:
        pass


class DesktopCv2CaptureBackend(CaptureBackend):
    """Real desktop path: cv2.VideoCapture over a USB/UVC webcam. Now the single owner of the cv2
    capture flags (extracted from VideoThread — R1). Two robustness rules baked in from the bench
    findings (SPEC_real_camera_capture.md §0):
      - Do NOT force MJPG. On newer OpenCV forcing MJPG can raise inside read() on empty warm-up
        buffers and wedge the UVC stream; let the driver default (YUYV) negotiate — cv2 returns BGR
        either way, so nothing downstream changes.
      - read() never raises: an empty/failed/raising read returns None, and the caller keeps the last
        good frame.

    Capture params (resolution/exposure) stay HARDCODED at today's values for now — they become
    configurable later (likely plugin-driven), see spec §4/§7.3."""

    def __init__(self):
        self._cap = None

    def open(self, deviceId: int = 0, exposure: int = None) -> None:
        import cv2
        from sys import platform
        # V4L2 is the reference backend on Linux (verified in the probe); CAP_ANY elsewhere.
        apiPreference = cv2.CAP_V4L2 if platform == 'linux' else cv2.CAP_ANY
        self._cap = cv2.VideoCapture(deviceId, apiPreference)

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

        # AUTO_EXPOSURE=1 selects MANUAL exposure mode on V4L2, then a fixed value (there is no
        # auto-exposure today — spec §7.4/§9.3). `exposure` is the per-camera good value seeded in
        # SpectrometerSensorUtil (e.g. ELP CFL calibration = 78); None falls back to the legacy default.
        self._cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
        if exposure is not None:
            self._cap.set(cv2.CAP_PROP_EXPOSURE, exposure)
        elif platform == 'linux':
            self._cap.set(cv2.CAP_PROP_EXPOSURE, 150)
        elif platform == 'win32':
            self._cap.set(cv2.CAP_PROP_EXPOSURE, -3)

    def read(self) -> QImage:
        import cv2
        if self._cap is None:
            return None
        try:
            ok, frame = self._cap.read()   # OpenCV can *raise* on an empty UVC buffer — never let it out
        except cv2.error:
            return None
        if not ok or frame is None:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        # .copy() detaches the QImage from the numpy buffer `rgb` (which is freed when this returns) —
        # otherwise the QImage points at released memory (the "crashes after some frames" symptom).
        return QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None


class AndroidUvcCaptureBackend(CaptureBackend):
    """DEFERRED (P7). The DIY spectrometer is a USB (UVC) camera; Android's Camera2 API does not
    expose external UVC devices, so this must go UVC-over-OTG: UsbManager grants a device fd ->
    libusb (libusb_wrap_sys_device) -> libuvc -> frames. Needs <uses-feature usb.host> +
    UsbManager.requestPermission (NOT android.permission.CAMERA). See spec §6."""

    def open(self, deviceId: int = 0, exposure: int = None) -> None:
        raise NotImplementedError("Android UVC-over-OTG capture is deferred (P7) — see spec §6")

    def read(self) -> QImage:
        raise NotImplementedError


class RaspberryPiNetworkCaptureBackend(CaptureBackend):
    """DEFERRED (P7) alternative. If the spectrometer gains a Raspberry-Pi tier, the Pi does the
    capture and the phone becomes a network client (reusing the Pyro/HTTP pattern) — no OTG. The
    choice between this and AndroidUvcCaptureBackend is made when the hardware direction is set."""

    def open(self, deviceId: int = 0, exposure: int = None) -> None:
        raise NotImplementedError("RPi-network capture is deferred (P7) — see spec §6")

    def read(self) -> QImage:
        raise NotImplementedError


def getCaptureBackend() -> CaptureBackend:
    """Pick the capture backend for the current platform. Today: desktop is real; Android raises
    on use (capture deferred — the virtual spectrometer is the on-device path for now)."""
    if is_android():
        return AndroidUvcCaptureBackend()
    return DesktopCv2CaptureBackend()
