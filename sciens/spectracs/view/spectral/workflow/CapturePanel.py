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
from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil
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

    # Below this camera DN the darkest bin of a capture is quantization-limited (one code step is
    # >15% relative there) — reported per capture by the low-DN guard, SPEC_capture_quality.md §17.6/11.
    # 16 DN is where the new dilution protocol puts the Soret floor (§17.5, side observation).
    # ⚠ FALLBACK ONLY (SPEC_soret_448_trim.md §13, D-captureguard): the guard is a MEASUREMENT constant and
    # travels on CaptureView.levels / guardBandNm / guardTargetDn, declared by the plugin. This value is what a
    # plugin that declares nothing still gets, so a non-declaring plugin's preview is unchanged.
    # ⭐ It is ALSO the floor check that survives in the CAPTURE-LOWDN log line after the 16 DN line came OFF
    # the plot (SPEC_capture_quality.md §16.23.10f): across 34 archive runs the minimum ever observed inside
    # the metric window was 37.6 DN, so as a drawn line it only added ink — but it is still the one thing that
    # would catch a genuinely broken capture (dead lamp, mis-clamped ROI) rather than a dosing error.
    __LOW_DN_WARN = 16.0
    __GUARD_COLOR = (200, 120, 60)
    __TARGET_COLOR = (107, 127, 90)
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
    # §7b (Edwin 2026-07-25): inner-tab order is Spectrum then Image. The SELECTED tab on entry is Image
    # (D-capture-default: aiming needs the live feed); capture auto-switches to Spectrum to show the result,
    # and AE forces Image during the sweep.
    __SPECTRUM_TAB = 0
    __IMAGE_TAB = 1

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
        self.__cancelRequested = False
        self.__coachLabel = None
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

    def isCapturing(self):
        # ⭐ §12.1a: while this is true the capture button reads "Cancel", so the acquisition-guidance cue
        # must not paint its amber "next action" dot on it.
        return self.__capturing

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

    def setActiveStep(self, step):
        # SPEC_simplified_plugin_navigation.md §4.6 (role-lift): drive the active role EXTERNALLY when the host's
        # chevron is the role selector (per-step chevrons). Hide the internal Reference/Sample tab bar and run the
        # same __onRoleTabChanged logic (reparent content, exposure-lock-on-sample, labels, plot).
        if step not in self.__steps:
            return
        index = self.__steps.index(step)
        self.__roleTabs.tabBar().setVisible(False)
        self.__roleTabs.blockSignals(True)
        self.__roleTabs.setCurrentIndex(index)
        self.__roleTabs.blockSignals(False)
        self.__onRoleTabChanged()

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
        self.__innerTabs.addTab(self.__spectrumPlot, "Spectrum")            # __SPECTRUM_TAB (index 0)
        self.__innerTabs.addTab(self.__videoViewModule, "Image")            # __IMAGE_TAB (index 1)
        self.__innerTabs.setCurrentIndex(self.__IMAGE_TAB)                  # D-capture-default: open on Image for aiming

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
        # ⭐⭐ INVERTED FOR §12.1a: the capture button is ALSO the cancel button, so during a capture it is
        # the one control that must stay live — every OTHER control below stays disabled exactly as before.
        # ⚠ Cancel works during the ~15 s auto-exposure sweep too (§23/V4): that is the longest single
        # blocking stretch of a capture, and a Cancel that is dead for 15 s teaches the operator it does
        # not work. ⛔ Except while already cancelling, when the button is deliberately dead.
        if busy and not self.__cancelRequested:
            self.__setCaptureButtonCancel()
        else:
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
            self.__videoViewModule.setCropToRoi(False)
        else:
            self.__videoViewModule.setRoi(*extended)
            # Change A: the active step's CaptureView decides whether the live preview shows only the cropped ROI.
            self.__videoViewModule.setCropToRoi(self.__croppedPreview())

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
        # ⭐⭐ A CAPTURE OWNS THE STATUS BAR FROM THE CLICK TO ITS END (SPEC_settled_measurement.md §27.23/P4).
        # ⛔ This used to reset the bar unconditionally — mid-capture that put "ready for action…" on screen
        # while the instrument was still measuring, and it stopped the animation for the rest of the sweep's
        # aftermath. The sweep is a SUB-STEP of the capture: it may refine the bar to its own real fraction
        # (n/N probes, which beats an animation), and it must then hand ownership BACK, not drop it.
        # ⚠ AE also runs on its own from the checkbox, and THERE the reset is exactly right (P5) — so this is
        # a condition, not a deletion.
        if self.__capturing:
            self.__emitIndeterminate("Exposure locked — waiting for the first frames …")
        else:
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

    def __logCameraSettings(self, role, frames=None):
        # One greppable line per capture (stdout, alongside the CaptureBackend prints): the AE-landed exposure and
        # the live V4L2 controls. Compare Reference vs Sample and run-to-run to trace the reference-tilt that shifts
        # the absorbed colour (SPEC_capability_proof.md §7.0.1). Best-effort — a diagnostic must never break capture.
        #
        # `frames` (SPEC_soret_448_trim.md §18 S7): the burst size is now plugin-declared and CHANGED (150 -> 60),
        # so the archive is frame-count-mixed from 2026-08-10 on and no diagnostic table has a column for it.
        # Logging it here is what stops a future session reconstructing it from the data — which is exactly what
        # §16.27 had to do for the exposure, because that was never persisted either.
        thread = self.__videoThread
        if thread is None:
            return
        try:
            settings = thread.readCameraSettings()
        except Exception as error:
            print("CAPTURE-SETTINGS role=%s frames=%s unavailable (%s)" % (role, frames, error))
            return
        print("CAPTURE-SETTINGS role=%s frames=%s exposure_applied=%s exposure_cv2=%s autoExposure=%s wb=%s "
              "autoWb=%s gain=%s backlight=%s wbRequested=%s"
              % (role, frames, settings.get("appliedExposure"), settings.get("exposure"),
                 settings.get("autoExposure"), settings.get("wbTemperature"), settings.get("autoWb"),
                 settings.get("gain"), settings.get("backlight"),
                 settings.get("whiteBalanceKelvinRequested")))

    def __guardReading(self, view, spectrum):
        """`min(S)` over the plugin's declared guard window, in ENCODED DN — SPEC_capture_quality.md §16.23.10f.

        ⭐ ONE computation, consumed by BOTH the log line and the drawn crosshair. That is the entire point of
        §16.23.10: the shipped code had `__logLowDnGuard` compute its own (unwindowed) minimum while
        `__drawLowDnGuard` painted unrelated static lines, so the number the operator read and the number the
        log recorded were never the same statistic.

        ⚠ `view.guardBandNm is None` ⇒ the legacy global minimum over every bin, so a plugin that declares
        nothing behaves exactly as before. That legacy path is what §16.23.10a shows to be useless on this
        lamp — it lands at 417 nm, the blue cutoff, on every capture — but it is not this change's job to
        alter a non-declaring plugin.

        Returns `(digitalNumber, nanometer)` or None. Never raises: a guard must not break a capture.
        """
        try:
            values = (spectrum.valuesByNanometers or {}) if spectrum is not None else {}
            if not values:
                return None
            band = getattr(view, "guardBandNm", None) if view is not None else None
            if band is not None:
                low, high = float(band[0]), float(band[1])
                values = {nm: value for nm, value in values.items() if low <= float(nm) <= high}
                if not values:
                    return None
            nanometer, minimum = min(values.items(), key=lambda item: item[1])
            # The spectrum is LINEAR here; the thresholds live in ENCODED (camera) DN — §16.23.10b, settled on
            # `20260804A`. Encode ONCE, here, so no caller can double-encode or compare across spaces.
            digitalNumber = SpectralColorUtil().encodeGammaFraction(max(0.0, float(minimum)) / 255.0)
            return digitalNumber, float(nanometer)
        except Exception:
            return None

    def __guardVerdict(self, view, digitalNumber):
        # (verdict, isInside) against the plugin's DECLARED target pair. No pair declared => no verdict, which
        # is the honest answer rather than inventing one from whatever levels happen to be drawn.
        target = getattr(view, "guardTargetDn", None) if view is not None else None
        if target is None or digitalNumber is None:
            return None, True
        low, high = float(target[0]), float(target[1])
        if digitalNumber < low:
            return "too-concentrated", False
        if digitalNumber > high:
            return "too-dilute", False
        return "in-window", True

    def __logLowDnGuard(self, role, step, spectrum):
        # Low-DN guard (SPEC_capture_quality.md §16.23.10f, §17.6/11). The darkest bin INSIDE THE DECLARED
        # WINDOW decides whether absorbance is real or quantization: at DN 5 a single code step is ~20%
        # relative before the gamma decode and ~44% after it, and once a bin reaches 0 absorbance saturates
        # silently. Best-effort, never breaks a capture.
        #
        # ⭐ The 16 DN floor line is no longer DRAWN (§16.23.10f) — across 34 archive runs the minimum observed
        # was 37.6 DN, so it only ever added ink. The CHECK stays here because it is the one thing that would
        # catch a genuinely broken capture (a dead lamp, a mis-clamped ROI) as opposed to a dosing error.
        try:
            view = step.getView() if step is not None else None
            reading = self.__guardReading(view, spectrum)
            if reading is None:
                return
            digitalNumber, nanometer = reading
            band = getattr(view, "guardBandNm", None) if view is not None else None
            target = getattr(view, "guardTargetDn", None) if view is not None else None
            verdict, _inside = self.__guardVerdict(view, digitalNumber)
            print("CAPTURE-LOWDN role=%s minDn=%.1f at=%.1fnm window=%s target=%s verdict=%s%s"
                  % (role, digitalNumber, nanometer,
                     ("%g-%gnm" % (band[0], band[1])) if band else "full",
                     ("%g-%g" % (target[0], target[1])) if target else "none",
                     verdict or "none",
                     # ⚠ The old text said "dilute less or expose longer" for a DARK bin, which is backwards —
                     # a dark bin needs MORE solvent, not less (§16.23.10f).
                     "  <-- FLOOR (quantization-limited; add solvent or expose longer)"
                     if digitalNumber < self.__LOW_DN_WARN else ""))
        except Exception as error:
            print("CAPTURE-LOWDN role=%s unavailable (%s)" % (role, error))

    def __onClickedCapture(self):
        # ⭐ THE CANCEL BUTTON IS THIS BUTTON (SPEC_settled_measurement.md §12.1a) — one control, nothing
        # extra to lay out at phone width, and the control that started the run is the one that stops it.
        #
        # ⛔ RE-ENTRANCY IS THE WHOLE HAZARD: this click arrives from INSIDE the nested QEventLoop that
        # __pumpFrames spins during the capture below, i.e. on the capture's own stack. So it may set the
        # flag and NOTHING else — never touch capture state, never navigate, never start a capture.
        if self.__capturing:
            self.__cancelRequested = True
            self.__setCaptureButtonCancelling()   # relabel + disable NOW, so a double-click cannot land
            return
        if self.__resolvedIndex is None or self.__videoThread is None or self.__autoExposing:
            return
        step = self.__activeStep
        if step is None:
            return
        self.__cancelRequested = False
        # SPEC_doc_automation §18.3 (C3a): mark the WHOLE capture busy — auto-exposure AND the multi-frame
        # burst — so the capture button (and role tabs / frames combo, via __updateControls) stay disabled
        # for its entire duration. Previously only auto-exposure set busy, so the button re-enabled mid-burst
        # (and for the SAMPLE role, which never auto-exposes, it was never disabled at all). set/reset in
        # try/finally so the capture-failed early return below can't leave the button stuck disabled.
        self.__capturing = True
        self.__updateControls()
        try:
            role = step.getRole()
            # ⭐ THE BAR STARTS AT THE CLICK, NOT AT THE FIRST ROW (Edwin, at the rig 2026-08-17). Between
            # pressing Measure and the first row there is the ~15 s auto-exposure sweep and then a whole
            # window of frames (~43 s at W = 60) — a minute in which the app showed nothing at all and
            # looked like it had ignored the click.
            # ⚠ Indeterminate from the outset because at this moment NOTHING about the duration is known:
            # not whether the plugin will monitor, not how long the fill will take. The burst path swaps
            # in its real fraction on the first frame; the monitored path keeps animating and swaps in the
            # coach text (§13.2).
            self.__emitIndeterminate("Measuring %s …"
                                     % ("reference" if role == REFERENCE else "sample"))
            if role == REFERENCE and self.__autoExposureCheckBox.isChecked():
                self.__emitIndeterminate("Auto-exposure sweep …")   # ~15 s of otherwise silent waiting
                self.__runAutoExposure()      # async: hands the sweep to the capture thread
                self.__waitForAutoExposure()  # ...block until it finishes before grabbing the reference burst
                # ⚠ Idempotent with the handler's own re-emit (§27.23/P4): `__waitForAutoExposure` is BOUNDED,
                # so a sweep that never reports finished returns here with its determinate fill still on the
                # bar. Re-asserting ownership costs one signal and closes that hole.
                self.__emitIndeterminate("Exposure locked — waiting for the first frames …")
                # The fixed 1-frame drop that used to sit here is RETIRED (SPEC_capture_quality.md §14.8): the
                # sweep now settles ADAPTIVELY at `best` (VideoThread.__settleUntilStable, C2) so the stream is
                # genuinely stable before the burst, and any residual dim frame is rejected per-frame in the
                # temporal reduction (C1) while the burst tops up to keep N effective (C3). Dropping exactly one
                # frame only ever covered ONE bad frame — the ELP emits several (the ksnip evidence).
                self.__latestImage = None     # discard the last pre-sweep stale frame; the burst waits for a fresh one

            frameCount = int(self.__framesComboBox.currentText())
            self.__innerTabs.setCurrentIndex(self.__SPECTRUM_TAB)
            self.__beginCaptureProgress(frameCount)
            self.__waitForFirstFrame()

            images = []
            state = {"roiApplied": False}

            def provider():
                self.__pumpFrames(120)  # let the stream advance a frame
                # ⭐ §12.1a: the cancel flag is seen here, at most one frame (~0.7 s) after the click. The
                # engine's provider contract has no "stop" value, so a cancelled run simply stops being
                # fed and unwinds through the same path a camera failure takes.
                if self.__cancelRequested:
                    return None
                if self.__latestImage is None:
                    return None
                image = self.__latestImage.copy()  # detach from the live numpy buffer
                if not state["roiApplied"]:
                    self.__applyExtendedRoi(image.width())  # widen to the analysis window before the FIRST extraction
                    state["roiApplied"] = True
                # ⛔ ONE representative frame, never a list (SPEC_settled_measurement.md §19/I1). Keeping
                # every frame to pick the middle one costs ~1 GB of QImages on a 20-minute monitored run —
                # harmless at 60 frames, fatal the moment a burst gets long.
                state["frameCount"] = state.get("frameCount", 0) + 1
                if state.get("representative") is None or state["frameCount"] % 2 == 0:
                    state["representative"] = image
                return image

            def onFrame(spectrum, index, total):
                self.__plotRoleSpectrum(role, spectrum)     # live: frame traces so far + running mean
                self.__stepCaptureProgress(index + 1)

            # ⭐ MONITORED ACQUISITION (SPEC_settled_measurement.md §10.4). The PLUGIN decides whether this
            # role gets one: it is handed the already-captured reference and returns an assembled monitor,
            # or None. ⛔ Nothing here knows what settling is — the host only pumps frames into an object
            # it was given, and a plugin that returns None gets exactly today's burst (§10.6).
            monitor = self.__monitorFor(step, role, frameCount)
            monitoredResult = None
            if monitor is not None:
                # ⚠ THE SECOND SILENCE (§27.23/P4). The burst path swaps in a real fraction on its first
                # frame, but a monitored run says nothing until its first DECISION ROW — a whole window,
                # ~43 s at W = 60 — and an empty bar in that gap reads as "the click was ignored", which is
                # the very complaint §27.10 set out to fix.
                self.__emitIndeterminate("Measuring %s — filling the first window …"
                                         % ("reference" if role == REFERENCE else "sample"))
                result = self.__engine.captureMonitoredStep(
                    step, frameProvider=provider, monitor=monitor, onRow=self.__onMonitorRow)
                monitoredResult = result
                self.__endCaptureProgress()
                self.__clearCoach()
                if not self.__cancelRequested and not self.__onMonitorFinished(step, role, result):
                    return
                spectrum = result.spectrum
            else:
                spectrum = self.__engine.captureAcquisitionStep(
                    step, frameProvider=provider, frames=frameCount, onFrame=onFrame)
                self.__endCaptureProgress()

            if self.__cancelRequested:
                # ⛔ A CANCELLED CAPTURE IS NOT A CAPTURE (§12.1): the step keeps no container, so the
                # workflow cannot advance on a partial one. ⚠ And the fill has already banked light dose —
                # re-measuring THIS jar is not the same experiment as measuring a fresh one (§17/U2).
                step.setContainer(None)
                self.__representativeFrames.pop(role, None)
                self.__showStatusText("Capture cancelled — nothing recorded. This fill has been in the "
                                      "beam and has changed; a fresh fill reads truer than a re-measure.")
                return

            if spectrum is None or state.get("representative") is None:
                # ⛔⛔ NEVER SAY "no frames were delivered" ABOUT A RUN THAT ANSWERED (§27.25/M3). That
                # dialog cost two measurements on 2026-08-17: a monitored run whose gate had fired and
                # whose value was computed was reported as a camera failure, and re-measuring the same jar
                # banked light dose that pushed the repeat upward. ⚠ The engine's fallback (M3) plus the
                # time-sized retention (M1) should make this unreachable for a monitored run — if it is
                # reached, the operator is told what is actually true.
                if monitoredResult is not None and monitoredResult.hasValue():
                    self.__showStatusText(
                        "⛔ The measurement was made (%s %.2f) but its spectrum could not be recovered, so "
                        "nothing was recorded. ⚠ This fill has been in the beam — a FRESH fill reads truer "
                        "than re-measuring it." % (monitoredResult.answer.get("valueKey", "value"),
                                                   monitoredResult.answer.get("value", float("nan"))))
                    return
                self.__onCaptureFailed()
                return

            self.__representativeFrames[role] = state["representative"]

            # Diagnostic (SPEC_capability_proof.md §7.0.1): log the landed exposure / white-balance / gain for THIS
            # capture, so reference-vs-sample and run-to-run drift (the absorbed-colour reference tilt) is traceable.
            self.__logCameraSettings(role, frames=frameCount)
            self.__logLowDnGuard(role, step, spectrum)

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
            self.__cancelRequested = False
            self.__restoreCaptureButtonLabel()
            self.__updateControls()

    # --- monitored acquisition (SPEC_settled_measurement.md §13) ---

    def __monitorFor(self, step, role, frameCount):
        """Ask the PLUGIN for a monitor. None -> today's plain burst, unchanged (§10.6).

        ⚠ Only the SAMPLE gets one, and only once a REFERENCE exists: every row is `S_window` against one
        fixed blank, so without a reference there is nothing to compute absorbance against.
        ⚠ PRODUCT mode here (§17/D3): the diagnostic arc is the SCRIPT's, and a mode chosen by the plugin
        would put a 20-minute run inside an end user's wizard."""
        plugin = getattr(self.__engine, "plugin", None)
        if plugin is None or role == REFERENCE or not hasattr(plugin, "createMonitor"):
            return None
        referenceStep = self.__stepForRole(REFERENCE)
        container = referenceStep.getContainer() if referenceStep is not None else None
        reference = container.getSpectra().get(REFERENCE) if container is not None else None
        if reference is None:
            return None
        try:
            from sciens.spectracs.plugin_sdk import MonitorMode
            return plugin.createMonitor(reference, mode=MonitorMode.PRODUCT, frames=frameCount)
        except Exception as error:            # a plugin that cannot build one must not break capture
            print("MONITOR unavailable (%s) — falling back to the plain burst" % error)
            return None

    def __onMonitorRow(self, row, monitor):
        """Per-row UI. ⚠ Cheap on purpose (§23/V3): `handleVideoThreadSignal` ends with `event.set()`, so
        the camera thread WAITS for the GUI — every millisecond spent here is a millisecond not grabbing.

        ⛔ NO PERCENTAGE (§13.1): a monitored run has no known end, and a bar creeping to 90 % and sitting
        there is worse than none. The status bar goes INDETERMINATE and the legend box carries the state.
        ⚠ Numbers refresh no faster than ~2 s — a value flickering at 1.4 Hz reads as instability."""
        import time as _time
        now = _time.monotonic()
        evaluator = getattr(monitor, "evaluator", None)
        coach = evaluator.coach(monitor.rows) if hasattr(evaluator, "coach") else None
        stateChanged = coach is not None and coach.get("state") != getattr(self, "_lastCoachState", None)
        if now - getattr(self, "_lastCoachPaint", 0.0) < 2.0 and not stateChanged:
            return
        self._lastCoachPaint = now
        if coach is not None:
            self._lastCoachState = coach.get("state")

        # ⭐⭐ PAINT THE SPECTRUM (Edwin, at the rig 2026-08-17). A monitored run can last twenty minutes,
        # and the first version showed only text for all of it — the plot sat empty and the instrument
        # looked dead. The BURST path always painted per frame (`onFrame`), and losing that on the longer
        # path was exactly the wrong way round.
        # ⚠ It is painted on the ~2 s throttle, NOT per row (§23/V3): `handleVideoThreadSignal` ends with
        # `event.set()`, so the camera thread waits for the GUI and a per-row redraw would throttle the
        # very stream being measured.
        # ⚠ This is the WINDOW MEAN, not a raw frame — the same spectrum the row's numbers came from, so
        # what the operator watches and what the gate reads are the same object.
        spectrum = getattr(row, "spectrum", None)
        if spectrum is not None:
            role = self.__activeStep.getRole() if self.__activeStep is not None else None
            self.__plotRoleSpectrum(role, spectrum)
        if coach is None:
            return
        self.__paintCoach(coach, row)
        # ⭐ §13.2: the falling gate number IS the progress indicator — it says both where it is and how
        # fast it is getting there, which a percentage never could.
        self.__emitIndeterminate("%s   %s" % (coach.get("state", "measuring …"),
                                              "  ".join("%s %s" % pair for pair in coach.get("fields", []))))

    def __paintCoach(self, coach, row):
        # ⛔ THE LEGEND BOX IS GONE (Edwin, at the rig 2026-08-17), and this REVERSES §13.2's placement.
        # During a run the state belongs in ONE place — the app's status bar, which is already animating
        # for exactly this reason. A second copy under the spectrum plot competed with the curve for the
        # operator's eye and stole height from the one thing that shows progress.
        # ⚠ The withholding rule is unchanged and now lives entirely in the evaluator's `coach()`: ⛔ NEVER
        # a provisional Q% (§17/U1) — a number displayed while it is still moving is a number somebody
        # writes down.
        return

    def __clearCoach(self):
        return

    def __onMonitorFinished(self, step, role, result):
        """Return True when the run produced a usable measurement.

        ⛔ §2.5/§12.3: an outcome without a value must always SAY WHY, or the operator learns to read a
        missing number as a bug. ⚠ And §17/U2: a fill that has been in the beam has banked light dose, so
        re-measuring THIS jar is not the same experiment as measuring a fresh one."""
        # ⛔⛔ THE RECORD IS WRITTEN FOR **EVERY** OUTCOME, NOT ONLY THE GOOD ONES (§12.1/§15.2).
        # ⚠ The first version wrote it only on success, which lost the trajectory of exactly the runs
        # worth looking at — a fill that never cleared, a cancelled one, a failed one. §12.1 is explicit:
        # "the trajectory so far is KEPT, marked, and never reported as a measurement". Keeping it is what
        # makes the Settling step (§18) a diagnostic rather than a trophy cabinet.
        workflow = self.__engine.getWorkflow() if hasattr(self.__engine, "getWorkflow") else None
        if workflow is not None and hasattr(workflow, "setMonitorRecord"):
            workflow.setMonitorRecord(result.toRecord())         # ⭐ §15.2 — the choice is auditable
        # One greppable line per monitored run, alongside the CAPTURE-SETTINGS / CAPTURE-LOWDN lines: an
        # outcome that only ever appears in a status bar is an outcome nobody can reconstruct afterwards.
        print("MONITOR outcome=%s rows=%d decisionRows=%d clearing=%s capsHit=%s cancelled=%s distinct=%s"
              % (result.outcome.value, len(result.rows), len(result.decisionRows()),
                 result.clearingSeconds, result.capsHit, result.cancelled, result.distinctFraction))

        # ⭐ THE SETTLING TAB BELONGS TO THE SAMPLE STEP (Edwin, at the rig 2026-08-17). It first landed in
        # PROCESSING, beside the other provenance views — but the operator reads it WHILE AND JUST AFTER
        # measuring this jar, and that is the Sample step. So it appears here as a third inner tab, next
        # to Spectrum and Image. ⚠ The PROCESSING/report declaration stays: it is the persisted, re-openable
        # artefact and the page that reaches the PDF (§18.4). Same view-model, two surfaces — which is the
        # "built once, used three times" claim of §18.1 doing its job.
        self.__showSettlingTab(result)

        if result.hasValue():
            answer = result.answer
            self.__showStatusText("✅ settled after %s — %s %.2f (%s)"
                                  % (self.__minutesText(result.clearingSeconds), answer["valueKey"],
                                     answer["value"], answer["readAs"]))
            return True
        step.setContainer(None)
        self.__showStatusText({
            "NEVER_SETTLED": "⛔ the fill never cleared within the time limit — no value. Warm it and "
                             "use a FRESH fill: this one has been in the beam and has changed.",
            "MEASUREMENT_BROKEN": "⛔ no signal in the Soret band — check the fill and the lamp.",
            "STALLED": "⛔ the camera stopped delivering frames — nothing recorded.",
            "FAILED": "⛔ the plugin's evaluation raised; the trajectory was kept but there is no value.",
        }.get(result.outcome.value, "⛔ no value — %s" % result.outcome.value))
        return False

    @staticmethod
    def __minutesText(seconds):
        return "—" if seconds is None else "%d:%02d" % (int(seconds) // 60, int(seconds) % 60)

    def __showSettlingTab(self, result):
        """Add / replace the "Settling" inner tab from the run that just finished.

        ⭐⭐ IT RENDERS THE VIEWS THE ENGINE ALREADY ATTACHED TO THE STEP (§27.12) — `result.views` holds
        the very objects now hanging off this step's EvaluationResult, which is also what the report will
        collect. ⛔ The panel no longer builds its own copy from the record: that was the same thing
        constructed twice, and it is what made a report-only step look necessary.
        ⚠ Shown for EVERY outcome, including the ones with no value: a run that never cleared is exactly
        the run whose curve explains itself (§12.1)."""
        views = getattr(result, "views", None)
        if not views:
            return
        try:
            from sciens.spectracs.view.spectral.workflow.render.QtWorkflowRenderer import QtWorkflowRenderer
            content = QtWorkflowRenderer().render(list(views))
        except Exception as error:              # a diagnostic must never break the capture it documents
            print("SETTLING tab unavailable (%s)" % error)
            return
        for index in range(self.__innerTabs.count()):
            if self.__innerTabs.tabText(index) == "Settling":
                self.__innerTabs.removeTab(index)
                break
        self.__innerTabs.addTab(content, "Settling")
        self.__innerTabs.setCurrentIndex(self.__innerTabs.count() - 1)

    # --- the capture button, which is also the CANCEL button (§12.1a) ---

    def __setCaptureButtonCancelling(self):
        if self.__captureButton is not None:
            self.__captureButton.setText("Cancelling …")
            self.__captureButton.setEnabled(False)   # ⭐ blocks the double-click while the run unwinds

    def __setCaptureButtonCancel(self):
        if self.__captureButton is not None:
            self.__captureButton.setText("Cancel")
            self.__captureButton.setProperty("danger", True)
            self.__captureButton.setEnabled(True)    # ⭐ the ONLY live control during a capture

    def __restoreCaptureButtonLabel(self):
        if self.__captureButton is None:
            return
        self.__captureButton.setProperty("danger", False)
        role = self.__activeStep.getRole() if self.__activeStep is not None else None
        self.__captureButton.setText("Capture reference" if role == REFERENCE else "Capture sample")

    def __emitIndeterminate(self, text):
        # ⭐ `stepsCount = 0` is the app-wide "no knowable end" convention (§13.2): MainStatusBarViewModule
        # answers it with the moving-stripes animation and keeps the text. ⛔ Not `guidance = True` — that
        # is the amber coach LINE with no bar at all, and during a capture there IS something running.
        signal = ApplicationStatusSignal()
        signal.isStatusReset = False
        signal.stepsCount = 0
        signal.currentStepIndex = 0
        signal.text = text
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(signal)

    def __showStatusText(self, text):
        signal = ApplicationStatusSignal()
        signal.isStatusReset = False
        signal.text = text
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(signal)

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
        # Drawn on a CAMERA-DN axis, not in linear light (SPEC_capture_quality.md §16.7.2e). This plot is an
        # EXPOSURE instrument: every judgement taken from it — clipping at 255, the AE target at 245,
        # quantization below 16 — is a sensor fact, and on a linear axis those landmarks collapse into the
        # bottom few percent (16..60 DN occupies 4% of the height). The pipeline keeps the linear values.
        title = "Reference" if role == REFERENCE else "Sample"
        if spectrum is None:
            plot.plotSpectrum(None, title=title)
            return
        util = SpectralColorUtil()
        frames = spectrum.getCapturedValuesByNanometers()
        plot.plotSpectrum(None, title=title)  # clear + set title
        plot.getPlotItem().setLabel("left", "camera DN")
        # ⚠ Pass the spectrum: the MEASURED crosshair is derived from it here, by the same `__guardReading`
        # the log used, so the plot and the log cannot show different numbers (§16.23.10f).
        self.__drawLowDnGuard(plot, spectrum)
        for values in frames:
            frameSpectrum = Spectrum()
            frameSpectrum.setValuesByNanometers(dict(values))
            plot.addTrace(util.toDisplayDnSpectrum(frameSpectrum), color=self.__FRAME_COLOR, width=1)
        plot.addTrace(util.toDisplayDnSpectrum(self.__meanSpectrum(spectrum)),
                      color=self.__MEAN_COLOR, width=2)

    def __drawMeasuredGuard(self, plot, spectrum):
        """The two-line crosshair at the MEASURED reading — SPEC_capture_quality.md §16.23.10f.

        Horizontal at the DN, vertical at the wavelength it landed on, green inside the plugin's declared
        target pair and red outside it. ⭐ The vertical line is what makes the number readable: the anchor is
        `min` over a window, so WHERE it landed is data, not a constant — and on `20260812_BillaClever` it
        landed at 448.0–448.2 nm, the window start, every time.

        ⚠ Both lines carry `setZValue(-5)` and are added AFTER the guard levels but BEFORE the traces, so an
        annotation can never drive autorange (`test_plot_annotations_do_not_rescale`).
        """
        import pyqtgraph as pg
        from sciens.spectracs.view.spectral.workflow.SpectrumPlotWidget import SpectrumPlotWidget
        view = self.__activeStep.getView() if self.__activeStep is not None else None
        if view is None or getattr(view, "guardBandNm", None) is None:
            return
        reading = self.__guardReading(view, spectrum)
        if reading is None:
            return
        digitalNumber, nanometer = reading
        _verdict, inside = self.__guardVerdict(view, digitalNumber)
        colors = getattr(view, "guardColors", None) or {}
        color = colors.get("inside" if inside else "outside") or (self.__TARGET_COLOR if inside
                                                                  else self.__GUARD_COLOR)
        pen = SpectrumPlotWidget.pen(color, width=2, style="solid")
        horizontal = pg.InfiniteLine(pos=digitalNumber, angle=0, pen=pen,
                                     label="%.0f DN @ %.1f nm" % (digitalNumber, nanometer),
                                     labelOpts={"position": 0.82, "color": color, "movable": False})
        horizontal.setZValue(-5)
        plot.addItem(horizontal)
        vertical = pg.InfiniteLine(pos=nanometer, angle=90, pen=pen)
        vertical.setZValue(-5)
        plot.addItem(vertical)

    def __drawLowDnGuard(self, plot, spectrum=None):
        # The lines the operator judges dilution against — SPEC_soret_448_trim.md §25.4.
        #
        # ⭐ PLUGIN-DECLARED, PER STEP, and drawn WITH THEIR CAPTIONS, exactly as the PROCESSING plot draws
        # them: the CaptureView carries `levels` in the same shape as SpectrumPlotView, so a value, its
        # caption, its colour and its style exist once and the live preview cannot drift from the report.
        #
        # ⛔ Reads the ACTIVE step, not `self.__steps[0]`. That was a real defect: steps[0] is always the
        # REFERENCE step, so the reference's declaration was painted on whichever role was on screen. It also
        # made "guards on the sample only" unexpressible — and §16.23.8 states the guard on min(S) AFTER THE
        # SAMPLE CAPTURE. The reference is a solvent blank judged against R ~ 88; 16/60 DN never applied to it.
        #
        # A plugin that declares nothing still gets the legacy single 16 DN line, so non-declaring plugins and
        # pre-2026-08-10 behaviour are unchanged.
        import pyqtgraph as pg
        from sciens.spectracs.view.spectral.workflow.SpectrumPlotWidget import SpectrumPlotWidget
        view = self.__activeStep.getView() if self.__activeStep is not None else None
        # ⭐ Drawn FIRST and independently of `levels` (§16.23.10f): the measured crosshair is a reading, not a
        # declaration, so a plugin that declares a guard window but no drawn levels still gets it — and the
        # `elif not levels: return` below must not swallow it.
        self.__drawMeasuredGuard(plot, spectrum)
        levels = getattr(view, "levels", None)
        if levels is None:
            levels = [] if view is not None else [(self.__LOW_DN_WARN, None, None, None, None, "dashed", None)]
        elif not levels:
            return
        for level in levels:
            value, _lowNm, _highNm, label, color, style, _number = tuple(level) + (None,) * (7 - len(level))
            pen = SpectrumPlotWidget.pen(color or self.__GUARD_COLOR, width=1, style=style or "dashed")
            line = pg.InfiniteLine(pos=value, angle=0, pen=pen,
                                   label=(str(label) if label else None),
                                   labelOpts={"position": 0.04, "color": (color or self.__GUARD_COLOR),
                                              "movable": False})
            line.setZValue(-5)
            plot.addItem(line)

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

    def __croppedPreview(self):
        # Change A: the active step's CaptureView.croppedPreview (default False = whole frame + dotted box).
        view = self.__activeStep.getView() if self.__activeStep is not None else None
        return bool(getattr(view, "croppedPreview", False))

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
