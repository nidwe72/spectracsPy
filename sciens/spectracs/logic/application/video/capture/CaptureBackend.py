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
    def open(self, deviceId: int = 0, exposure: int = None, whiteBalanceKelvin: int = None) -> None:
        raise NotImplementedError

    def read(self) -> QImage:
        raise NotImplementedError

    def setExposure(self, exposure: int) -> None:
        """Change exposure on the already-open device (for a live control). No-op by default."""
        pass

    def getResolution(self):
        """(width, height) actually delivered by the open device, or (None, None) if not open."""
        return (None, None)

    def readCameraSettings(self) -> dict:
        """Diagnostic read-back of the live camera controls (exposure / white-balance / gain / ...). Empty when
        the backend has no such notion. Best-effort — never raises."""
        return {}

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
        self._deviceId = None
        self._width = None
        self._height = None

    def open(self, deviceId: int = 0, exposure: int = None, whiteBalanceKelvin: int = None) -> None:
        import cv2
        from sys import platform
        # V4L2 is the reference backend on Linux (verified in the probe); CAP_ANY elsewhere.
        apiPreference = cv2.CAP_V4L2 if platform == 'linux' else cv2.CAP_ANY
        self._deviceId = deviceId
        self._cap = cv2.VideoCapture(deviceId, apiPreference)

        # Minimize driver frame buffering so read() returns the LATEST frame, not a stale queued one. At high
        # resolution the frame rate is low (~1.5 fps at 2592 over USB2), so a deep FIFO buffer means an exposure
        # change isn't visible for several reads — the "exposure looks like it does nothing / auto-exposure sees a
        # flat curve" symptom (SPEC_capture_quality.md §4.8). BUFFERSIZE=1 keeps only the freshest frame.
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # Capture resolution is PINNED to 2592x1944 for the ELP. DO NOT change this to "highest / native", to a
        # generic default, or back to 1920x1080 — each silently corrupts the spectrum (SPEC_capture_quality.md §4.9):
        #   * It MUST MATCH the calibration resolution. The ROI (regionOfInterestX1..Y2) and the px->nm cubic
        #     (interpolationCoefficientA..D) on SpectrometerCalibrationProfile were AUTHORED at 2592x1944; capturing
        #     at any other size mis-maps every wavelength. Capturing here => the existing calibration applies directly,
        #     no recalibration needed.
        #   * NOT the sensor max (3264x2448): it is not the calibration resolution (would need a recalibration), and
        #     its frame rate is even lower than 2592's ~1.5 fps, which makes the minimum exposure longer (a bright lamp
        #     saturates and can't be dimmed) and worsens frame-buffer staleness. (Exposure DOES work at 2592 — verified
        #     2026-07-15; the earlier "broken at high res" impression was a bright over-illuminated scene + stale
        #     buffered frames, now mitigated by BUFFERSIZE=1 above.)
        #   * NOT 1920x1080 (the prior hardcode / the regression this fixed): the ELP has no such mode, so V4L2 snapped
        #     it to 1600x1200 — BELOW the calibration size — clipping the ROI and putting the pumpkin Q-band off-frame.
        # readback confirms the driver honoured it; the extractor (ImageSpectrumAcquisitionLogicModule) also warns if
        # the ROI ever exceeds the frame, as a drift tripwire.
        # TODO: make this per-sensor (seed alongside the VID/PID in SpectrometerSensorUtil) when a second camera lands.
        # ⭐⭐ PIN THE PIXEL FORMAT — SPEC_capture_quality.md §16.39.5a.
        # ⛔⛔ The docstring above says "cv2 returns BGR either way, so nothing downstream changes." That
        # reasons about the API SURFACE, not the data: MJPG is lossy in both chroma and DCT, and a
        # JPEG-compressed spectrum would present as unexplained noise, never as an error. Enumerating the ELP
        # returns exactly two formats and **MJPG is index 0** — the driver's first — so today we rely on
        # OpenCV's V4L2 backend preferring uncompressed, which is its behaviour and not a contract.
        # ⚠ ORDER MATTERS: FOURCC goes BEFORE width/height, or V4L2 renegotiates and can snap the size — and
        # 2592x1944 exists in only one format on this camera.
        # ⚠ AND THE ORIGINAL RULE IS RESPECTED. "Do NOT force MJPG" exists because forcing a FOURCC once
        # wedged the stream on warm-up buffers; what is forced here is the UNCOMPRESSED one, the read-back
        # is checked, and `__yuyvOrFallback` reopens without forcing if the stream does not come up. The
        # fallback IS today's behaviour, so the worst case is what we already have.
        self.__forceUncompressed(cv2)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2592)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1944)
        # ⭐ The guard on the pinned format: a few grabs to prove the stream came up. §16.39.5a's whole
        # risk is that FORCING a format wedges the UVC stream on warm-up buffers, and that failure is silent
        # — read() simply never returns a frame. Proving it here, at open, is what makes the pin safe to
        # ship: if the stream is dead we reopen exactly as the code did before, and the operator sees why.
        # ⚠ SEVERAL grabs, not one: the first frames after open are routinely empty even on a healthy
        # stream (§3.5), so a single failure would condemn a working camera.
        if not any(self._cap.grab() for _ in range(8)):
            self.__reopenUnforced(cv2, deviceId, apiPreference)
        self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print("CaptureBackend: capture resolution = %dx%d" % (self._width, self._height))

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

        self._cap.set(cv2.CAP_PROP_GAIN, 0)             # pinned in BOTH modes (also undoes a sticky gain=100 a probe left)

        # White balance is MODE-SPLIT (SPEC_capture_quality.md §14.8, fix 1).
        if whiteBalanceKelvin is None:
            # CALIBRATION path — keep the camera's AUTO white-balance (and default backlight). The colour-anchored
            # wavelength peak-detection (§13/§14.6) is tuned for auto-WB's line prominences; do not disturb it.
            # Set it explicitly (not merely "untouched") so a manual WB left sticky by a prior measurement open on
            # the same /dev/videoN can't leak in.
            self._cap.set(cv2.CAP_PROP_AUTO_WB, 1)
        else:
            # MEASUREMENT path — FREEZE the auto loops so the reference/sample bursts are deterministic. Auto-WB +
            # auto-backlight otherwise re-converge after the AE exposure change, and the reference burst (run right
            # after the sweep) catches that transient while the settled sample does not — the reference-only settling
            # band the ksnip captures showed. Fixed to the LAMP's colour temperature (6500 K here), WB renders the
            # lamp neutrally: it cancels in T = S/R and gives the colour evaluation a stable per-channel balance.
            # Order matters on V4L2: auto OFF first, THEN the temperature control is live.
            self._cap.set(cv2.CAP_PROP_AUTO_WB, 0)
            self._cap.set(cv2.CAP_PROP_WB_TEMPERATURE, int(whiteBalanceKelvin))
            self._cap.set(cv2.CAP_PROP_BACKLIGHT, 0)
            actualWb = int(self._cap.get(cv2.CAP_PROP_WB_TEMPERATURE))
            print("CaptureBackend: white balance fixed = %dK (requested %dK)" % (actualWb, int(whiteBalanceKelvin)))

    def __forceUncompressed(self, cv2):
        """Ask for YUYV and say what was actually granted. Never raises; never leaves the cap unusable."""
        try:
            granted = self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUYV"))
            code = int(self._cap.get(cv2.CAP_PROP_FOURCC))
            fourcc = "".join(chr((code >> (8 * i)) & 0xFF) for i in range(4))
        except Exception as error:                    # a pixel format is not worth a failed capture
            print("CaptureBackend: pixel format unchanged (%s)" % error)
            return
        # ⛔ `set()` returns True on V4L2 even when it did nothing — the read-back is the only evidence,
        # which is the lesson the white-balance path already learned three lines of print ago.
        print("CaptureBackend: pixel format = %s (requested YUYV, set()=%s)" % (fourcc, granted))
        if fourcc != "YUYV":
            print("CaptureBackend: ⚠ the driver kept %s — if that is a COMPRESSED format the spectrum is "
                  "reading JPEG artefacts (SPEC_capture_quality.md §16.39.5a)" % fourcc)

    def __reopenUnforced(self, cv2, deviceId, apiPreference):
        """The guarded fallback: if forcing the format left a stream that will not deliver, reopen exactly
        as the code did before §16.39.5a. ⭐ The worst case of this change is therefore today's behaviour."""
        print("CaptureBackend: ⚠ no frame after pinning the pixel format — reopening unforced")
        try:
            self._cap.release()
        except Exception:
            pass
        self._cap = cv2.VideoCapture(deviceId, apiPreference)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2592)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1944)

    def __exposureRange(self):
        """(min, max) of the camera's manual exposure control, from V4L2 — or (None, None).

        ⚠ WHY AN IOCTL AND NOT `cap.get()`: OpenCV exposes control VALUES but not their RANGES, and the range
        is the whole point — 90 is an ELP number on a 1-500 scale, and the Orbbec board probed on 2026-08-30
        runs 0-6500 where the same 90 is a far darker frame (SPEC_capture_quality.md §16.39.5, D21).
        ⛔ READ-ONLY and fully guarded: querying a control neither opens a stream nor disturbs a capture, and
        any failure at all returns (None, None). A camera that will not answer simply says nothing."""
        import fcntl, os, struct
        node = "/dev/video%d" % self._deviceId if isinstance(self._deviceId, int) else None
        if node is None or not os.path.exists(node):
            return None, None
        size = 68                                     # sizeof(struct v4l2_queryctrl)
        request = 0xC0000000 | (size << 16) | (ord("V") << 8) | 36        # _IOWR('V', 36, v4l2_queryctrl)
        try:
            descriptor = os.open(node, os.O_RDONLY | os.O_NONBLOCK)
        except OSError:
            return None, None
        try:
            for control in (0x009A0902, 0x00980911):  # EXPOSURE_ABSOLUTE, then the legacy EXPOSURE
                buffer = bytearray(struct.pack("I", control) + bytes(size - 4))
                try:
                    fcntl.ioctl(descriptor, request, buffer, True)
                except OSError:
                    continue
                low, high = struct.unpack_from("ii", buffer, 40)
                return low, high
        finally:
            os.close(descriptor)
        return None, None

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

    def setExposure(self, exposure: int) -> None:
        import cv2
        if self._cap is not None and exposure is not None:
            # Re-assert V4L2 MANUAL exposure mode before the value: many UVC drivers ignore mid-stream
            # CAP_PROP_EXPOSURE writes unless manual mode is (re)asserted, so slider/auto-exposure changes had
            # no effect (the AE bisection saw constant brightness → slider stuck at the seed). Mirrors open().
            self._cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
            self._cap.set(cv2.CAP_PROP_EXPOSURE, exposure)

    def getResolution(self):
        return (self._width, self._height)

    def readCameraSettings(self) -> dict:
        # Diagnostic read-back of the live V4L2 controls (SPEC_capability_proof.md §7.0.1 — the reference-tilt
        # investigation: is the exposure / white-balance / gain drifting between reference and sample, run to run?).
        # cv2 .get() is a lightweight control query (VIDIOC_G_CTRL), distinct from frame grabbing; each read is
        # guarded so a failure yields a None entry rather than raising.
        import cv2
        if self._cap is None:
            return {}

        def get(prop):
            try:
                return self._cap.get(prop)
            except cv2.error:
                return None

        low, high = self.__exposureRange()
        return {
            "exposureMin": low,
            "exposureMax": high,
            "exposure": get(cv2.CAP_PROP_EXPOSURE),
            "autoExposure": get(cv2.CAP_PROP_AUTO_EXPOSURE),
            "wbTemperature": get(cv2.CAP_PROP_WB_TEMPERATURE),
            "autoWb": get(cv2.CAP_PROP_AUTO_WB),
            "gain": get(cv2.CAP_PROP_GAIN),
            "backlight": get(cv2.CAP_PROP_BACKLIGHT),
        }

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None


class AndroidUvcCaptureBackend(CaptureBackend):
    """DEFERRED (P7). The DIY spectrometer is a USB (UVC) camera; Android's Camera2 API does not
    expose external UVC devices, so this must go UVC-over-OTG: UsbManager grants a device fd ->
    libusb (libusb_wrap_sys_device) -> libuvc -> frames. Needs <uses-feature usb.host> +
    UsbManager.requestPermission (NOT android.permission.CAMERA). See spec §6."""

    def open(self, deviceId: int = 0, exposure: int = None, whiteBalanceKelvin: int = None) -> None:
        raise NotImplementedError("Android UVC-over-OTG capture is deferred (P7) — see spec §6")

    def read(self) -> QImage:
        raise NotImplementedError


class RaspberryPiNetworkCaptureBackend(CaptureBackend):
    """DEFERRED (P7) alternative. If the spectrometer gains a Raspberry-Pi tier, the Pi does the
    capture and the phone becomes a network client (reusing the Pyro/HTTP pattern) — no OTG. The
    choice between this and AndroidUvcCaptureBackend is made when the hardware direction is set."""

    def open(self, deviceId: int = 0, exposure: int = None, whiteBalanceKelvin: int = None) -> None:
        raise NotImplementedError("RPi-network capture is deferred (P7) — see spec §6")

    def read(self) -> QImage:
        raise NotImplementedError


def getCaptureBackend() -> CaptureBackend:
    """Pick the capture backend for the current platform. Today: desktop is real; Android raises
    on use (capture deferred — the virtual spectrometer is the on-device path for now)."""
    if is_android():
        return AndroidUvcCaptureBackend()
    return DesktopCv2CaptureBackend()
