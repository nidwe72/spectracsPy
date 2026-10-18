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
from sciens.spectracs.logic.camera.CameraDevice import CameraDevice
from sciens.spectracs.logic.camera.CameraProfile import CameraProfile
from sciens.spectracs.logic.camera.CameraSettingsResolver import CameraSettingsResolver
from sciens.spectracs.model.spectral.camera.CameraOpenRecord import CameraOpenRecord
from sciens.spectracs.plugin_sdk.camera.CameraControl import CameraControl
from sciens.spectracs.plugin_sdk.camera.CameraSettings import CameraSettings

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


def requireProfile(profile):
    """⛔ Every opener passes its spectral profile EXPLICITLY (SPEC_camera_settings.md §2, D1) — never again inferred
    from `whiteBalanceKelvin is None`, which is how the warm-keeper came to run with calibration semantics."""
    if profile is None:
        raise ValueError("CaptureBackend.open needs a CameraProfile (SPEC_camera_settings.md §2)")
    return CameraProfile.of(profile)


class CaptureBackend:
    def open(self, deviceId: int = 0, profile=None, override=None, exposureSeed: int = None) -> CameraOpenRecord:
        """Open the camera and set EVERY control it offers, resolved `device default ← profile ← override`; read
        each back. Returns the CameraOpenRecord — `refusal` set when a MEASUREMENT open could not be proven, and
        then no frame is delivered (SPEC_camera_settings.md §5)."""
        raise NotImplementedError

    def read(self) -> QImage:
        raise NotImplementedError

    def setExposure(self, exposure: int):
        """Change exposure on the already-open device (a live control, §3.3a). Returns the value the camera
        APPLIED in V4L2 units, or None when it will not say. No-op by default."""
        return None

    def getOpenRecord(self):
        """The CameraOpenRecord of the current open, or None before the first."""
        return None

    def readCameraState(self) -> CameraSettings:
        """The read-back of every control, as a CameraSettings — what a leg snapshot records (§4). Empty when the
        backend has no such notion."""
        return CameraSettings()

    @staticmethod
    def readDeviceDefaults(deviceId) -> CameraDevice:
        """⭐ The camera's FACTORY STATE, from its firmware — no open, no stream (§3.4).

        Linux asks V4L2 on its own fd, so it is safe from the GUI thread while the warm-keeper streams (E4).
        ⚠ Windows answers an empty CameraDevice until CS3 reads `GetRange` there; Android/RPi likewise."""
        from sys import platform
        if platform != "linux" or is_android():
            return CameraDevice()
        from sciens.spectracs.logic.application.video.capture.LinuxUvcControls import LinuxUvcControls
        controls = LinuxUvcControls.forDevice(deviceId)
        if controls is None:
            return CameraDevice()
        try:
            return controls.describe()
        finally:
            controls.close()

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
        self._rawYuy2 = False       # True: read() gets the raw buffer and converts it itself (W1.3 win32, W1.4b Linux)
        self._nativeControls = None  # win32: the camera's DirectShow controls (W1.6), set + read there
        self._controls = None        # linux: LinuxUvcControls — the ONE writer of every control (CS2)
        self._record = None          # CameraOpenRecord of the current open
        self._resolution = None

    # Tests replace the Linux controls (a fake V4L2 node); None = LinuxUvcControls.forDevice.
    controlsFactory = None

    def getOpenRecord(self):
        return self._record

    def open(self, deviceId: int = 0, profile=None, override=None, exposureSeed: int = None) -> CameraOpenRecord:
        import cv2
        from sys import platform
        profile = requireProfile(profile)
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
        self._pixelFormat = None     # never a stale format from a previous open deciding the conversion
        self._record = CameraOpenRecord(profile=profile.value)
        self._resolution = None
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
        if windows or self._pixelFormat in UNCOMPRESSED_FOURCCS:
            # ⭐ OUR conversion on every OS, not the backend's (SPEC_windows_build.md §6.3): the backend hands over the
            # raw YUY2 bytes and `yuy2ToBgr` converts them with the very call V4L2's backend makes internally — so
            # Linux frames do not change by a single code (proven in W1.4, §11c.11) and Windows gets the same values
            # instead of Media Foundation's. Fixed AT OPEN — toggling CONVERT_RGB on a running stream breaks MSMF
            # (§6.6b) and re-queues the buffer on V4L2. Linux only when the read-back says YUYV: a driver that kept
            # MJPG is converted by the backend as before (Windows refuses it below).
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
                self._record.refusal = refusal
                self.__fillHost(cv2)
                self.release()
                return self._record
        elif not streaming:
            self.__reopenUnforced(cv2, deviceId, apiPreference)
        self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print("CaptureBackend: capture resolution = %dx%d (%s, %s%s)"
              % (self._width, self._height, self._backendName, self._pixelFormat,
                 ", own conversion" if self._rawYuy2 else ""))

        self.__fillHost(cv2)

        if windows:
            self.__openWindowsControls(cv2, profile, override, exposureSeed)
            return self._record
        self.__applyLinuxControls(cv2, profile, override, exposureSeed)
        return self._record

    def __fillHost(self, cv2):
        import platform as platformModule
        self._record.host = {"os": platformModule.system(), "backend": self._backendName,
                             "pixelFormat": self._pixelFormat, "conversion": "own" if self._rawYuy2 else "backend",
                             "opencv": getattr(cv2, "__version__", None)}

    def __linuxControls(self, deviceId):
        factory = type(self).controlsFactory
        if factory is None:
            from sciens.spectracs.logic.application.video.capture.LinuxUvcControls import LinuxUvcControls
            factory = LinuxUvcControls.forDevice
        return factory(deviceId)

    def __applyLinuxControls(self, cv2, profile, override, exposureSeed):
        """CS2: every control the camera offers, resolved and written by LinuxUvcControls, then read back.

        ⭐ ONE WRITER (§5, D6): cv2 sets no control any more — it keeps the stream (format, size, buffer size,
        CONVERT_RGB). Written ONCE, after the final cap exists (after `__reopenUnforced` if it ran), in the order
        auto-mode-before-value, never an inactive control.
        ⛔ Q4: a MEASUREMENT whose read-back does not confirm every requested control is REFUSED — image controls
        too; CALIBRATION and IDLE only warn. A camera whose controls cannot be reached at all proves nothing, and
        is refused the same way."""
        from sciens.spectracs.logic.application.video.capture.LinuxUvcControls import cameraIdentity
        record = self._record
        record.camera = cameraIdentity(self._deviceId)
        self._controls = self.__linuxControls(self._deviceId)
        device = self._controls.describe() if self._controls is not None else CameraDevice()
        resolution = CameraSettingsResolver.resolve(device, profile, override, exposureSeed)
        self._resolution = resolution
        self.__fillResolution(device, resolution)
        if self._controls is None:
            record.failures.append("no V4L2 node for device %s — its controls cannot be set or read" % self._deviceId)
            applied = CameraSettings()
            seed = exposureSeed if exposureSeed is not None else profile.exposureFallback()
            if seed is not None:
                # The one cv2 write left: a camera without a node still gets its exposure, as before CS2.
                self._cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
                self._cap.set(cv2.CAP_PROP_EXPOSURE, seed)
        else:
            applied, failures = self._controls.apply(resolution)
            record.failures.extend(failures)
        record.applied = applied.toJson()
        record.mismatches = [{"control": control.value, "requested": requested, "applied": readBack}
                             for control, requested, readBack in resolution.mismatches(applied)] \
            if self._controls is not None else []
        print("CaptureBackend: camera controls (%s) %s" % (profile.value, " ".join(
            "%s=%s%s" % (control.value, value, "" if resolution.sources.get(control) != "plugin" else "(plugin)")
            for control, value in applied.items())))
        for note in list(resolution.adjusted.values()) + resolution.rejected:
            print("CaptureBackend: ⚠ %s" % note)
        if resolution.autoLoopsOn:
            print("CaptureBackend: ⛔ auto loop on — not a frozen instrument state: %s"
                  % ", ".join(control.value for control in resolution.autoLoopsOn))
        self.__judge(profile, "; ".join(record.failures + ["%(control)s requested %(requested)s, applied %(applied)s"
                                                           % entry for entry in record.mismatches]))

    def __fillResolution(self, device, resolution):
        record = self._record
        record.deviceDefaults = device.defaults().toJson()
        record.deviceRanges = device.toJson()
        wire = resolution.toJson()
        for key in ("requested", "sources", "adjusted", "skipped", "inactive", "rejected", "autoLoopsOn"):
            setattr(record, key, wire[key])

    def __judge(self, profile, problem):
        if not problem:
            return
        if profile.refusesOnMismatch():
            print("CaptureBackend: ⛔ REFUSED to capture on %s - %s (SPEC_camera_settings.md §5, Q4)"
                  % (self._backendName, problem))
            self._record.refusal = problem
            self.release()
        else:
            print("CaptureBackend: ⚠ %s - %s open continues" % (problem, profile.value))

    def __openWindowsControls(self, cv2, profile, override, exposureSeed):
        """Windows until CS3: the W1.6 native path, fed from the profile instead of `whiteBalanceKelvin`.

        ⚠ Exposure still goes through cv2 MSMF in V4L2 numbers, as before — the log₂ converter and the native
        exposure write are CS3 (§3.3a). White balance: CALIBRATION auto; MEASUREMENT and IDLE manual at the
        override's or the profile's temperature. Only MEASUREMENT refuses (IDLE used to run as calibration)."""
        override = CameraSettings.of(override if profile.acceptsPluginOverride() else None)
        exposure = override.get(CameraControl.EXPOSURE, exposureSeed)
        self._cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
        self._cap.set(cv2.CAP_PROP_EXPOSURE, exposure if exposure is not None else -3)
        self._cap.set(cv2.CAP_PROP_GAIN, 0)
        whiteBalanceKelvin = None if profile is CameraProfile.CALIBRATION else int(
            override.get(CameraControl.WHITE_BALANCE_KELVIN,
                         profile.values().get(CameraControl.WHITE_BALANCE_KELVIN, 6500)))
        self._record.requested = {CameraControl.EXPOSURE.value: exposure,
                                  CameraControl.WHITE_BALANCE_AUTO.value: whiteBalanceKelvin is None}
        if whiteBalanceKelvin is not None:
            self._record.requested[CameraControl.WHITE_BALANCE_KELVIN.value] = whiteBalanceKelvin
        self._record.notes.append("Windows: the W1.6 control path until CS3 (exposure via MSMF, not converted)")
        self.__applyNativeControls(whiteBalanceKelvin, refuse=profile.refusesOnMismatch())

    def __applyNativeControls(self, whiteBalanceKelvin, refuse=True):
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
        if problem is not None and not refuse:
            print("CaptureBackend: ⚠ %s - the open continues (not a measurement)" % problem)
        elif problem is not None:
            print("CaptureBackend: ⛔ REFUSED to capture on %s - %s (SPEC_windows_build.md §6.4b)"
                  % (self._backendName, problem))
            self._record.refusal = problem
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
        # Whatever the driver picks unforced, the BACKEND converts it — it may be MJPG, which `yuy2ToBgr` cannot.
        self._rawYuy2 = False
        self._pixelFormat = self.__fourccName(cv2)

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

    def setExposure(self, exposure: int):
        """The live change; returns the APPLIED value (V4L2 units), read back from the camera (§3.3a, D3)."""
        import cv2
        if self._cap is None or exposure is None:
            return None
        if self._controls is not None:
            return self._controls.setExposure(exposure)
        # No V4L2 node (or Windows until CS3): cv2, as before. Re-assert MANUAL mode before the value — many UVC
        # drivers ignore a mid-stream CAP_PROP_EXPOSURE write unless manual mode is (re)asserted.
        self._cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
        self._cap.set(cv2.CAP_PROP_EXPOSURE, exposure)
        return exposure

    def getResolution(self):
        return (self._width, self._height)

    def readCameraState(self) -> CameraSettings:
        """Every control as it reads back now. Linux: LinuxUvcControls' own fd, safe from the GUI thread while the
        worker streams (E6). Windows (until CS3): white balance, gain and backlight from DirectShow — its exposure
        is in log₂ seconds and is reported separately (`readCameraSettings`)."""
        if self._cap is None:
            return CameraSettings()
        if self._controls is not None:
            try:
                return self._controls.read()
            except Exception:
                return CameraSettings()
        native = self.__nativeSettings() if self._nativeControls is not None else {}
        values = {}
        for control, key in ((CameraControl.WHITE_BALANCE_KELVIN, "wbTemperature"), (CameraControl.GAIN, "gain"),
                             (CameraControl.BACKLIGHT, "backlight")):
            if native.get(key) is not None:
                values[control] = native[key]
        if native.get("autoWb") is not None:
            values[CameraControl.WHITE_BALANCE_AUTO] = bool(native["autoWb"])
        return CameraSettings(values)

    def readCameraSettings(self) -> dict:
        # Diagnostic read-back of the live controls for the CAPTURE-SETTINGS line (SPEC_capability_proof.md §7.0.1 —
        # the reference-tilt investigation: is exposure / white balance / gain drifting between reference and
        # sample, run to run?). Each read is guarded so a failure yields a None entry rather than raising.
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

        settings = {
            "backend": self._backendName,
            "pixelFormat": self._pixelFormat,
            "conversion": "own" if self._rawYuy2 else "backend",      # who turned YUYV into BGR (§6.3, W1.4b)
            "profile": self._record.profile if self._record is not None else None,
        }
        if self._controls is not None:
            # ⭐ CS2: from the camera via V4L2, in model words — `autoExposure` reads MANUAL / AUTO, so the old
            # menu-index trap (1 = manual, beside an autoWb whose off is 0) cannot be misread any more.
            state = guarded(self._controls.read, CameraSettings())
            exposureRange = guarded(lambda: self._controls.describe().rangeOf(CameraControl.EXPOSURE), None)
            autoWb = state.get(CameraControl.WHITE_BALANCE_AUTO)
            settings.update({
                "exposureMin": exposureRange.minimum if exposureRange is not None else None,
                "exposureMax": exposureRange.maximum if exposureRange is not None else None,
                "exposure": state.get(CameraControl.EXPOSURE),
                "autoExposure": state.get(CameraControl.AUTO_EXPOSURE),
                "autoExposureMode": None,
                "wbTemperature": state.get(CameraControl.WHITE_BALANCE_KELVIN),
                "autoWb": None if autoWb is None else int(autoWb),
                "gain": state.get(CameraControl.GAIN),
                "backlight": state.get(CameraControl.BACKLIGHT),
                "camera": state.toJson(),
            })
            return settings
        settings.update({
            "exposureMin": None,
            "exposureMax": None,
            "exposure": get(cv2.CAP_PROP_EXPOSURE),
            "autoExposure": get(cv2.CAP_PROP_AUTO_EXPOSURE),
            "autoExposureMode": None,
            "wbTemperature": get(cv2.CAP_PROP_WB_TEMPERATURE),
            "autoWb": get(cv2.CAP_PROP_AUTO_WB),
            "gain": get(cv2.CAP_PROP_GAIN),
            "backlight": get(cv2.CAP_PROP_BACKLIGHT),
        })
        # Windows: the camera's own answer replaces OpenCV's (which cannot read WB and reads exposure back wrong).
        settings.update(guarded(self.__nativeSettings, {}))
        return settings

    def release(self) -> None:
        self._nativeControls = None
        if self._controls is not None:
            try:
                self._controls.close()
            except Exception:
                pass
            self._controls = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None


class AndroidUvcCaptureBackend(CaptureBackend):
    """DEFERRED (P7). The DIY spectrometer is a USB (UVC) camera; Android's Camera2 API does not
    expose external UVC devices, so this must go UVC-over-OTG: UsbManager grants a device fd ->
    libusb (libusb_wrap_sys_device) -> libuvc -> frames. Needs <uses-feature usb.host> +
    UsbManager.requestPermission (NOT android.permission.CAMERA). See spec §6."""

    def open(self, deviceId: int = 0, profile=None, override=None, exposureSeed: int = None) -> CameraOpenRecord:
        raise NotImplementedError("Android UVC-over-OTG capture is deferred (P7) — see spec §6")

    def read(self) -> QImage:
        raise NotImplementedError


class RaspberryPiNetworkCaptureBackend(CaptureBackend):
    """DEFERRED (P7) alternative. If the spectrometer gains a Raspberry-Pi tier, the Pi does the
    capture and the phone becomes a network client (reusing the Pyro/HTTP pattern) — no OTG. The
    choice between this and AndroidUvcCaptureBackend is made when the hardware direction is set."""

    def open(self, deviceId: int = 0, profile=None, override=None, exposureSeed: int = None) -> CameraOpenRecord:
        raise NotImplementedError("RPi-network capture is deferred (P7) — see spec §6")

    def read(self) -> QImage:
        raise NotImplementedError


def getCaptureBackend() -> CaptureBackend:
    """Pick the capture backend for the current platform. Today: desktop is real; Android raises
    on use (capture deferred — the virtual spectrometer is the on-device path for now)."""
    if is_android():
        return AndroidUvcCaptureBackend()
    return DesktopCv2CaptureBackend()
