from PySide6.QtCore import Qt, QEventLoop, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox,
                               QSlider, QCheckBox, QTabWidget, QSizePolicy)

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.application.style.Metrics import Metrics
from sciens.spectracs.logic.application.video.DevCaptureVideoThread import DevCaptureVideoThread
from sciens.spectracs.logic.application.video.capture.SensorCaptureIndexResolver import SensorCaptureIndexResolver
from sciens.spectracs.logic.spectral.acquisition.ExtendedRoiLogicModule import ExtendedRoiLogicModule
from sciens.spectracs.logic.model.util.spectrometerSensor.SpectrometerSensorUtil import SpectrometerSensorUtil
from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModule import MeanSpectrumLogicModule
from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModuleParameters import MeanSpectrumLogicModuleParameters
from sciens.spectracs.model.application.applicationStatus.ApplicationStatusSignal import ApplicationStatusSignal
from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.plugin_sdk.roles import REFERENCE, SAMPLE
from sciens.spectracs.view.settings.development.DevCaptureVideoViewModule import DevCaptureVideoViewModule
from sciens.spectracs.view.spectral.workflow.SpectrumPlotWidget import SpectrumPlotWidget


# A capture thread can block inside a cv2 call (VideoCapture(open) on a still-busy device, or a slow high-res
# read) and outlive its CapturePanel. If it is garbage-collected while still running, PySide aborts
# ("QThread: Destroyed while thread is still running"); if it stays connected, its next queued emit lands on a
# deleted panel slot and segfaults in Qt's posted-event delivery. So on stop we DISCONNECT it from the panel and,
# if it did not finish promptly, park it here — a live reference — until the cv2 call finally returns.
_STUCK_CAPTURE_THREADS = []


def _retireStuckThread(thread):
    _STUCK_CAPTURE_THREADS.append(thread)
    thread.finished.connect(
        lambda: _STUCK_CAPTURE_THREADS.remove(thread) if thread in _STUCK_CAPTURE_THREADS else None)


class CapturePanel(QWidget):
    """Shared live-capture acquisition panel (SPEC_plugin_driven_convergence.md §9, S2a — Option A).

    The ONE place the real-camera acquisition UI + machinery lives, so BOTH hosts — the dev measurement bench
    and (on a real device) the end-user wizard — use it instead of the bench-private copy. It mirrors the
    bench's proven "Option A" model: Reference/Sample role step-tabs with ONE live-video widget + ONE spectrum
    plot reparented into the active step's page (never two camera streams). The numeric burst runs through the
    HEADLESS engine seam — `engine.captureAcquisitionStep(step, frameProvider, frames, onFrame)` (§9.1) — so
    this panel owns only the Qt/camera side; the extraction maths stays in the engine.

    Host-generic. Constructed with the ordered role-bearing acquisition `steps`, the `engine`, and callbacks:
      onCaptured(step)   — a role finished capturing (host refreshes nav + guidance)
      onRoleChanged()    — the active role-tab changed (host re-derives the amber cue)
      onCaptureFailed()  — no frames delivered (host shows its own dialog)
    It exposes `getCaptureButton()` / `getRoleTabs()` so the host can paint acquisition-guidance cues on them
    (D4 — highlight targets stay host-side). It owns NO navigation, guidance derivation, or failure dialog.

    NOTE: the live-camera behaviour is rig-verified (golden-frame + live smoke, §9.5) — it cannot run offscreen.
    """

    __EXPOSURE_MIN = 1
    __EXPOSURE_MAX = 500
    __EXPOSURE_FALLBACK = 150
    __AUTO_EXPOSE_MAX_PROBES = 8
    __FRAME_CHOICES = ["10", "20", "50"]
    __DEFAULT_FRAMES = "20"
    __NM_MIN = 400.0
    __NM_MAX = 700.0
    __FRAME_COLOR = "#777777"   # per-frame traces (gray)
    __MEAN_COLOR = "#2ECC71"    # mean spectrum (green)
    __IMAGE_TAB = 0
    __SPECTRUM_TAB = 1

    def __init__(self, steps, engine, onCaptured=None, onRoleChanged=None, onCaptureFailed=None):
        super().__init__()
        self.__steps = list(steps)          # ordered role-bearing ACQUISITION steps
        self.__engine = engine
        self.__onCaptured = onCaptured or (lambda step: None)
        self.__onRoleChanged = onRoleChanged or (lambda: None)
        self.__onCaptureFailed = onCaptureFailed or (lambda: None)

        self.__resolver = SensorCaptureIndexResolver()
        self.__sensor = None
        self.__resolvedIndex = None
        self.__videoThread = None
        self.__latestImage = None
        self.__autoExposing = False
        self.__capturing = False
        self.__lockedExposure = None
        self.__savedRoiX = None
        self.__captureTotal = 1
        self.__previewRoiWidth = None
        self.__representativeFrames = {}    # role -> QImage (preview-only middle frame)
        self.__activeStep = self.__steps[0] if self.__steps else None

        self.__build()
        self.__resolveCamera()
        self.__applyControlVisibility()
        self.__applyLabels()
        self.__updateControls()

    # --- public API for the host ---

    def getCaptureButton(self):
        return self.__captureButton

    def getRoleTabs(self):
        return self.__roleTabs

    def getActiveStep(self):
        return self.__activeStep

    def isCameraReady(self):
        return self.__resolvedIndex is not None

    def getRepresentativeFrame(self, role):
        return self.__representativeFrames.get(role)

    def startStream(self):
        self.__startStream()

    def stopStream(self):
        self.__stopStream()

    def plotActiveRole(self):
        self.__plotActiveRole()

    # --- build ---

    def __build(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, Metrics.S, 0, 0)
        layout.setSpacing(Metrics.S)
        self.setLayout(layout)

        self.__videoViewModule = DevCaptureVideoViewModule()
        self.__videoViewModule.setObjectName("CapturePanel.videoViewModule")
        self.__videoViewModule.setStyleSheet("BaseVideoViewModule { border: none; }")
        self.__spectrumPlot = SpectrumPlotWidget()
        self.__innerTabs = QTabWidget()
        self.__innerTabs.setObjectName("CapturePanel.innerTabs")
        self.__innerTabs.addTab(self.__videoViewModule, "Captured image")   # __IMAGE_TAB
        self.__innerTabs.addTab(self.__spectrumPlot, "Spectrum")            # __SPECTRUM_TAB

        controls = QWidget()
        controls.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        controlsLayout = QGridLayout()
        controlsLayout.setContentsMargins(0, 0, 0, 0)
        controlsLayout.setSpacing(Metrics.S)
        controls.setLayout(controlsLayout)

        self.__framesComboBox = QComboBox()
        # Seed the frame count from the PLUGIN-declared burst (step.getFrames()), not a hardcoded default —
        # the capture reads this combo, so this is what makes a plugin's FRAMES actually take effect for real
        # capture (e.g. the dev bench's 150). The dropdown (when the plugin shows it) still overrides.
        declaredFrames = self.__steps[0].getFrames() if self.__steps else None
        default = str(declaredFrames) if declaredFrames else self.__DEFAULT_FRAMES
        choices = sorted(set(self.__FRAME_CHOICES + [default]), key=int)
        self.__framesComboBox.addItems(choices)
        self.__framesComboBox.setCurrentText(default)
        self.__framesControl = self.__labeled("Frames", self.__framesComboBox)
        controlsLayout.addWidget(self.__framesControl, 0, 0, 1, 2)

        self.__exposureSlider = QSlider(Qt.Orientation.Horizontal)
        self.__exposureSlider.setMinimum(self.__EXPOSURE_MIN)
        self.__exposureSlider.setMaximum(self.__EXPOSURE_MAX)
        self.__exposureSlider.valueChanged.connect(self.__onExposureChanged)
        self.__exposureLabel = QLabel("")
        self.__autoExposureCheckBox = QCheckBox("auto-exposure")
        self.__autoExposureCheckBox.setChecked(True)
        self.__autoExposureCheckBox.toggled.connect(self.__updateControls)
        exposureRow = QWidget()
        exposureRowLayout = QGridLayout()
        exposureRowLayout.setContentsMargins(0, 0, 0, 0)
        exposureRowLayout.setSpacing(Metrics.S)
        exposureRow.setLayout(exposureRowLayout)
        exposureRowLayout.addWidget(self.__exposureSlider, 0, 0, 1, 1)
        exposureRowLayout.addWidget(self.__exposureLabel, 0, 1, 1, 1)
        exposureRowLayout.addWidget(self.__autoExposureCheckBox, 1, 0, 1, 2)
        exposureRowLayout.setColumnStretch(0, 85)
        exposureRowLayout.setColumnStretch(1, 15)
        self.__exposureControl = self.__labeled("Exposure", exposureRow)
        controlsLayout.addWidget(self.__exposureControl, 1, 0, 1, 2)

        self.__captureButton = QPushButton("Capture reference")
        self.__captureButton.setObjectName("CapturePanel.captureButton")
        self.__captureButton.clicked.connect(self.__onClickedCapture)
        controlsLayout.addWidget(self.__captureButton, 2, 0, 1, 2)

        self.__stepContent = QWidget()
        stepContentLayout = QVBoxLayout()
        stepContentLayout.setContentsMargins(0, 0, 0, 0)
        stepContentLayout.setSpacing(Metrics.S)
        self.__stepContent.setLayout(stepContentLayout)
        stepContentLayout.addWidget(self.__innerTabs)
        stepContentLayout.addWidget(controls)

        self.__roleTabs = QTabWidget()
        self.__roleTabs.setObjectName("CapturePanel.roleTabs")
        self.__pages = []
        for step in self.__steps:
            page = self.__stepPage()
            self.__pages.append(page)
            self.__roleTabs.addTab(page, step.getLabel() or (step.getRole() or ""))
        self.__roleTabs.tabBar().setDrawBase(False)
        if self.__pages:
            self.__pages[0].layout().addWidget(self.__stepContent)  # start on the first step
        self.__syncExposureToSensor()
        self.__roleTabs.currentChanged.connect(self.__onRoleTabChanged)
        layout.addWidget(self.__roleTabs)

    def __labeled(self, text, component):
        # A minimal label-above-component holder (the panel is a plain QWidget, so it has no PageWidget
        # createLabeledComponent). Visual detail is rig-tunable.
        holder = QWidget()
        holderLayout = QVBoxLayout()
        holderLayout.setContentsMargins(0, 0, 0, 0)
        holderLayout.setSpacing(2)
        holder.setLayout(holderLayout)
        holderLayout.addWidget(QLabel(text))
        holderLayout.addWidget(component)
        return holder

    def __stepPage(self):
        page = QWidget()
        pageLayout = QVBoxLayout()
        pageLayout.setContentsMargins(0, Metrics.S, 0, 0)
        pageLayout.setSpacing(Metrics.S)
        page.setLayout(pageLayout)
        return page

    def __attachStepContent(self, index):
        if not (0 <= index < len(self.__pages)):
            return
        page = self.__pages[index]
        if self.__stepContent is not None and self.__stepContent.parentWidget() is not page:
            page.layout().addWidget(self.__stepContent)

    def __stepForRole(self, role):
        for step in self.__steps:
            if step.getRole() == role:
                return step
        return None

    # --- role / labels ---

    def __onRoleTabChanged(self):
        index = self.__roleTabs.currentIndex()
        self.__attachStepContent(index)
        if 0 <= index < len(self.__steps):
            self.__activeStep = self.__steps[index]
        role = self.__activeStep.getRole() if self.__activeStep is not None else None
        if role == SAMPLE and self.__lockedExposure is not None:
            self.__exposureSlider.blockSignals(True)
            self.__exposureSlider.setValue(self.__lockedExposure)
            self.__exposureSlider.blockSignals(False)
            self.__updateExposureLabel()
            if self.__videoThread is not None:
                self.__videoThread.setLiveExposure(self.__lockedExposure)
        self.__captureButton.setText(self.__captureLabelForStep(self.__activeStep))
        self.__plotActiveRole()
        self.__updateControls()
        self.__onRoleChanged()

    def __captureLabelForStep(self, step):
        view = step.getView() if step is not None else None
        label = getattr(view, "captureLabel", None) if view is not None else None
        if label:
            return label
        role = step.getRole() if step is not None else None
        return "Capture reference" if role == REFERENCE else "Capture sample"

    def __applyLabels(self):
        for index, step in enumerate(self.__steps):
            if step.getLabel():
                self.__roleTabs.setTabText(index, step.getLabel())
        if self.__activeStep is not None:
            self.__captureButton.setText(self.__captureLabelForStep(self.__activeStep))

    def __applyControlVisibility(self):
        # The plugin's CaptureView decides whether the dev capture chrome shows (both steps carry the same flags).
        view = self.__steps[0].getView() if self.__steps else None
        self.__framesControl.setVisible(bool(getattr(view, "showFramesControl", False)))
        self.__exposureControl.setVisible(bool(getattr(view, "showExposureControls", False)))

    # --- camera resolution ---

    def __resolveCamera(self):
        profile = ApplicationContextLogicModule().getApplicationSettings().getSpectrometerProfile()
        try:
            self.__sensor = profile.spectrometer.spectrometerSensor
        except AttributeError:
            self.__sensor = None
        self.__resolvedIndex = self.__resolver.resolveCaptureIndex(self.__sensor)

    def __calibration(self):
        profile = ApplicationContextLogicModule().getApplicationSettings().getSpectrometerProfile()
        return getattr(profile, "spectrometerCalibrationProfile", None) if profile is not None else None

    # --- controls / exposure ---

    def __onExposureChanged(self):
        self.__updateExposureLabel()
        if self.__videoThread is not None:
            self.__videoThread.setLiveExposure(self.__exposureSlider.value())

    def __updateExposureLabel(self):
        if self.__exposureLabel is not None:
            self.__exposureLabel.setText(str(self.__exposureSlider.value()))

    def __syncExposureToSensor(self):
        settings = SpectrometerSensorUtil().getSensorSettings(self.__sensor) if self.__sensor is not None else None
        value = settings.calibrationExposure if settings is not None and settings.calibrationExposure is not None \
            else self.__EXPOSURE_FALLBACK
        value = max(self.__EXPOSURE_MIN, min(self.__EXPOSURE_MAX, value))
        self.__exposureSlider.blockSignals(True)
        self.__exposureSlider.setValue(value)
        self.__exposureSlider.blockSignals(False)
        self.__updateExposureLabel()

    def __updateControls(self):
        connected = self.__resolvedIndex is not None
        streaming = self.__videoThread is not None
        busy = self.__autoExposing or self.__capturing   # capture (auto-expose + burst) keeps controls disabled (C3a)
        role = self.__activeStep.getRole() if self.__activeStep is not None else None
        sampleLocked = role == SAMPLE and self.__lockedExposure is not None
        autoOn = self.__autoExposureCheckBox is not None and self.__autoExposureCheckBox.isChecked()
        self.__captureButton.setEnabled(connected and streaming and not busy)
        if self.__autoExposureCheckBox is not None:
            self.__autoExposureCheckBox.setEnabled(not busy and not sampleLocked)
        if self.__exposureSlider is not None:
            self.__exposureSlider.setEnabled(streaming and not busy and not autoOn and not sampleLocked)
        if self.__roleTabs is not None:
            self.__roleTabs.tabBar().setEnabled(not busy)
        if self.__framesComboBox is not None:
            self.__framesComboBox.setEnabled(not busy)

    # --- streaming ---

    def __startStream(self):
        if self.__videoThread is not None or self.__resolvedIndex is None:
            self.__updateControls()
            return
        self.__latestImage = None
        thread = DevCaptureVideoThread()
        thread.setIsVirtual(False)
        thread.setDeviceId(self.__resolvedIndex)
        role = self.__activeStep.getRole() if self.__activeStep is not None else None
        exposure = self.__lockedExposure if (role == SAMPLE and self.__lockedExposure is not None) \
            else self.__exposureSlider.value()
        thread.setExposure(exposure)
        thread.setLiveExposure(exposure)
        thread.setFrameCount(0)  # continuous until stop()
        thread.videoThreadSignal.connect(self.handleVideoThreadSignal)
        thread.autoExposureProgress.connect(self.__onAutoExposeProgress)
        thread.autoExposureFinished.connect(self.__onAutoExposeFinished)
        thread.finished.connect(self.__onThreadFinished)
        self.__videoThread = thread
        thread.start()
        self.__updateControls()

    def __stopStream(self):
        # Stop the live capture safely. Two failure modes to avoid (both seen in the field):
        #   1) A leaked worker (blocked in a cv2 call) later emits a queued signal into THIS panel after it has
        #      been discarded on a plugin switch -> Qt delivers a posted event to a deleted QObject -> SEGFAULT.
        #      Fix: DISCONNECT every worker->panel signal here, before anything can delete the panel.
        #   2) The QThread is garbage-collected while still running -> abort. Fix: never drop the only reference to
        #      a running thread; park a stuck one in _STUCK_CAPTURE_THREADS until it finishes.
        # The render backpressure is interruptible by stop() (DevCaptureVideoThread), so a worker that is NOT stuck
        # in cv2 exits within a poll tick and wait() returns fast; that is the normal path and it frees the camera
        # before any reopen (the plugin-switch reopen race).
        thread = self.__videoThread
        self.__videoThread = None
        if thread is not None:
            for signal, slot in (
                    (thread.videoThreadSignal, self.handleVideoThreadSignal),
                    (thread.autoExposureProgress, self.__onAutoExposeProgress),
                    (thread.autoExposureFinished, self.__onAutoExposeFinished),
                    (thread.finished, self.__onThreadFinished)):
                try:
                    signal.disconnect(slot)
                except (TypeError, RuntimeError):
                    pass
            thread.stop()
            if not thread.wait(1500):
                _retireStuckThread(thread)   # blocked in a cv2 call — keep it alive so PySide can't GC it running
        self.__updateControls()

    def __onThreadFinished(self):
        self.__videoThread = None
        self.__updateControls()

    def handleVideoThreadSignal(self, event, videoSignal):
        # Preview frames (emitted DURING the auto-exposure sweep so the view isn't frozen) paint but must NOT become
        # __latestImage: the reference-burst drop logic (§14.6) assumes nothing lands here during the sweep, so if a
        # preview frame did, the drop would consume it and the burst would start on the mid-ramp outlier.
        if not videoSignal.isPreview:
            self.__latestImage = videoSignal.image
        if self.__videoViewModule is not None:
            self.__videoViewModule.handleVideoThreadSignal(videoSignal)
            width = videoSignal.image.width() if videoSignal.image is not None else None
            if width is not None and width != self.__previewRoiWidth:
                self.__previewRoiWidth = width
                self.__applyPreviewRoiOverlay(width)
        event.set()

    def __applyPreviewRoiOverlay(self, imageWidth):
        calibration = self.__calibration()
        nmMin, nmMax = self.__captureWindow()  # overlay reflects the plugin's clamped window (§9 M1), not 400–700
        extended = ExtendedRoiLogicModule().extendedRoi(calibration, imageWidth, nmMin, nmMax) \
            if calibration is not None else None
        if extended is None:
            self.__videoViewModule.clearRoi()
        else:
            self.__videoViewModule.setRoi(*extended)

    # --- auto-exposure ---

    def __runAutoExposure(self):
        # Hand the sweep to the capture thread, which runs it SYNCHRONOUSLY on the backend (set exposure -> drain
        # -> measure qGray peak) — no async live-stream reads, so no stale-frame lag (SPEC_capture_quality.md
        # §14.6). Progress + result come back on the thread's autoExposure* signals.
        if self.__videoThread is None or self.__autoExposing:
            return
        self.__autoExposing = True
        # Drop the last streamed frame: the thread emits NOTHING during the ~15 s sweep, so __latestImage would
        # otherwise stay stale (a pre-sweep, old-exposure frame) and the reference burst would grab it as its first
        # frame(s) — the reference-only outliers (SPEC_capture_quality.md §14.6). Nulling it forces
        # __waitForFirstFrame to wait for a genuinely fresh post-AE frame before the burst starts.
        self.__latestImage = None
        if self.__innerTabs is not None:
            self.__innerTabs.setCurrentIndex(self.__IMAGE_TAB)
        self.__updateControls()
        self.__videoThread.requestAutoExpose(
            self.__EXPOSURE_MIN, self.__EXPOSURE_MAX, iterations=self.__AUTO_EXPOSE_MAX_PROBES)

    def __onAutoExposeProgress(self, probeIndex, totalProbes):
        signal = ApplicationStatusSignal()
        signal.isStatusReset = False
        signal.stepsCount = totalProbes
        signal.currentStepIndex = min(probeIndex, totalProbes)
        signal.text = "Auto-exposing… finding best exposure [%d/%d]" % (signal.currentStepIndex, totalProbes)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(signal)

    def __onAutoExposeFinished(self, exposure):
        self.__exposureSlider.setValue(exposure)  # thread already applied it; this updates the UI + label
        self.__autoExposing = False
        self.__clearStatus()
        self.__updateControls()

    def __waitForAutoExposure(self):
        # The capture sequence (auto-expose THEN burst) needs the async in-thread sweep to FINISH before it grabs
        # the reference frames. Spin the event loop until the autoExposureFinished signal has cleared __autoExposing
        # (bounded so a stuck sweep can't hang the capture). We're only WAITING for the result here — the brightness
        # measuring happens synchronously in the thread, so there is no stale-frame lag.
        waited = 0
        while self.__autoExposing and waited < 15000:
            self.__pumpFrames(100)
            waited += 100

    def __waitForFirstFrame(self):
        for _ in range(12):
            if self.__latestImage is not None:
                return
            self.__pumpFrames(150)

    def __pumpFrames(self, milliseconds):
        loop = QEventLoop()
        QTimer.singleShot(milliseconds, loop.quit)
        loop.exec()

    # --- capture (routes the burst through the headless engine seam) ---

    def __onClickedCapture(self):
        if self.__resolvedIndex is None or self.__videoThread is None or self.__autoExposing:
            return
        step = self.__activeStep
        if step is None:
            return
        # SPEC_doc_automation §18.3 (C3a): mark the WHOLE capture busy — auto-exposure AND the multi-frame
        # burst — so the capture button (and role tabs / frames combo, via __updateControls) stay disabled
        # for its entire duration. Previously only auto-exposure set busy, so the button re-enabled mid-burst
        # (and for the SAMPLE role, which never auto-exposes, it was never disabled at all). set/reset in
        # try/finally so the capture-failed early return below can't leave the button stuck disabled.
        self.__capturing = True
        self.__updateControls()
        try:
            role = step.getRole()
            if role == REFERENCE and self.__autoExposureCheckBox.isChecked():
                self.__runAutoExposure()      # async: hands the sweep to the capture thread
                self.__waitForAutoExposure()  # ...block until it finishes before grabbing the reference burst
                # The FIRST frame the stream delivers after the sweep resumes is a one-off outlier on this ELP
                # (its recurring first-frame quirk — §14.6). Wait for it, then drop it, so the reference burst
                # starts on the second, clean frame. Sample never sweeps, so its warm stream never shows this.
                self.__waitForFirstFrame()
                self.__latestImage = None

            frameCount = int(self.__framesComboBox.currentText())
            self.__innerTabs.setCurrentIndex(self.__SPECTRUM_TAB)
            self.__beginCaptureProgress(frameCount)
            self.__waitForFirstFrame()

            images = []
            state = {"roiApplied": False}

            def provider():
                self.__pumpFrames(120)  # let the stream advance a frame
                if self.__latestImage is None:
                    return None
                image = self.__latestImage.copy()  # detach from the live numpy buffer
                if not state["roiApplied"]:
                    self.__applyExtendedRoi(image.width())  # widen to the analysis window before the FIRST extraction
                    state["roiApplied"] = True
                images.append(image)
                return image

            def onFrame(spectrum, index, total):
                self.__plotRoleSpectrum(role, spectrum)     # live: frame traces so far + running mean
                self.__stepCaptureProgress(index + 1)

            spectrum = self.__engine.captureAcquisitionStep(
                step, frameProvider=provider, frames=frameCount, onFrame=onFrame)
            self.__endCaptureProgress()

            if spectrum is None or not images:
                self.__onCaptureFailed()
                return

            self.__representativeFrames[role] = images[len(images) // 2]

            if role == REFERENCE:
                self.__lockedExposure = self.__exposureSlider.value()
                # A fresh reference re-locks exposure; an earlier sample no longer matches — drop it.
                sampleStep = self.__stepForRole(SAMPLE)
                if sampleStep is not None and sampleStep is not step and sampleStep.getContainer() is not None:
                    sampleStep.setContainer(None)
                    self.__representativeFrames.pop(SAMPLE, None)

            self.__plotActiveRole()
            self.__innerTabs.setCurrentIndex(self.__SPECTRUM_TAB)
            self.__onCaptured(step)
        finally:
            self.__capturing = False
            self.__updateControls()

    # --- plotting ---

    def __plotActiveRole(self):
        step = self.__activeStep
        role = step.getRole() if step is not None else None
        self.__plotRoleSpectrum(role, self.__spectrumForStep(step))

    def __spectrumForStep(self, step):
        if step is None:
            return None
        container = step.getContainer()
        if container is None:
            return None
        return container.getSpectra().get(step.getRole())

    def __plotRoleSpectrum(self, role, spectrum):
        plot = self.__spectrumPlot
        if plot is None:
            return
        title = "Reference" if role == REFERENCE else "Sample"
        if spectrum is None:
            plot.plotSpectrum(None, title=title)
            return
        frames = spectrum.getCapturedValuesByNanometers()
        plot.plotSpectrum(None, title=title)  # clear + set title
        for values in frames:
            frameSpectrum = Spectrum()
            frameSpectrum.setValuesByNanometers(dict(values))
            plot.addTrace(frameSpectrum, color=self.__FRAME_COLOR, width=1)
        plot.addTrace(self.__meanSpectrum(spectrum), color=self.__MEAN_COLOR, width=2)

    def __meanSpectrum(self, spectrum):
        parameters = MeanSpectrumLogicModuleParameters()
        parameters.setSpectrum(spectrum)
        return MeanSpectrumLogicModule().meanSpectrum(parameters).getSpectrum()

    # --- capture progress (to the app status bar) ---

    def __beginCaptureProgress(self, total):
        self.__captureTotal = max(1, total)

    def __stepCaptureProgress(self, value):
        role = self.__activeStep.getRole() if self.__activeStep is not None else None
        roleText = "reference" if role == REFERENCE else "sample"
        signal = ApplicationStatusSignal()
        signal.isStatusReset = False
        signal.stepsCount = self.__captureTotal
        signal.currentStepIndex = min(value, self.__captureTotal)
        signal.text = "Capturing %s frame %d / %d" % (roleText, signal.currentStepIndex, self.__captureTotal)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(signal)

    def __endCaptureProgress(self):
        self.__clearStatus()

    def __clearStatus(self):
        signal = ApplicationStatusSignal()
        signal.isStatusReset = True
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(signal)

    # --- ROI widen / restore (idempotent per session) ---

    def __captureWindow(self):
        # SPEC_capture_quality.md §9 (M1): the plugin's declared usable wavelength window (from the active step's
        # CaptureView), or the legacy 400–700 default when the plugin declares none. Same window on every step
        # (Reference/Sample) — the plugin sets one constant on all of them — so T=S/R divides matching domains.
        view = self.__activeStep.getView() if self.__activeStep is not None else None
        nmMin = getattr(view, "wavelengthMinNm", None)
        nmMax = getattr(view, "wavelengthMaxNm", None)
        return (nmMin if nmMin is not None else self.__NM_MIN,
                nmMax if nmMax is not None else self.__NM_MAX)

    def __applyExtendedRoi(self, imageWidth):
        if self.__savedRoiX is not None:
            return
        calibration = self.__calibration()
        if calibration is None:
            return
        x1, x2 = calibration.regionOfInterestX1, calibration.regionOfInterestX2
        if x1 is None or x2 is None:
            return
        nmMin, nmMax = self.__captureWindow()
        newX1, newX2 = ExtendedRoiLogicModule().extendedXBounds(calibration, imageWidth, nmMin, nmMax)
        if newX1 is None or newX2 is None:
            return
        self.__warnIfWindowShortfall(calibration, newX1, newX2, nmMin, nmMax)
        self.__savedRoiX = (x1, x2)
        calibration.regionOfInterestX1 = int(newX1)
        calibration.regionOfInterestX2 = int(newX2)

    def __warnIfWindowShortfall(self, calibration, x1, x2, nmMin, nmMax):
        # SPEC §9 (M1) guard: extendedXBounds silently clamps to the raster, so if the calibration can't physically
        # reach nmMin/nmMax the achieved window is NARROWER than requested with no notice. Compare the achieved nm
        # at the clamped columns and flag the shortfall (an operator-confidence signal).
        coeffs = [getattr(calibration, n, None) for n in
                  ("interpolationCoefficientA", "interpolationCoefficientB",
                   "interpolationCoefficientC", "interpolationCoefficientD")]
        if any(c is None for c in coeffs):
            return
        a, b, c, d = (float(v) for v in coeffs)
        nmAt = lambda px: a * px ** 3 + b * px ** 2 + c * px + d
        achievedLo, achievedHi = sorted((nmAt(int(x1)), nmAt(int(x2))))
        tol = 2.0
        if achievedLo > nmMin + tol or achievedHi < nmMax - tol:
            print("WARNING CapturePanel: capture window shortfall — requested %.0f–%.0f nm, calibration reaches "
                  "only %.0f–%.0f nm (raster-clamped). SPEC_capture_quality.md §9."
                  % (nmMin, nmMax, achievedLo, achievedHi))

    def restoreRoi(self):
        if self.__savedRoiX is None:
            return
        calibration = self.__calibration()
        if calibration is not None:
            calibration.regionOfInterestX1, calibration.regionOfInterestX2 = self.__savedRoiX
        self.__savedRoiX = None
