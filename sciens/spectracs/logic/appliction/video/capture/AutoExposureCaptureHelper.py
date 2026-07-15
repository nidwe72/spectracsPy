import numpy as np

from PySide6.QtCore import QObject, QEventLoop, QTimer

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.appliction.video.DevCaptureVideoThread import DevCaptureVideoThread
from sciens.spectracs.logic.appliction.video.capture.AutoExposureLogicModule import AutoExposureLogicModule
from sciens.spectracs.logic.appliction.video.capture.SensorCaptureIndexResolver import SensorCaptureIndexResolver
from sciens.spectracs.logic.model.util.spectrometerSensor.SpectrometerSensorUtil import SpectrometerSensorUtil
from sciens.spectracs.model.application.applicationStatus.ApplicationStatusSignal import ApplicationStatusSignal


class AutoExposureCaptureHelper(QObject):
    """Reusable auto-exposure PRE-PASS for one-shot burst captures that have no live stream of their own
    (the calibration ROI / peak-detection bursts). It briefly opens a continuous DevCaptureVideoThread,
    runs our bisection auto-exposure over the live frames, releases the camera, and returns the best
    exposure so the caller can open its burst at that value instead of a bloomed default.

    Same algorithm and brightness metric as the dev views (SPEC_dev_measure_bench §P2); factored out so
    the calibration wizard does not duplicate the streaming/pump/brightness plumbing."""

    EXPOSURE_MIN = 1
    EXPOSURE_MAX = 500
    EXPOSURE_FALLBACK = 150
    MAX_PROBES = 8

    def __init__(self):
        super().__init__()
        self.__latestImage = None
        self.__thread = None

    def autoExposeForSensor(self, sensor):
        """Resolve the sensor's capture index + seed exposure and run the pre-pass. Returns
        (deviceIndex, bestExposure); (None, None) for a virtual/absent sensor so the caller skips it."""
        if sensor is None or sensor.isVirtual:
            return (None, None)
        deviceIndex = SensorCaptureIndexResolver().resolveCaptureIndex(sensor)
        seed = self.__seedExposure(sensor)
        best = self.findBestExposure(deviceIndex if deviceIndex is not None else 0, seed)
        return (deviceIndex, best)

    def resolveFixedExposureCapture(self, sensor):
        """Resolve (deviceIndex, storedExposure) WITHOUT running the auto-exposure bisection. The delicate
        wavelength-calibration burst captures at the authored calibration exposure instead of searching:
        this ELP's exposure control is INVERTED and clamps above ~16 (SPEC_capture_quality.md §4.8), which
        violates AutoExposureLogicModule's monotonic-brightness assumption, so the pre-pass walked the burst
        to a wrong level and the mercury green doublet collapsed. A fixed stored exposure (validated by
        diagnostics/calibration_fix_test.py against the cfl_2592 fixture) resolves the doublet reliably.
        Returns (None, None) for a virtual/absent sensor so the caller skips it."""
        if sensor is None or sensor.isVirtual:
            return (None, None)
        deviceIndex = SensorCaptureIndexResolver().resolveCaptureIndex(sensor)
        return (deviceIndex, self.__seedExposure(sensor))

    def findBestExposure(self, deviceIndex, seedExposure):
        thread = DevCaptureVideoThread()
        thread.setIsVirtual(False)
        thread.setDeviceId(deviceIndex)
        thread.setExposure(seedExposure)
        thread.setLiveExposure(seedExposure)
        thread.setFrameCount(0)  # continuous until stop()
        thread.videoThreadSignal.connect(self.__onSignal)
        self.__thread = thread
        thread.start()
        try:
            self.__waitForFirstFrame()
            probe = {"i": 0}

            def measure(exposure):
                probe["i"] += 1
                self.__emitProgress(probe["i"])
                thread.setLiveExposure(exposure)
                self.__pump(350)  # let the UVC stream settle
                return self.__brightness(self.__latestImage)

            best = AutoExposureLogicModule().findExposure(
                measure, self.EXPOSURE_MIN, self.EXPOSURE_MAX, iterations=self.MAX_PROBES)
        finally:
            thread.stop()
            self.__drain()       # release the camera BEFORE the caller opens its burst
            self.__clearStatus()
            self.__thread = None
        return best

    def __seedExposure(self, sensor):
        settings = SpectrometerSensorUtil().getSensorSettings(sensor)
        if settings is not None and settings.calibrationExposure is not None:
            return settings.calibrationExposure
        return self.EXPOSURE_FALLBACK

    def __onSignal(self, event, videoSignal):
        self.__latestImage = videoSignal.image
        event.set()

    def __waitForFirstFrame(self):
        for _ in range(12):
            if self.__latestImage is not None:
                return
            self.__pump(150)

    def __drain(self):
        # After stop() the worker may be blocked in event.wait() for its last frame; pump so it is
        # delivered (our __onSignal sets the event), the run flag is re-checked, and the backend released.
        for _ in range(15):
            if self.__thread.isFinished():
                break
            self.__pump(80)
        self.__thread.wait(2000)

    def __pump(self, milliseconds):
        loop = QEventLoop()
        QTimer.singleShot(milliseconds, loop.quit)
        loop.exec()

    def __brightness(self, image):
        if image is None:
            return 0
        img = image.convertToFormat(image.format())
        width, height = img.width(), img.height()
        ptr = img.constBits()
        arr = np.frombuffer(ptr, np.uint8).reshape(height, img.bytesPerLine())[:, :width * 3].reshape(height, width, 3)
        return float(np.percentile(arr.max(axis=2), 99.9))

    def __emitProgress(self, probeIndex):
        signal = ApplicationStatusSignal()
        signal.isStatusReset = False
        signal.stepsCount = self.MAX_PROBES
        signal.currentStepIndex = min(probeIndex, self.MAX_PROBES)
        signal.text = "Auto-exposing… finding best exposure [%d/%d]" % (signal.currentStepIndex, self.MAX_PROBES)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(signal)

    def __clearStatus(self):
        signal = ApplicationStatusSignal()
        signal.isStatusReset = True
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(signal)
