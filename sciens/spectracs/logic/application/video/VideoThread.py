import os
import time
from typing import Generic, TypeVar

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from sciens.spectracs.logic.application.video.capture.AutoExposureLogicModule import AutoExposureLogicModule
from sciens.spectracs.logic.application.video.capture.CaptureBackend import getCaptureBackend
from sciens.spectracs.model.databaseEntity.AppDataPathUtil import get_app_data_dir
from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule

S = TypeVar('S')

class VideoThread(QThread,Generic[S]):

    qImage: QImage
    _isVirtual:bool=False

    # Auto-exposure runs SYNCHRONOUSLY inside this thread (which owns the backend), mirroring the proven
    # diagnostics drain — no async live-stream / event-loop lag (SPEC_capture_quality.md §14.6).
    autoExposureProgress = Signal(int, int)   # (probeIndex, totalProbes) — drives the status bar
    autoExposureFinished = Signal(int)        # chosen exposure — the view applies it to its slider
    # Fixed drain per probe, safely past the ELP's exposure-change settle (~1.2 s latency then jump; steady by
    # ~1.5 s — measured, SPEC_capture_quality.md §14.6). A shorter/adaptive drain under-reads a big jump (the
    # sensor is still ramping) → the sweep picks an over-bright, clipping exposure. A flat fixed wait can't misfire.
    __AUTO_EXPOSE_SETTLE_MS = 1800

    # Adaptive settle AFTER the sweep picks `best`, before handing back to the burst (SPEC_capture_quality.md
    # §14.8 C2). The per-probe drain above stays a flat wait (measuring mid-sweep must not false-converge on the
    # ramp plateau). But the FINAL settle at `best` is where the reference-burst dim outliers come from: a fixed
    # 1.8 s is too short when the ramp runs long. Drain in chunks and stop once channelPeak stops changing (K
    # reads within tolerance) — but only AFTER a minimum wait PAST the ~1.2 s latency plateau, so we can't
    # false-converge on the flat pre-jump window (the §14.6 trap). Capped so a slow ramp hands back, never hangs.
    __SETTLE_CHUNK_MS = 200
    __SETTLE_MIN_MS = 1500          # never declare "settled" before the latency plateau is past
    __SETTLE_MAX_MS = 4000          # cap total wall-clock (a slow/never-settling ramp hands back the last frame)
    __SETTLE_STABLE_READS = 3       # K consecutive full-frame-brightness reads within tolerance
    __SETTLE_TOLERANCE_FRAC = 0.01  # frame-brightness change (RELATIVE — the mean is small on a mostly-dark frame)
                                    # under this fraction counts as "no longer changing" (§14.8 fix 2)

    # White-balance mode passed to CaptureBackend.open (SPEC_capture_quality.md §14.8, fix 1). None = the camera's
    # AUTO white balance — the DEFAULT, so calibration threads (which key on auto-WB's colour rendering, §13/§14.6)
    # are unchanged. The MEASUREMENT thread (DevCaptureVideoThread) overrides this to the lamp's fixed temperature so
    # its reference/sample bursts are deterministic.
    WHITE_BALANCE_KELVIN = None

    def __init__(self):
        super().__init__()
        self._runFlag = True
        self.qImage = None
        self._autoExposeRequest = None        # (minExposure, maxExposure, target, iterations) or None

        # Real capture is routed through a platform CaptureBackend (owns cv2). _deviceId defaults to 0,
        # preserving today's behaviour; the resolver sets the correct index via setDeviceId (SM2).
        self._backend = None
        self._deviceId = 0
        # Per-camera manual exposure (V4L2 units); None => backend legacy default. Set by the caller from
        # the seeded SpectrometerSensorSettings for the active light-source scenario (spec §9.3).
        self._exposure = None
        # Live exposure override applied mid-stream (a dev-view slider). None => leave as opened.
        self._liveExposure = None
        self._appliedExposure = None

        self._frameCount = 0
        self._currentFrameIndex = 0
        self.spectralJob=None

    def setDeviceId(self, deviceId: int):
        self._deviceId = deviceId

    def readCameraSettings(self) -> dict:
        # Diagnostic snapshot of the live camera controls for the reference-tilt investigation
        # (SPEC_capability_proof.md §7.0.1): the backend's live read-back merged with what THIS thread applied
        # (the AE-landed exposure) and the requested white-balance mode. Safe on virtual/headless (no backend →
        # just the applied values).
        settings = self._backend.readCameraSettings() if self._backend is not None else {}
        settings["appliedExposure"] = self._appliedExposure
        settings["whiteBalanceKelvinRequested"] = self.WHITE_BALANCE_KELVIN
        return settings

    def setExposure(self, exposure: int):
        self._exposure = exposure

    def setLiveExposure(self, exposure: int):
        # Thread-safe enough: a plain int assignment; the capture loop applies it before the next grab.
        self._liveExposure = exposure

    def requestAutoExpose(self, minExposure: int, maxExposure: int, target: int = None, iterations: int = 8):
        """Ask the capture thread to run a synchronous auto-exposure sweep (picked up before the next grab).
        Thread-safe: a single attribute assignment. Progress + result come back via the autoExposure* signals."""
        self._autoExposeRequest = (minExposure, maxExposure, target, iterations)

    def __runAutoExposeSync(self):
        # Synchronous sweep INSIDE the capture thread: set exposure -> drain frames for a wall-clock window so the
        # UVC change actually takes effect and stale frames flush -> measure qGray peak. This is exactly what the
        # diagnostics probe does (and why its curve is clean), with the direction-agnostic AutoExposureLogicModule
        # choosing the winner. No Qt event loop, no async live-stream reads => none of the stale-frame lag.
        minExposure, maxExposure, target, iterations = self._autoExposeRequest
        if target is None:
            target = AutoExposureLogicModule.DEFAULT_TARGET
        probe = {"i": 0}

        def measure(exposure):
            probe["i"] += 1
            self.autoExposureProgress.emit(probe["i"], iterations)
            self._backend.setExposure(exposure)
            self._appliedExposure = exposure
            # Fixed drain past the settle so a big jump has fully ramped before we measure (each probe self-settles;
            # no separate warm-up needed).
            frame = self.__drainSync(self.__AUTO_EXPOSE_SETTLE_MS)
            # Paint the just-drained frame so the preview shows the exposure ramping instead of freezing for the
            # whole sweep (the frame is already read — measurement still uses these same drained frames).
            self.qImage = frame
            self._emitPreview()
            return AutoExposureLogicModule.channelPeak(frame)

        best = AutoExposureLogicModule().findExposure(measure, minExposure, maxExposure, target, iterations)
        self._backend.setExposure(best)
        self._appliedExposure = best
        self._liveExposure = best     # keep the normal loop from re-applying a stale slider value
        # Settle at the CHOSEN exposure before we hand back to the burst: `best` is a fresh change from the last
        # probe, and the ELP takes ~1.2-1.5 s to ramp — without this the first burst frames would be captured
        # mid-ramp (the reference-only outliers, SPEC_capture_quality.md §14.6/§14.8). Sample capture reuses an
        # already-settled exposure, which is why it never showed them. ADAPTIVE now (§14.8 C2): drain until
        # channelPeak stabilises (past the latency plateau), so a long ramp is fully covered, not cut off at 1.8 s.
        self.qImage = self.__settleUntilStable()
        self._emitPreview()
        self.autoExposureFinished.emit(int(best))

    def __settleUntilStable(self):
        # Adaptive replacement for the fixed final drain (SPEC_capture_quality.md §14.8 C2). Drain short chunks and
        # measure channelPeak; stop once K consecutive reads are within tolerance AND the minimum wait (past the
        # ramp's latency plateau) has elapsed; hard-cap the total. Returns the last drained frame.
        start = time.monotonic()
        last = None
        previous = None
        stable = 0
        while True:
            frame = self.__drainSync(self.__SETTLE_CHUNK_MS)
            if frame is not None:
                last = frame
            # Fix 2 (§14.8): settle on FULL-FRAME brightness, not channelPeak. channelPeak (the p99.9 peak)
            # saturates/plateaus at the AE target while the mid/dim regions are still ramping → it can read
            # "stable" too early; a frame MEAN stays linear and moves until the whole frame settles.
            brightness = AutoExposureLogicModule.frameBrightness(frame)
            if previous is not None and abs(brightness - previous) <= self.__SETTLE_TOLERANCE_FRAC * max(previous, 1.0):
                stable += 1
            else:
                stable = 0
            previous = brightness
            elapsedMs = (time.monotonic() - start) * 1000.0
            if elapsedMs >= self.__SETTLE_MIN_MS and stable >= self.__SETTLE_STABLE_READS:
                break
            if elapsedMs >= self.__SETTLE_MAX_MS:
                break
        return last

    def __drainSync(self, milliseconds):
        # Actively read+discard frames for `milliseconds` of wall-clock (mirrors diagnostics drain): buffered reads
        # return near-instantly, so draining over real time lets the exposure change turn over. Returns the last.
        end = time.monotonic() + milliseconds / 1000.0
        last = self._backend.read()
        while time.monotonic() < end:
            frame = self._backend.read()
            if frame is not None:
                last = frame
        return last


    def setFrameCount(self, spectraCount: int):
        self._frameCount = spectraCount

    def getFrameCount(self):
        return self._frameCount

    def _setCurrentFrameIndex(self, currentCount: int):
        self._currentFrameIndex = currentCount

    def _getCurrentFrameIndex(self):
        return self._currentFrameIndex

    def setIsVirtual(self, isVirtual: int):
        self._isVirtual = isVirtual

    def getIsVirtual(self):
        return self._isVirtual


    def run(self):

        self._runFlag=True

        self.onStart()

        # Virtual mode serves frames from VirtualSpectrometerSettings and must never touch a
        # physical camera. This is also required on Android, where there is no usable capture device
        # (getCaptureBackend() there raises on open). Only open a backend for a real sensor.
        if not self.getIsVirtual():
            self._backend = getCaptureBackend()
            self._backend.open(self._deviceId, self._exposure, self.WHITE_BALANCE_KELVIN)
            self._appliedExposure = self._exposure

            # Warm-up: the first frames after open can be empty while the UVC stream settles; discard a
            # few so the first delivered frame is real (spec §3.5 / §0). read() never raises → None ok.
            for _ in range(6):
                if self._backend.read() is not None:
                    break

        while self._runFlag:

            # A pending auto-exposure request runs synchronously here (backend is single-threaded and ours),
            # pausing normal streaming — no display/event-loop lag while sweeping.
            if self._backend is not None and self._autoExposeRequest is not None:
                self.__runAutoExposeSync()
                self._autoExposeRequest = None
                continue

            # Apply a pending live-exposure change (dev-view slider) before grabbing the next frame.
            if self._backend is not None and self._liveExposure is not None \
                    and self._liveExposure != self._appliedExposure:
                self._backend.setExposure(self._liveExposure)
                self._appliedExposure = self._liveExposure

            self.beforeCapture()
            self.__captureFrame()


        self._setCurrentFrameIndex(0)
        if self._backend is not None:
            self._backend.release()
            self._backend = None

    def __captureFrame(self):

        isVirtual = self.getIsVirtual()

        doSavePhysicallyCapturedImages = ApplicationContextLogicModule().getApplicationSettings().getVirtualSpectrometerSettings().getDoSavePhysicallyCapturedImages()

        temporaryDirectory=None
        if doSavePhysicallyCapturedImages:
            temporaryDirectory = get_app_data_dir()+'/tmpImages'

            if not os.path.isdir(temporaryDirectory):
                os.makedirs(temporaryDirectory)

        if isVirtual:
            self.__captureVirtualFrame()
        else:
            self.__capturePhysicalFrame(temporaryDirectory)

    def __capturePhysicalFrame(self,temporaryDirectory:str):
        qImage = self._backend.read() if self._backend is not None else None
        if qImage is not None:
            # backend.read() already yields a detached RGB888 QImage (freed-buffer safe).
            self.qImage = qImage

            if temporaryDirectory is not None:
                self.qImage.save(temporaryDirectory+'/test.png','PNG')

        # On a failed/empty read qImage stays as the last good frame; always advance the burst.
        self.afterCapture()

    def __captureVirtualFrame(self):

        self.qImage=ApplicationContextLogicModule().getApplicationSettings().getVirtualSpectrometerSettings().getVirtualCameraImage()
        self.afterCapture()


    def stop(self):
        self._runFlag = False
        self._setCurrentFrameIndex(0)

    def beforeCapture(self):
        pass

    def afterCapture(self):
        frameCount = self.getFrameCount()
        if frameCount > 0:
            self._setCurrentFrameIndex(self._getCurrentFrameIndex() + 1)
            currentCount = self._getCurrentFrameIndex()
            if currentCount == frameCount-1:
                self._runFlag = False

    def createSignal(self)->S:
        return None

    def _emitPreview(self):
        # Live-preview hook for the auto-exposure sweep. Subclasses that drive a visible stream override this to
        # emit their view signal with self.qImage, FIRE-AND-FORGET (no one-frame backpressure), so the synchronous
        # sweep is never blocked on the render. Default no-op: virtual/headless threads have nothing to paint.
        return None

    def onStart(self):
        return None






