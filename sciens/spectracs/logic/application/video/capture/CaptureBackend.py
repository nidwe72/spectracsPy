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

# The camera's uncompressed format under its two names: V4L2 says YUYV, Windows says YUY2 — the same bytes (B3).
UNCOMPRESSED_FOURCCS = ("YUYV", "YUY2")


def yuy2ToBgr(raw, width, height):
    """OUR conversion of a raw YUY2 (= YUYV) buffer to BGR — SPEC_windows_build.md §6.3, W1.3.

    The function OpenCV's V4L2 backend applies internally, called by us, so the 8-bit values do not depend on which
    OS (or which Media Foundation colour matrix) did the conversion. The backend hands the buffer over in its own
    shape (MSMF: 1×N), hence the flatten. None when the size does not fit a width×height YUY2 frame — then the
    backend did not deliver raw YUY2, and a guessed reshape would be noise."""
    import cv2
    import numpy as np
    if raw is None or width is None or height is None:
        return None
    flat = np.ascontiguousarray(raw).reshape(-1)
    if flat.dtype != np.uint8 or flat.size != width * height * 2:
        return None
    return cv2.cvtColor(flat.reshape(height, width, 2), cv2.COLOR_YUV2BGR_YUY2)


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
        self._backendName = None
        self._pixelFormat = None
        self._rawYuy2 = False       # True: read() gets the raw buffer and converts it itself (win32, W1.3)
        self._nativeControls = None  # win32: the camera's DirectShow controls (W1.6), set + read there

    def open(self, deviceId: int = 0, exposure: int = None, whiteBalanceKelvin: int = None) -> None:
        import cv2
        from sys import platform
        # V4L2 is the reference backend on Linux (verified in the probe). Windows PINS MSMF (SPEC_windows_build.md
        # §6.2): CAP_ANY is behaviour, not a contract, the resolver's index is an MSMF index, and only MSMF hands over
        # the raw YUY2 buffer (DSHOW ignores CONVERT_RGB=0, §6.6b). CAP_ANY elsewhere.
        windows = platform == 'win32'
        if platform == 'linux':
            apiPreference, self._backendName = cv2.CAP_V4L2, "V4L2"
        elif windows:
            apiPreference, self._backendName = cv2.CAP_MSMF, "MSMF"
        else:
            apiPreference, self._backendName = cv2.CAP_ANY, "ANY"
        self._deviceId = deviceId
        self._rawYuy2 = False
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
        self.__forceUncompressed(cv2, "YUY2" if windows else "YUYV", readBackNow=not windows)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2592)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1944)
        if windows:
            # ⭐ OUR conversion, not Media Foundation's (SPEC_windows_build.md §6.3): the backend hands over the raw
            # YUY2 bytes and `yuy2ToBgr` converts them with the function Linux's V4L2 backend uses. Fixed AT OPEN —
            # toggling CONVERT_RGB on a running MSMF stream breaks it (§6.6b).
            self._cap.set(cv2.CAP_PROP_CONVERT_RGB, 0)
            self._rawYuy2 = True
        # ⭐ The guard on the pinned format: a few grabs to prove the stream came up. §16.39.5a's whole
        # risk is that FORCING a format wedges the UVC stream on warm-up buffers, and that failure is silent
        # — read() simply never returns a frame. Proving it here, at open, is what makes the pin safe to
        # ship: if the stream is dead we reopen exactly as the code did before, and the operator sees why.
        # ⚠ SEVERAL grabs, not one: the first frames after open are routinely empty even on a healthy
        # stream (§3.5), so a single failure would condemn a working camera.
        streaming = any(self._cap.grab() for _ in range(8))
        if windows:
            # MSMF reports the granted format only once the stream is up — read right after the request it is
            # blank (seen in the VM, W1.3) — so the evidence is read here, after the grabs.
            self._pixelFormat = self.__fourccName(cv2)
            print("CaptureBackend: pixel format = %s (read back after open)" % self._pixelFormat)
            # ⛔ NO FALLBACK ON WINDOWS (§6.3.1): a stream that is not raw YUY2 — or not there — is refused, never
            # reopened unforced. A JPEG spectrum must not become a Windows Rv. read() then returns None, the path
            # every caller already takes for a camera that delivers nothing.
            refusal = None
            if self._pixelFormat not in UNCOMPRESSED_FOURCCS:
                refusal = "the driver granted %s, not YUY2" % self._pixelFormat
            elif not streaming:
                refusal = "no frame after opening YUY2"
            if refusal is not None:
                print("CaptureBackend: ⛔ REFUSED to capture on %s - %s (SPEC_windows_build.md §6.3)"
                      % (self._backendName, refusal))
                self.release()
                return
        elif not streaming:
            self.__reopenUnforced(cv2, deviceId, apiPreference)
        self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print("CaptureBackend: capture resolution = %dx%d (%s, %s%s)"
              % (self._width, self._height, self._backendName, self._pixelFormat,
                 ", own conversion" if self._rawYuy2 else ""))

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

        if windows:
            # W1.6: OpenCV cannot set WB on MSMF and reads exposure back wrong (§6.6b) — the camera's own
            # DirectShow controls do both. Same mode split as below, every control set on every open (§6.4b).
            self.__applyNativeControls(whiteBalanceKelvin)
            return

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

    def __applyNativeControls(self, whiteBalanceKelvin):
        """Windows: set every UVC control natively and PROVE the measurement state from the read-back (§6.4b).

        ⛔ A measurement open whose read-back does not show WB manual at the lamp's temperature, gain 0, backlight 0
        and manual exposure is REFUSED, like a non-YUY2 stream — auto-WB re-converging between reference and sample
        is the §14.8 tilt, and nothing downstream would notice. The calibration path (auto WB) only warns."""
        from sciens.spectracs.logic.application.video.capture.WindowsUvcControls import WindowsUvcControls, \
            provesFrozen
        from sciens.spectracs.logic.application.video.capture.SensorCaptureIndexResolver import CAP_MSMF
        problem = None
        readBack = {}
        try:
            from cv2_enumerate_cameras import enumerate_cameras
            path = next((camera.path for camera in enumerate_cameras(CAP_MSMF) if camera.index == self._deviceId), None)
            if path is None:
                raise LookupError("MSMF index %s is no longer enumerated" % self._deviceId)
            self._nativeControls = WindowsUvcControls(path)
            readBack = self._nativeControls.apply(whiteBalanceKelvin)
        except Exception as error:
            self._nativeControls = None
            problem = "native controls unavailable (%s: %s)" % (type(error).__name__, error)
        if problem is None and readBack.get("failures"):
            problem = "could not set %s" % ", ".join(readBack["failures"])
        print("CaptureBackend: native controls (%s) %s" % (
            "calibration, auto WB" if whiteBalanceKelvin is None else "measurement, WB %dK" % int(whiteBalanceKelvin),
            " ".join("%s=%s%s" % (name, entry.get("value"), "(auto)" if entry.get("flags") == 1 else "")
                     for name, entry in readBack.items() if isinstance(entry, dict))))
        if whiteBalanceKelvin is None:
            if problem is not None:
                print("CaptureBackend: ⚠ %s - the camera keeps whatever it was left with" % problem)
            return
        if problem is None and not provesFrozen(readBack, whiteBalanceKelvin):
            problem = "the read-back does not prove WB %dK manual / gain 0 / backlight 0 / manual exposure" \
                      % int(whiteBalanceKelvin)
        if problem is not None:
            print("CaptureBackend: ⛔ REFUSED to capture on %s - %s (SPEC_windows_build.md §6.4b)"
                  % (self._backendName, problem))
            self.release()

    def __nativeSettings(self):
        """Windows read-back of the live controls, from the camera itself; {} if it will not answer."""
        if self._nativeControls is None:
            return {}
        try:
            readBack = self._nativeControls.read()
        except Exception:
            return {}

        def value(name):
            return (readBack.get(name) or {}).get("value")

        exposure = readBack.get("Exposure") or {}
        whiteBalance = readBack.get("WhiteBalance") or {}
        return {
            # ⚠ log2-seconds steps (-13..-1), NOT V4L2 units — the unit bridge is W1.5 (§6.6c).
            "exposure": exposure.get("value"),
            "exposureMin": exposure.get("min"),
            "exposureMax": exposure.get("max"),
            "autoExposureMode": {1: "auto", 2: "manual"}.get(exposure.get("flags")),
            "wbTemperature": whiteBalance.get("value"),
            "autoWb": None if not whiteBalance else (1 if whiteBalance.get("flags") == 1 else 0),
            "gain": value("Gain"),
            "backlight": value("BacklightCompensation"),
        }

    def __fourccName(self, cv2):
        """The granted FOURCC as text, e.g. `YUY2`; None if the backend will not say."""
        try:
            code = int(self._cap.get(cv2.CAP_PROP_FOURCC))
        except Exception:
            return None
        return "".join(chr((code >> (8 * i)) & 0xFF) for i in range(4))

    def __forceUncompressed(self, cv2, requested, readBackNow=True):
        """Ask for the uncompressed format (`YUYV` on V4L2, `YUY2` on Windows — same bytes, B3) and say what was
        actually granted, in `_pixelFormat`. Never raises; never leaves the cap unusable. `readBackNow=False`
        (MSMF): the granted format is only readable once the stream is up, so `open()` reads it after the grabs."""
        try:
            granted = self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*requested))
            if not readBackNow:
                print("CaptureBackend: pixel format requested %s (set()=%s), read back after open" % (requested, granted))
                return
            code = int(self._cap.get(cv2.CAP_PROP_FOURCC))
            fourcc = "".join(chr((code >> (8 * i)) & 0xFF) for i in range(4))
        except Exception as error:                    # a pixel format is not worth a failed capture
            print("CaptureBackend: pixel format unchanged (%s)" % error)
            return
        self._pixelFormat = fourcc
        # ⛔ `set()` returns True on V4L2 even when it did nothing — the read-back is the only evidence,
        # which is the lesson the white-balance path already learned three lines of print ago.
        print("CaptureBackend: pixel format = %s (requested %s, set()=%s)" % (fourcc, requested, granted))
        if fourcc not in UNCOMPRESSED_FOURCCS:
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

    def __videoNode(self):
        """`/dev/videoN` for the open device, or None.

        `_deviceId` is the cv2 index, and on Linux/V4L2 the two coincide for a UVC camera. Anything else — a
        Windows host, a path-valued id, a node that is not there — simply says nothing, which is what every
        caller of this is built to accept."""
        import os
        node = "/dev/video%d" % self._deviceId if isinstance(self._deviceId, int) else None
        return node if node is not None and os.path.exists(node) else None

    def __queryControl(self, control):
        """`(min, max, default)` for one V4L2 control id, or None.

        ⛔ READ-ONLY and fully guarded: querying a control neither opens a stream nor disturbs a capture, and
        any failure at all returns None. A camera that will not answer simply says nothing."""
        import os, struct
        node = self.__videoNode()
        if node is None:
            return None
        import fcntl                                  # only past the node check: there is no fcntl on Windows (R7)
        size = 68                                     # sizeof(struct v4l2_queryctrl)
        request = 0xC0000000 | (size << 16) | (ord("V") << 8) | 36        # _IOWR('V', 36, v4l2_queryctrl)
        try:
            descriptor = os.open(node, os.O_RDONLY | os.O_NONBLOCK)
        except OSError:
            return None
        try:
            buffer = bytearray(struct.pack("I", control) + bytes(size - 4))
            try:
                fcntl.ioctl(descriptor, request, buffer, True)
            except OSError:
                return None
            low, high, _step, default = struct.unpack_from("iiii", buffer, 40)
            return low, high, default
        finally:
            os.close(descriptor)

    def __exposureRange(self):
        """(min, max) of the camera's manual exposure control, from V4L2 — or (None, None).

        ⚠ WHY AN IOCTL AND NOT `cap.get()`: OpenCV exposes control VALUES but not their RANGES, and the range
        is the whole point — 90 is an ELP number on a 1-500 scale, and the Orbbec board probed on 2026-08-30
        runs 0-6500 where the same 90 is a far darker frame (SPEC_capture_quality.md §16.39.5, D21)."""
        for control in (0x009A0902, 0x00980911):      # EXPOSURE_ABSOLUTE, then the legacy EXPOSURE
            answer = self.__queryControl(control)
            if answer is not None:
                return answer[0], answer[1]
        return None, None

    def __exposureModeName(self, value):
        """The DRIVER'S OWN name for auto-exposure mode `value` — e.g. `"Manual Mode"` — or None.

        ⛔⛔ WHY THIS EXISTS, and it cost an evening twice. `CAP_PROP_AUTO_EXPOSURE` is not a boolean. It is
        V4L2's `V4L2_CID_EXPOSURE_AUTO`, a MENU, and the enum runs

            0 AUTO   1 MANUAL   2 SHUTTER_PRIORITY   3 APERTURE_PRIORITY

        so the value that means *auto-exposure is OFF* is **1**, while `autoWb` sitting next to it on the same
        log line is a real boolean whose off value is **0**. Two adjacent controls, opposite conventions, both
        printed raw — and a log reading `autoExposure=1.0` was twice read as "the camera is auto-exposing"
        when it says the exact opposite (Edwin, 2026-09-06).
        ⭐ The name is asked of the DEVICE (`VIDIOC_QUERYMENU`) rather than mapped from a table here, so the
        line cannot drift from what the driver actually reports. A UVC camera typically publishes only 1 and
        3, and defaults to 3 — which is why pinning is not decoration.
        ⛔ READ-ONLY and fully guarded, like `__queryControl`: None on any failure, and the caller prints the
        bare number instead."""
        import os, struct
        node = self.__videoNode()
        if node is None or value is None:
            return None
        import fcntl                                  # only past the node check: there is no fcntl on Windows (R7)
        try:
            index = int(value)
        except (TypeError, ValueError):
            return None
        size = 44                                     # sizeof(struct v4l2_querymenu), PACKED
        request = 0xC0000000 | (size << 16) | (ord("V") << 8) | 37        # _IOWR('V', 37, v4l2_querymenu)
        try:
            descriptor = os.open(node, os.O_RDONLY | os.O_NONBLOCK)
        except OSError:
            return None
        try:
            buffer = bytearray(struct.pack("=II32sI", 0x009A0901, index, b"", 0))   # EXPOSURE_AUTO
            try:
                fcntl.ioctl(descriptor, request, buffer, True)
            except OSError:
                return None
            name = struct.unpack("=II32sI", bytes(buffer))[2].split(b"\0")[0]
            return name.decode("ascii", "replace") or None
        finally:
            os.close(descriptor)

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
        if self._rawYuy2:
            frame = yuy2ToBgr(frame, self._width, self._height)     # §6.3: our conversion, not the backend's
            if frame is None:
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

        def guarded(read, default):
            # Per field (R7): one control that will not answer must not blank the whole CAPTURE-SETTINGS line.
            try:
                return read()
            except Exception:
                return default

        low, high = guarded(self.__exposureRange, (None, None))
        settings = {
            "backend": self._backendName,
            "pixelFormat": self._pixelFormat,
            "exposureMin": low,
            "exposureMax": high,
            "exposure": get(cv2.CAP_PROP_EXPOSURE),
            # ⚠ A MENU INDEX, NOT A BOOLEAN — 1 is MANUAL, 3 is auto. `autoExposureMode` carries the
            # driver's own word for it so no reader has to know that (see `__exposureModeName`).
            "autoExposure": get(cv2.CAP_PROP_AUTO_EXPOSURE),
            "autoExposureMode": guarded(lambda: self.__exposureModeName(get(cv2.CAP_PROP_AUTO_EXPOSURE)), None),
            "wbTemperature": get(cv2.CAP_PROP_WB_TEMPERATURE),
            "autoWb": get(cv2.CAP_PROP_AUTO_WB),
            "gain": get(cv2.CAP_PROP_GAIN),
            "backlight": get(cv2.CAP_PROP_BACKLIGHT),
        }
        # Windows: the camera's own answer replaces OpenCV's (which cannot read WB and reads exposure back wrong).
        settings.update(guarded(self.__nativeSettings, {}))
        return settings

    def release(self) -> None:
        self._nativeControls = None
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
