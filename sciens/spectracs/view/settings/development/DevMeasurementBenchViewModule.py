import numpy as np
import pyqtgraph as pg

from PySide6.QtCore import Qt, QEventLoop, QTimer, QRect
from PySide6.QtGui import QPixmap, QColor, QPainter
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox,
                               QSlider, QCheckBox, QTabWidget, QStackedWidget, QScrollArea,
                               QFrame, QSizePolicy, QFileDialog)

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.appliction.style.Metrics import Metrics
from sciens.spectracs.logic.appliction.video.DevCaptureVideoThread import DevCaptureVideoThread
from sciens.spectracs.logic.appliction.video.capture.AutoExposureLogicModule import AutoExposureLogicModule
from sciens.spectracs.logic.appliction.video.capture.SensorCaptureIndexResolver import SensorCaptureIndexResolver
from sciens.spectracs.logic.spectral.acquisition.ExtendedRoiLogicModule import ExtendedRoiLogicModule
from sciens.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModule import ImageSpectrumAcquisitionLogicModule
from sciens.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModuleParameters import ImageSpectrumAcquisitionLogicModuleParameters
from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModule import MeanSpectrumLogicModule
from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModuleParameters import MeanSpectrumLogicModuleParameters
from sciens.spectracs.logic.model.util.spectrometerSensor.SpectrometerSensorUtil import SpectrometerSensorUtil
from sciens.spectracs.logic.session.ActiveSpectrometerProfileLogicModule import ActiveSpectrometerProfileLogicModule
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
from sciens.spectracs.logic.spectral.plugin.dev.DevSpectralPlugin import DevSpectralPlugin
from sciens.spectracs.logic.spectral.plugin.pumpkin.PumpkinOilPlugin import PumpkinOilPlugin
from sciens.spectracs.logic.spectral.workflow.SpectralWorkflowEngine import SpectralWorkflowEngine
from sciens.spectracs.model.application.applicationStatus.ApplicationStatusSignal import ApplicationStatusSignal
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.model.spectral.SpectraContainer import SpectraContainer
from sciens.spectracs.model.spectral.SpectralVideoThreadSignal import SpectralVideoThreadSignal
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.model.spectral.plugin.view.ReportView import ReportView
from sciens.spectracs.model.spectral.plugin.view.LimsPublishView import LimsPublishView
from sciens.spectracs.model.spectral.plugin.view.SpectrumCaptureView import SpectrumCaptureView
from sciens.spectracs.model.spectral.plugin.view.SpectrumPlotView import SpectrumPlotView
from sciens.spectracs.plugin_sdk import SpectrumFeatureUtil
from sciens.spectracs.plugin_sdk.roles import REFERENCE, SAMPLE, TRANSMISSION, ABSORPTION
from sciens.spectracs.view.application.widgets.InWindowDialog import InWindowDialog
from sciens.spectracs.view.application.widgets.ScaledImageLabel import ScaledImageLabel
from sciens.spectracs.view.application.widgets.PdfPreviewWidget import PdfPreviewWidget
from sciens.spectracs.view.spectral.workflow.EvaluationResultRenderer import EvaluationResultRenderer
from sciens.spectracs.view.application.widgets.StepBarWidget import StepBarWidget
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget
from sciens.spectracs.view.settings.development.DevCaptureVideoViewModule import DevCaptureVideoViewModule
from sciens.spectracs.view.spectral.workflow.SpectrumPlotWidget import SpectrumPlotWidget
from sciens.spectracs.view.spectral.workflow.render.WorkflowPhaseRenderer import WorkflowPhaseRenderer


class DevMeasurementBenchViewModule(PageWidget):
    """Master "Swiss-knife" measurement bench (SPEC_dev_measure_bench.md). A generic real-camera run of the
    same pipeline an end-user plugin drives — capture REFERENCE + SAMPLE, compute transmission + absorption —
    without any use-case verdict. Backed by a transiently-injected DevSpectralPlugin; capture is owned by the
    view (real camera + exposure), extraction by ImageSpectrumAcquisitionLogicModule (shared). Transmission
    geometry only (sample between bulb and camera). Master-only; ephemeral (no saved runs)."""

    __EXPOSURE_MIN = 1
    __EXPOSURE_MAX = 500
    __EXPOSURE_FALLBACK = 150
    __AUTO_EXPOSE_MAX_PROBES = 8
    __FRAME_CHOICES = ["10", "20", "50"]
    __DEFAULT_FRAMES = "20"

    # Bench analysis window (SPEC_dev_measure_bench.md §12): the calibration ROI clips the VIS band, so the
    # bench temporarily widens the in-memory ROI to span this wavelength range (clamped to the raster).
    __NM_MIN = 400.0
    __NM_MAX = 700.0

    __REF_COLOR = "#5DADE2"      # reference spectrum (blue)
    __SAMPLE_COLOR = "#F5B041"   # sample spectrum (orange)
    __FRAME_COLOR = "#777777"    # per-frame traces (gray)
    __MEAN_COLOR = "#2ECC71"     # mean spectrum (green)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__resolver = SensorCaptureIndexResolver()
        self.__sensor = None
        self.__resolvedIndex = None
        self.__videoThread = None
        self.__latestImage = None
        self.__autoExposing = False

        self.__engine = None
        self.__workflow = None
        # P7: which plugin drives the bench (master-selectable, decoupled from SpectrometerSetup).
        self.__pluginClasses = [DevSpectralPlugin, PumpkinOilPlugin]
        self.__selectedPluginClass = DevSpectralPlugin
        self.__pluginSelect = None
        self.__cursor = 0
        self.__phases = [SpectralWorkflowPhaseType.ACQUISITION, SpectralWorkflowPhaseType.PROCESSING,
                         SpectralWorkflowPhaseType.EVALUATION]

        self.__activeRole = REFERENCE
        self.__lockedExposure = None
        self.__roleSpectra = {}            # role -> extracted Spectrum (with N captured frames)
        self.__representativeFrames = {}   # role -> QImage (preview-only middle frame)
        self.__savedRoiX = None            # (x1, x2) authored originals while the extended window is applied

        # widgets
        self.__messageLabel = None
        self.__stepBar = None
        self.__stack = None
        self.__videoViewModule = None
        self.__roleTabs = None          # QTabWidget wrapping the Reference/Sample steps (S1)
        self.__referencePage = None
        self.__samplePage = None
        self.__stepContent = None       # the ONE shared inner-tabs + controls widget, reparented per role (S1)
        self.__innerTabs = None
        self.__spectrumPlot = None
        self.__framesComboBox = None
        self.__framesControl = None     # labeled "Frames" component (plugin may hide it)
        self.__exposureControl = None   # labeled "Exposure" component (plugin may hide it)
        self.__exposureSlider = None
        self.__exposureLabel = None
        self.__autoExposureCheckBox = None
        self.__captureButton = None
        self.__captureTotal = 1         # frame count of the in-flight capture (S2: status-bar progress)
        self.__processingTabs = None
        self.__evaluationTabs = None    # QTabWidget: Metrics | Spectrum (S4)
        self.__publishingTabs = None    # QTabWidget: Send to LIMS (L6)
        self.__backButton = None
        self.__cancelButton = None
        self.__nextButton = None

    def _getPageTitle(self):
        return "Settings > Development > Measurement bench"

    # --- page scaffold ---

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()
        self.__messageLabel = self.createMessageLabel("")
        result["message"] = self.__messageLabel
        # P7: master-only plugin selector — run ANY plugin on the bench (the M1 acceptance test). Decoupled
        # from the SpectrometerSetup binding; selecting one re-injects it and restarts the run.
        self.__pluginSelect = QComboBox()
        for pluginClass in self.__pluginClasses:
            self.__pluginSelect.addItem(pluginClass.title)
        self.__pluginSelect.currentIndexChanged.connect(self.__onPluginChanged)
        result["pluginSelect"] = self.createLabeledComponent("Plugin", self.__pluginSelect)
        self.__stepBar = StepBarWidget()
        result["stepBar"] = self.__stepBar
        self.__stack = QStackedWidget()
        self.__stack.setObjectName("benchPhaseStack")
        # S11: the phase stack shows ONE WorkflowPhase page at a time (a single content component), whose own
        # tab widgets already frame it — so the stack needs no frame of its own. Drop the global
        # `QStackedWidget { border:1px }` here. This is the WORKFLOW-PHASE border Edwin flagged; it is NOT the
        # WorkflowStep (Reference/Sample = __roleTabs) frame, which stays. Scoped by objectName so it does not
        # touch the internal QStackedWidgets of the nested QTabWidgets (already border:none globally).
        self.__stack.setStyleSheet("QStackedWidget#benchPhaseStack { border: none; }")
        self.__stack.addWidget(self.__buildAcquisitionPanel())   # index 0
        self.__stack.addWidget(self.__buildProcessingPage())     # index 1
        self.__stack.addWidget(self.__buildEvaluationPage())     # index 2 (E1)
        self.__stack.addWidget(self.__buildPublishingPage())     # index 3 (L6 — shown only if declared)
        result["stack"] = self.__stack
        return result

    def createNavigationGroupBox(self):
        result = super().createNavigationGroupBox()
        layout = result.layout()
        self.__backButton = QPushButton("← Back")
        self.__backButton.clicked.connect(self.onClickedBack)
        layout.addWidget(self.__backButton, 0, 0, 1, 1)
        self.__cancelButton = QPushButton("Cancel")
        self.__cancelButton.setProperty("buttonType", "secondary")
        self.__cancelButton.clicked.connect(self.__goToSettings)
        layout.addWidget(self.__cancelButton, 0, 1, 1, 1)
        self.__nextButton = QPushButton("Next →")
        self.__nextButton.clicked.connect(self.onClickedNext)
        layout.addWidget(self.__nextButton, 0, 2, 1, 1)
        return result

    # --- acquisition panel (role tab-bar + shared [Captured image | Spectrum] — Option A, §15) ---

    __IMAGE_TAB = 0
    __SPECTRUM_TAB = 1

    def __buildAcquisitionPanel(self):
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, Metrics.S, 0, 0)
        layout.setSpacing(Metrics.S)
        panel.setLayout(layout)

        # S7: no hint, no inline connection-status line — the role QTabWidget is the top element of the phase
        # content. Connection state shows in the header indicator (green/white/grey); the not-connected
        # diagnostic goes to the app status bar (see __resolveCamera).

        # Shared [ Captured image | Spectrum ] tabs: ONE live-video widget + ONE spectrum plot (re-plotted
        # per active role). During auto-exposure → Captured image; after a capture → Spectrum (E3).
        self.__videoViewModule = DevCaptureVideoViewModule()
        self.__videoViewModule.setObjectName("DevMeasurementBenchViewModule.videoViewModule")
        # S10 (was S8 ③): drop the image widget's own outline (the global BaseVideoViewModule E2/C2 border) for
        # the bench — __innerTabs' pane (the INNER frame) already frames the image area, so the image's own
        # hairline would double it. Bench-only; same selector as the global rule so this widget-local sheet wins.
        self.__videoViewModule.setStyleSheet("BaseVideoViewModule { border: none; }")
        self.__spectrumPlot = SpectrumPlotWidget()
        self.__innerTabs = QTabWidget()
        self.__innerTabs.addTab(self.__videoViewModule, "Captured image")  # __IMAGE_TAB
        self.__innerTabs.addTab(self.__spectrumPlot, "Spectrum")           # __SPECTRUM_TAB

        controls = QWidget()
        controls.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        controlsLayout = QGridLayout()
        controlsLayout.setContentsMargins(0, 0, 0, 0)
        controlsLayout.setSpacing(Metrics.S)
        controls.setLayout(controlsLayout)

        self.__framesComboBox = QComboBox()
        self.__framesComboBox.addItems(self.__FRAME_CHOICES)
        self.__framesComboBox.setCurrentText(self.__DEFAULT_FRAMES)
        self.__framesControl = self.createLabeledComponent("Frames", self.__framesComboBox)
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
        # H3: auto-exposure on its OWN line (full width) so its label no longer wraps/cuts at narrow width
        # (the wrapping was what made the row too tall + overflow).
        exposureRowLayout.addWidget(self.__exposureSlider, 0, 0, 1, 1)
        exposureRowLayout.addWidget(self.__exposureLabel, 0, 1, 1, 1)
        exposureRowLayout.addWidget(self.__autoExposureCheckBox, 1, 0, 1, 2)
        exposureRowLayout.setColumnStretch(0, 85)
        exposureRowLayout.setColumnStretch(1, 15)
        self.__exposureControl = self.createLabeledComponent("Exposure", exposureRow)
        controlsLayout.addWidget(self.__exposureControl, 1, 0, 1, 2)

        self.__captureButton = QPushButton("Capture reference")
        self.__captureButton.clicked.connect(self.onClickedCapture)
        controlsLayout.addWidget(self.__captureButton, 2, 0, 1, 2)
        # S2: per-frame capture progress is emitted to the app status bar (like auto-exposure) — no inline bar.

        # Reference / Sample acquisition STEPS as a real tab panel whose pane frames the whole step content
        # (S1). The ONE shared inner-tabs + controls widget (§15 Option A) is reparented into the active
        # step's page on tab change — never duplicated.
        self.__stepContent = QWidget()
        stepContentLayout = QVBoxLayout()
        stepContentLayout.setContentsMargins(0, 0, 0, 0)
        stepContentLayout.setSpacing(Metrics.S)
        self.__stepContent.setLayout(stepContentLayout)
        stepContentLayout.addWidget(self.__innerTabs)
        stepContentLayout.addWidget(controls)

        self.__roleTabs = QTabWidget()
        # S10: every QTabWidget keeps its global QTabWidget::pane border — no override here. The role-tabs pane
        # is the OUTER frame of the acquisition step; __innerTabs' pane is the INNER frame around the plot/video
        # (the controls sit below __innerTabs, inside this outer frame). Supersedes S8 ① (which flattened this
        # pane) and S9 (which would have moved the frame onto __stepContent).
        self.__referencePage = self.__stepPage()
        self.__samplePage = self.__stepPage()
        self.__roleTabs.addTab(self.__referencePage, "Reference")
        self.__roleTabs.addTab(self.__samplePage, "Sample")
        self.__roleTabs.tabBar().setDrawBase(False)  # S3: drop the white base line under the inactive tab
        self.__referencePage.layout().addWidget(self.__stepContent)  # start on Reference (index 0)
        self.__roleTabs.currentChanged.connect(self.__onRoleChanged)
        layout.addWidget(self.__roleTabs)
        return panel

    def __stepPage(self):
        # An empty host page for one acquisition step; the shared step-content is reparented in on selection.
        page = QWidget()
        pageLayout = QVBoxLayout()
        pageLayout.setContentsMargins(0, Metrics.S, 0, 0)
        pageLayout.setSpacing(Metrics.S)
        page.setLayout(pageLayout)
        return page

    def __attachStepContent(self, index):
        # Move the single shared step-content widget into the selected step's page (reparent auto-removes it
        # from the previous page). Keeps §15 Option A: one live-video widget + one spectrum plot, not two.
        page = self.__referencePage if index == 0 else self.__samplePage
        if self.__stepContent is not None and self.__stepContent.parentWidget() is not page:
            page.layout().addWidget(self.__stepContent)

    def __roleForTabIndex(self, index):
        return REFERENCE if index == 0 else SAMPLE

    def __buildEvaluationPage(self):
        # E1: EVALUATION is its own phase/page. S4: two step-tabs — Metrics | Spectrum — so the metric list and
        # the bands plot no longer compete for height (no vertical scrollbar). Populated by __runEvaluation.
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, Metrics.S, 0, 0)
        page.setLayout(layout)
        self.__evaluationTabs = QTabWidget()
        layout.addWidget(self.__evaluationTabs)
        return page

    def __buildProcessingPage(self):
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, Metrics.S, 0, 0)
        page.setLayout(layout)
        self.__processingTabs = QTabWidget()
        layout.addWidget(self.__processingTabs)
        return page

    def __buildPublishingPage(self):
        # L6: the PUBLISHING phase page — a "Send to LIMS" step-tab. Populated by __runPublishing; the page
        # exists in the stack even when the plugin declares no publishing step (then it is simply never shown).
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, Metrics.S, 0, 0)
        page.setLayout(layout)
        self.__publishingTabs = QTabWidget()
        layout.addWidget(self.__publishingTabs)
        return page

    # --- lifecycle ---

    def showEvent(self, event):
        super().showEvent(event)
        # React only to real navigation TO the bench (non-spontaneous). A spontaneous show is a window-system
        # event — a virtual-desktop switch back, minimise/restore — and must NOT restart the run (which resets
        # to ACQUISITION) or re-open the camera; the stream is still live from before (Edwin's desktop-switch bug).
        if not event.spontaneous():
            self.__startRun()

    def hideEvent(self, event):
        super().hideEvent(event)
        # Symmetric: only free the camera + restore the ROI when actually navigating AWAY (non-spontaneous).
        # A spontaneous hide (leaving the desktop) leaves the stream running and the cursor/ROI intact so
        # returning is a no-op.
        if not event.spontaneous():
            self.__stopStream()
            self.__restoreRoi()  # leaving the view restores the authored ROI (never persisted; §12.4)

    def __startRun(self):
        # Reset run state.
        self.__restoreRoi()  # defensive: never start a run with a leftover widened ROI
        self.__cursor = 0
        self.__activeRole = REFERENCE
        self.__lockedExposure = None
        self.__roleSpectra = {}
        self.__representativeFrames = {}
        self.__latestImage = None

        # The user may have just authored the calibration (Save writes it on the server and does NOT
        # refresh the in-memory active profile). Re-fetch the current profile from the server by the
        # session's serial so the precondition below sees a freshly-calibrated setup (SPEC §11).
        ActiveSpectrometerProfileLogicModule().installFromSession()

        if not self.__hasCalibratedSetup():
            # D1 — in-window inline dialog; then back to Settings (instrument setup lives there).
            InWindowDialog.notify(self, "Calibration required",
                                  "No calibrated spectrometer setup is active. Set up and calibrate the "
                                  "spectrometer in Settings, then reopen the measurement bench.")
            self.__goToSettings()
            return

        self.__resolveCamera()
        self.__engine = SpectralWorkflowEngine(self.__selectedPluginClass())  # P7: the selected plugin
        self.__workflow = self.__engine.getWorkflow()
        self.__engine.runPhaseHook(SpectralWorkflowPhaseType.ACQUISITION)  # declares REFERENCE + SAMPLE
        self.__engine.runPhaseHook(SpectralWorkflowPhaseType.PUBLISHING)   # L6: static; detect if the plugin declares it

        self.__phases = [SpectralWorkflowPhaseType.ACQUISITION, SpectralWorkflowPhaseType.PROCESSING,
                         SpectralWorkflowPhaseType.EVALUATION]
        labels = ["Acquisition", "Processing", "Evaluation"]
        if not self.__engine.isSkipped(SpectralWorkflowPhaseType.PUBLISHING):
            self.__phases.append(SpectralWorkflowPhaseType.PUBLISHING)
            labels.append("Publishing")
        self.__stepBar.setSteps(labels)
        self.__syncExposureToSensor()
        self.__roleTabs.blockSignals(True)
        self.__roleTabs.setCurrentIndex(0)  # start on Reference
        self.__roleTabs.blockSignals(False)
        self.__attachStepContent(0)  # defensive: ensure the shared content sits in the Reference page
        self.__applyPluginAcquisitionLabels()  # P6-lite: role-tab + capture-button wording from the plugin's steps
        self.__applyCaptureControlVisibility()  # plugin decides if frame/exposure controls are shown (Edwin)
        self.__innerTabs.setCurrentIndex(self.__IMAGE_TAB)  # start on the live camera image
        self.__spectrumPlot.plotSpectrum(None, title="Reference")
        self.__renderPhase()
        self.__startStream()

    def __hasCalibratedSetup(self):
        profile = ApplicationContextLogicModule().getApplicationSettings().getSpectrometerProfile()
        if profile is None:
            return False
        calibration = getattr(profile, "spectrometerCalibrationProfile", None)
        return calibration is not None and getattr(calibration, "interpolationCoefficientA", None) is not None

    def __resolveCamera(self):
        profile = ApplicationContextLogicModule().getApplicationSettings().getSpectrometerProfile()
        try:
            self.__sensor = profile.spectrometer.spectrometerSensor
        except AttributeError:
            self.__sensor = None
        self.__resolvedIndex = self.__resolver.resolveCaptureIndex(self.__sensor)
        # S7: no inline status line. Connected → the header connection indicator (green) already shows it, so
        # just clear any stale message; the not-connected/virtual/no-sensor diagnostic goes to the app status bar.
        if self.__sensor is None:
            self.__emitStatusMessage("The active setup has no camera device — re-run instrument setup.")
        elif self.__sensor.isVirtual:
            self.__emitStatusMessage("The active setup is a virtual device; the bench needs a real camera.")
        elif self.__resolvedIndex is None:
            self.__emitStatusMessage("Not connected — no %s:%s camera found. Plug the device directly into a "
                                     "USB port (not a hub) and reopen this view."
                                     % (self.__sensor.vendorId, self.__sensor.modelId))
        else:
            self.__clearStatus()

    def __emitStatusMessage(self, text):
        # S7: a plain (non-progress) message in the app status bar — value 0, text = message (mirrors the
        # resting "ready for action..." look). Used for the bench's not-connected diagnostics.
        signal = ApplicationStatusSignal()
        signal.isStatusReset = False
        signal.stepsCount = 1
        signal.currentStepIndex = 0
        signal.text = text
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(signal)

    # --- rendering / navigation ---

    def __renderPhase(self):
        phaseType = self.__phases[self.__cursor]
        self.__stack.setCurrentIndex(self.__cursor)
        self.__stepBar.setCurrentIndex(self.__cursor)
        if phaseType == SpectralWorkflowPhaseType.ACQUISITION:
            self.__plotActiveRole()
        self.__refreshNav()

    def __refreshNav(self):
        terminal = self.__cursor >= len(self.__phases) - 1
        # Back only from the 2nd phase (PROCESSING) onward — on the first phase (ACQUISITION) there is nowhere
        # to go back to; use Cancel to leave (Edwin).
        self.__backButton.setVisible(self.__cursor > 0)
        self.__backButton.setEnabled(self.__cursor > 0)
        self.__nextButton.setText("Close" if terminal else "Next →")
        if terminal:
            self.__nextButton.setEnabled(True)
        else:
            self.__nextButton.setEnabled(self.__acquisitionComplete())
        self.__updateControls()

    def __acquisitionComplete(self):
        return REFERENCE in self.__roleSpectra and SAMPLE in self.__roleSpectra

    def onClickedBack(self):
        if self.__cursor > 0:
            self.__cursor -= 1
            self.__renderPhase()
            if self.__phases[self.__cursor] == SpectralWorkflowPhaseType.ACQUISITION:
                self.__startStream()
        else:
            self.__goToSettings()

    def onClickedNext(self):
        phaseType = self.__phases[self.__cursor]
        if phaseType == SpectralWorkflowPhaseType.ACQUISITION:
            if not self.__acquisitionComplete():
                return
            self.__stopStream()
            self.__runProcessing()
            self.__cursor = 1
            self.__renderPhase()
        elif phaseType == SpectralWorkflowPhaseType.PROCESSING:
            self.__runEvaluation()               # E1: EVALUATION is its own phase
            self.__cursor = 2
            self.__renderPhase()
        elif phaseType == SpectralWorkflowPhaseType.EVALUATION:
            if SpectralWorkflowPhaseType.PUBLISHING in self.__phases:
                self.__runPublishing()           # L6: PUBLISHING is its own phase when the plugin declares it
                self.__cursor = self.__phases.index(SpectralWorkflowPhaseType.PUBLISHING)
                self.__renderPhase()
            else:
                self.__goToSettings()
        else:  # PUBLISHING -> terminal
            self.__goToSettings()

    # --- capture ---

    def onClickedCapture(self):
        if self.__resolvedIndex is None or self.__videoThread is None or self.__autoExposing:
            return
        role = self.__activeRole
        if role == REFERENCE and self.__autoExposureCheckBox.isChecked():
            self.__runAutoExposure()

        frameCount = int(self.__framesComboBox.currentText())
        self.__innerTabs.setCurrentIndex(self.__SPECTRUM_TAB)   # watch the spectra build (F1/E3)
        self.__beginCaptureProgress(frameCount)
        self.__waitForFirstFrame()

        # Per-frame loop (F1, SPEC §16.1): grab → extract → re-plot traces-so-far + running mean → step the
        # progress bar. The event-loop pump between frames is what paints the progress + live plot.
        images = []
        spectrum = None
        for i in range(frameCount):
            self.__pumpFrames(120)  # let the stream advance a frame
            if self.__latestImage is None:
                continue
            image = self.__latestImage.copy()  # detach from the live numpy buffer (RD-2)
            images.append(image)
            if spectrum is None:
                # Widen the ROI to the bench analysis window before the FIRST extraction — needs the real
                # raster width to clamp 700 nm to the sensor edge (§12). Idempotent; restored on leave.
                self.__applyExtendedRoi(image.width())
            signal = SpectralVideoThreadSignal()
            signal.image = image
            parameters = ImageSpectrumAcquisitionLogicModuleParameters()
            parameters.setVideoSignal(signal)
            parameters.spectrum = spectrum
            spectrum = ImageSpectrumAcquisitionLogicModule().execute(parameters).spectrum
            self.__plotRoleSpectrum(role, spectrum)  # live: frame traces so far + running mean
            self.__stepCaptureProgress(i + 1)

        self.__endCaptureProgress()
        if not images or spectrum is None:
            InWindowDialog.notify(self, "Capture failed", "No frames were delivered by the camera.")
            return

        step = self.__stepForRole(role)
        container = SpectraContainer()
        container.addToSpectra(spectrum, role)
        step.setContainer(container)

        self.__roleSpectra[role] = spectrum
        self.__representativeFrames[role] = images[len(images) // 2]

        if role == REFERENCE:
            self.__lockedExposure = self.__exposureSlider.value()
            # N2 — a fresh reference re-locks exposure; any earlier sample no longer matches.
            if SAMPLE in self.__roleSpectra:
                self.__roleSpectra.pop(SAMPLE, None)
                self.__representativeFrames.pop(SAMPLE, None)
                self.__stepForRole(SAMPLE).setContainer(None)

        self.__plotActiveRole()
        self.__innerTabs.setCurrentIndex(self.__SPECTRUM_TAB)  # E3: after a capture, reveal the spectrum
        self.__refreshNav()

    def __stepForRole(self, role):
        phase = self.__workflow.getPhase(SpectralWorkflowPhaseType.ACQUISITION)
        for step in phase.getSteps().values():
            if step.getRole() == role:
                return step
        return None

    # P6-lite: the acquisition WORDING is plugin-driven — role-tab labels come from the declared step labels and
    # the Measure-button text from the step's CaptureView.captureLabel (so Pumpkin shows "Isopropanol (reference)"
    # etc.). The capture machinery (video/exposure/ROI/§15 reparenting) is unchanged. (TODO P6: the CaptureView
    # prompt has no home since S7 removed the hint label; full capture-path migration remains.)
    def __captureLabelForRole(self, role):
        step = self.__stepForRole(role)
        view = step.getView() if step is not None else None
        label = getattr(view, "captureLabel", None) if view is not None else None
        return label or ("Capture reference" if role == REFERENCE else "Capture sample")

    def __applyPluginAcquisitionLabels(self):
        refStep = self.__stepForRole(REFERENCE)
        sampleStep = self.__stepForRole(SAMPLE)
        if refStep is not None and refStep.getLabel():
            self.__roleTabs.setTabText(0, refStep.getLabel())
        if sampleStep is not None and sampleStep.getLabel():
            self.__roleTabs.setTabText(1, sampleStep.getLabel())
        self.__captureButton.setText(self.__captureLabelForRole(self.__activeRole))

    def __applyCaptureControlVisibility(self):
        # The plugin's CaptureView decides whether the dev capture chrome is shown (Edwin): the frame-count and
        # exposure/auto-exposure controls are hidden by default (end-user plugins), and the master dev plugin
        # opts them back in. Both acquisition steps carry the same flags, so read the reference step's view.
        step = self.__stepForRole(REFERENCE)
        view = step.getView() if step is not None else None
        showFrames = bool(getattr(view, "showFramesControl", False))
        showExposure = bool(getattr(view, "showExposureControls", False))
        if self.__framesControl is not None:
            self.__framesControl.setVisible(showFrames)
        if self.__exposureControl is not None:
            self.__exposureControl.setVisible(showExposure)

    def __plotActiveRole(self):
        self.__plotRoleSpectrum(self.__activeRole, self.__roleSpectra.get(self.__activeRole))

    def __plotRoleSpectrum(self, role, spectrum):
        # Plot a role's per-frame traces + running mean on the shared spectrum plot. Called live per frame
        # during capture (F1) and once after (from __plotActiveRole).
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

    # --- capture progress bar (F1) ---

    def __beginCaptureProgress(self, total):
        # S2: capture progress is emitted to the app status bar (same path as auto-exposure), not an inline bar.
        self.__captureTotal = max(1, total)

    def __stepCaptureProgress(self, value):
        roleText = "reference" if self.__activeRole == REFERENCE else "sample"
        signal = ApplicationStatusSignal()
        signal.isStatusReset = False
        signal.stepsCount = self.__captureTotal
        signal.currentStepIndex = min(value, self.__captureTotal)
        signal.text = "Capturing %s frame %d / %d" % (roleText, signal.currentStepIndex, self.__captureTotal)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(signal)

    def __endCaptureProgress(self):
        self.__clearStatus()

    def __meanSpectrum(self, spectrum):
        parameters = MeanSpectrumLogicModuleParameters()
        parameters.setSpectrum(spectrum)
        return MeanSpectrumLogicModule().meanSpectrum(parameters).getSpectrum()

    # --- processing ---

    def __runProcessing(self):
        phase = self.__workflow.getPhase(SpectralWorkflowPhaseType.PROCESSING)
        phase.getSteps().clear()  # idempotent if the user came Back then Next again
        self.__engine.runPhaseHook(SpectralWorkflowPhaseType.PROCESSING)

        # P5: plugin steps render generically through the shared WorkflowPhaseRenderer (the "Spectra" overlay
        # is now a declared multi-trace SpectrumPlotView). The raster inspection tabs stay host dev chrome for
        # now — TODO P5 raster-as-SpectrumCaptureView (the captured frame is host-only, not in the model).
        self.__processingTabs.clear()
        self.__processingTabs.addTab(self.__rasterTab(REFERENCE), "Reference raster")
        self.__processingTabs.addTab(self.__rasterTab(SAMPLE), "Sample raster")
        renderer = WorkflowPhaseRenderer()
        for step in phase.getSteps().values():
            content = renderer.renderStep(step)
            if content is not None:
                self.__processingTabs.addTab(content, step.getLabel())

    # --- evaluation (own phase — E1) ---

    def __runEvaluation(self):
        # P4: EVALUATION is fully plugin-driven — the plugin declares Metrics + Spectrum steps and the shared
        # WorkflowPhaseRenderer renders each as a step-tab (was: host-built Metrics scroll + host-drawn bands
        # plot with DevSpectralPlugin's constants). Idempotent on Back-then-Next.
        evaluationPhase = self.__workflow.getPhase(SpectralWorkflowPhaseType.EVALUATION)
        evaluationPhase.getSteps().clear()
        self.__engine.runPhaseHook(SpectralWorkflowPhaseType.EVALUATION)

        self.__evaluationTabs.clear()
        steps = list(evaluationPhase.getSteps().values())
        if not steps:
            placeholder = QWidget()
            placeholderLayout = QVBoxLayout()
            placeholder.setLayout(placeholderLayout)
            placeholderLayout.addWidget(QLabel("No evaluation produced (insufficient signal)."))
            self.__evaluationTabs.addTab(placeholder, "Metrics")
            return
        renderer = WorkflowPhaseRenderer()
        for step in steps:
            view = step.getView() if hasattr(step, "getView") else None
            if isinstance(view, ReportView):
                # M2: the plugin-declared Report step → a matplotlib preview (that IS the PDF) + Save action.
                # Fill the acquisition captures with the real frames first so they render + embed (§5b).
                self.__fillReportCaptures()
                content = self.__buildReportTab(view)
            else:
                content = renderer.renderStep(step)
            if content is not None:
                self.__evaluationTabs.addTab(content, step.getLabel())

    # --- report (M2 — SPEC_bench_pdf_export.md §1/§6) ---

    def __fillReportCaptures(self):
        # Inject the host-owned acquisition data into the plugin-declared, report-flagged views on the
        # acquisition steps: the captured FRAME into each SpectrumCaptureView (cropped to / masked outside the
        # ROI per its descriptor), and the role's extracted SPECTRUM (mean) into each SpectrumPlotView. The
        # plugin declared presence + flag; the host supplies the pixels/values it alone has.
        acquisition = self.__workflow.getPhase(SpectralWorkflowPhaseType.ACQUISITION)
        if acquisition is None:
            return
        roi = self.__roi()
        for step in acquisition.getSteps().values():
            role = step.getRole()
            frame = self.__representativeFrames.get(role)
            spectrum = self.__roleSpectra.get(role)
            result = step.getEvaluationResult()
            if result is None:
                continue
            for item in result.getItems():
                if isinstance(item, SpectrumCaptureView) and frame is not None:
                    item.image = self.__cropToRoi(frame, roi) if item.cropped \
                        else self.__maskOutsideRoi(frame, roi)
                elif isinstance(item, SpectrumPlotView) and spectrum is not None:
                    item.spectrum = self.__meanSpectrum(spectrum)

    def __buildReportTab(self, reportView):
        from sciens.spectracs.view.spectral.workflow.render.WorkflowReportBuilder import WorkflowReportBuilder
        builder = WorkflowReportBuilder(self.__workflow, reportView).build()
        pixmaps = builder.previewPixmaps()  # rasterise once; reused by the tab preview and the "Open bigger" view
        return _ReportTab(pixmaps,
                          onSave=lambda: self.__onSaveReport(builder),
                          onOpenBigger=lambda: self.__openReportBigger(pixmaps))

    def __openReportBigger(self, pixmaps):
        # Small-device affordance (Edwin): show the PDF preview in a full-window in-window view so it is legible
        # without the tab/pane chrome. A fresh PdfPreviewWidget fits the pages to the whole window width.
        InWindowDialog.showWidget(self, "Report", PdfPreviewWidget(pixmaps))

    def __onSaveReport(self, builder):
        # Native save dialog (the existing convention — cf. DevCaptureViewModule "save PNG"); bench is
        # desktop/master-only. Append .pdf if missing.
        path, _ = QFileDialog.getSaveFileName(self, "Save report", "measurement_report.pdf", "PDF (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path = path + ".pdf"
        try:
            builder.savePdf(path)
        except Exception as error:
            InWindowDialog.notify(self, "Report failed", "Could not write the PDF:\n%s" % error)
            return
        InWindowDialog.notify(self, "Report saved", "Saved the PDF report to:\n%s" % path)

    # --- publishing (L6 — SPEC_lims_integration.md §3) ---

    def __runPublishing(self):
        # Render the plugin's PUBLISHING step(s). A LimsPublishView step becomes a "Send to LIMS" tab with a
        # Publish button; the click builds the M2 PDF and calls the server publish RPC. Idempotent on Back/Next.
        phase = self.__workflow.getPhase(SpectralWorkflowPhaseType.PUBLISHING)
        phase.getSteps().clear()
        self.__engine.runPhaseHook(SpectralWorkflowPhaseType.PUBLISHING)
        self.__publishingTabs.clear()
        for step in phase.getSteps().values():
            view = step.getView() if hasattr(step, "getView") else None
            if isinstance(view, LimsPublishView):
                tab = _PublishTab(view)
                tab.publishButton.clicked.connect(
                    lambda checked=False, t=tab, v=view: self.__onPublish(t, v))
                self.__publishingTabs.addTab(tab, step.getLabel())

    def __onPublish(self, tab, view):
        tab.setBusy("Publishing to LIMS…")
        pdfBytes = self.__buildReportPdfBytes()
        if pdfBytes is None:
            tab.setResult(False, "No report is available to publish (run the evaluation first).")
            return
        userId = CurrentUserSession().userId
        result = SpectracsPyServerClient().publishSampleToLims(userId, view.toPluginLimsInfo(), pdfBytes)
        if result.get("ok"):
            tab.setResult(True, "Logged to LIMS — sample %s" % result.get("sampleId"))
        else:
            tab.setResult(False, result.get("message") or "Publish failed")

    def __buildReportPdfBytes(self):
        # Build the same M2 PDF the Report tab shows, as bytes, for the publish RPC. Reuses the EVALUATION
        # ReportView + fills the acquisition captures first (as the Report tab does).
        from sciens.spectracs.view.spectral.workflow.render.WorkflowReportBuilder import WorkflowReportBuilder
        evaluation = self.__workflow.getPhase(SpectralWorkflowPhaseType.EVALUATION)
        reportView = None
        for step in evaluation.getSteps().values():
            view = step.getView() if hasattr(step, "getView") else None
            if isinstance(view, ReportView):
                reportView = view
                break
        if reportView is None:
            return None
        self.__fillReportCaptures()
        return WorkflowReportBuilder(self.__workflow, reportView).build().pdfBytes()

    def __onPluginChanged(self, index):
        # P7: switch the plugin driving the bench and restart the run (only once the view is built).
        if 0 <= index < len(self.__pluginClasses):
            self.__selectedPluginClass = self.__pluginClasses[index]
            if self.__stack is not None:
                self.__stopStream()
                self.__startRun()

    def __rasterTab(self, role):
        # I1: the full masked frame and the cropped ROI go into TWO sub-tabs (one image each → fits the
        # panel width AND height, no scrollbar) instead of stacking both in a scrolled column.
        image = self.__representativeFrames.get(role)
        if image is None:
            return QLabel("No captured frame.")
        roi = self.__roi()
        tabs = QTabWidget()
        tabs.addTab(self.__rasterImageTab("Region outside the ROI blacked out (preview only)",
                                          self.__maskOutsideRoi(image, roi)), "Full frame")
        tabs.addTab(self.__rasterImageTab("Cropped to the ROI", self.__cropToRoi(image, roi)), "Cropped ROI")
        return tabs

    def __rasterImageTab(self, caption, image):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(Metrics.M, Metrics.M, Metrics.M, Metrics.M)
        layout.setSpacing(Metrics.S)
        widget.setLayout(layout)
        # Caption on top; the image FILLS the remaining area (stretch factor 1) and ScaledImageLabel fits it to
        # BOTH width and height, centred — a tall 1600x1200 frame no longer overflows the panel height (which
        # pushed the ROI band below the fold → all black when maximized). Supersedes the S12 leading/trailing
        # stretch (the fitted image centres itself within the space).
        layout.addWidget(QLabel(caption))
        layout.addWidget(self.__imageLabel(image), 1)
        return widget

    def __roi(self):
        calibration = ApplicationContextLogicModule().getApplicationSettings() \
            .getSpectrometerProfile().spectrometerCalibrationProfile
        x1 = int(calibration.regionOfInterestX1)
        y1 = int(calibration.regionOfInterestY1)
        x2 = int(calibration.regionOfInterestX2)
        y2 = int(calibration.regionOfInterestY2)
        return QRect(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))

    # --- bench-extended ROI (SPEC_dev_measure_bench.md §12) -----------------------------------------
    # Temporarily widen the IN-MEMORY calibration's X1/X2 to span __NM_MIN..__NM_MAX (clamped to the
    # raster), so both extraction and the raster preview read the wider window with zero pipeline
    # plumbing. Never persisted; restored on leaving the view. Y and the A-D coefficients are untouched.

    def __calibration(self):
        profile = ApplicationContextLogicModule().getApplicationSettings().getSpectrometerProfile()
        return getattr(profile, "spectrometerCalibrationProfile", None) if profile is not None else None

    def __applyExtendedRoi(self, imageWidth):
        if self.__savedRoiX is not None:
            return  # already applied this session (idempotent)
        calibration = self.__calibration()
        if calibration is None:
            return
        x1, x2 = calibration.regionOfInterestX1, calibration.regionOfInterestX2
        if x1 is None or x2 is None:
            return
        newX1, newX2 = ExtendedRoiLogicModule().extendedXBounds(calibration, imageWidth,
                                                             self.__NM_MIN, self.__NM_MAX)
        if newX1 is None or newX2 is None:
            return
        self.__savedRoiX = (x1, x2)  # save originals only once we are actually widening
        calibration.regionOfInterestX1 = int(newX1)
        calibration.regionOfInterestX2 = int(newX2)
        # S6: the "Analysis window: N–N nm" readout was removed (not wanted); the ROI clamp itself stays.

    def __restoreRoi(self):
        if self.__savedRoiX is None:
            return
        calibration = self.__calibration()
        if calibration is not None:
            calibration.regionOfInterestX1, calibration.regionOfInterestX2 = self.__savedRoiX
        self.__savedRoiX = None

    def __maskOutsideRoi(self, image, roi):
        masked = image.copy()
        painter = QPainter(masked)
        black = QColor(0, 0, 0)
        width, height = masked.width(), masked.height()
        painter.fillRect(0, 0, width, roi.top(), black)                                  # above
        painter.fillRect(0, roi.bottom(), width, height - roi.bottom(), black)           # below
        painter.fillRect(0, roi.top(), roi.left(), roi.height(), black)                  # left
        painter.fillRect(roi.right(), roi.top(), width - roi.right(), roi.height(), black)  # right
        painter.end()
        return masked

    def __cropToRoi(self, image, roi):
        return image.copy(roi)

    def __imageLabel(self, image):
        # H2: a resize-aware label that scales the frame to the panel width (no fixed 720 → no H-scrollbar).
        label = ScaledImageLabel()
        label.setImagePixmap(QPixmap.fromImage(image))
        return label

    # --- controls / exposure (mirrors DevCaptureViewModule) ---

    def __onRoleChanged(self):
        index = self.__roleTabs.currentIndex()
        self.__attachStepContent(index)  # bring the shared step-content into the newly-selected step's page
        self.__activeRole = self.__roleForTabIndex(index)
        if self.__activeRole == SAMPLE and self.__lockedExposure is not None:
            self.__exposureSlider.blockSignals(True)
            self.__exposureSlider.setValue(self.__lockedExposure)
            self.__exposureSlider.blockSignals(False)
            self.__updateExposureLabel()
            if self.__videoThread is not None:
                self.__videoThread.setLiveExposure(self.__lockedExposure)
        self.__captureButton.setText(self.__captureLabelForRole(self.__activeRole))
        self.__plotActiveRole()
        self.__updateControls()

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
        onAcquisition = self.__phases[self.__cursor] == SpectralWorkflowPhaseType.ACQUISITION
        connected = self.__resolvedIndex is not None
        streaming = self.__videoThread is not None
        busy = self.__autoExposing
        # Sample role reuses the locked reference exposure: no auto-expose, no manual slider (correctness).
        sampleLocked = self.__activeRole == SAMPLE and self.__lockedExposure is not None
        autoOn = self.__autoExposureCheckBox is not None and self.__autoExposureCheckBox.isChecked()

        self.__captureButton.setEnabled(onAcquisition and connected and streaming and not busy)
        if self.__autoExposureCheckBox is not None:
            self.__autoExposureCheckBox.setEnabled(onAcquisition and not busy and not sampleLocked)
        if self.__exposureSlider is not None:
            self.__exposureSlider.setEnabled(onAcquisition and streaming and not busy
                                             and not autoOn and not sampleLocked)
        if self.__roleTabs is not None:
            # Disable only the TAB BAR (role switching), not the QTabWidget — the page content stays usable.
            self.__roleTabs.tabBar().setEnabled(onAcquisition and not busy)
        if self.__framesComboBox is not None:
            self.__framesComboBox.setEnabled(onAcquisition and not busy)

    # --- streaming ---

    def __startStream(self):
        if self.__videoThread is not None or self.__resolvedIndex is None:
            self.__updateControls()
            return
        self.__latestImage = None
        thread = DevCaptureVideoThread()
        thread.setIsVirtual(False)
        thread.setDeviceId(self.__resolvedIndex)
        exposure = self.__lockedExposure if (self.__activeRole == SAMPLE and self.__lockedExposure is not None) \
            else self.__exposureSlider.value()
        thread.setExposure(exposure)
        thread.setLiveExposure(exposure)
        thread.setFrameCount(0)  # continuous until stop()
        thread.videoThreadSignal.connect(self.handleVideoThreadSignal)
        thread.finished.connect(self.__onThreadFinished)
        self.__videoThread = thread
        thread.start()
        self.__updateControls()
        # NOTE: auto-exposure runs on the Capture click (a user action), NOT here — running the
        # nested-event-loop bisection inside showEvent re-enters the view lifecycle and corrupts the
        # stream thread. The live preview opens at the seeded exposure; Capture auto-exposes then grabs.

    def __stopStream(self):
        if self.__videoThread is not None:
            self.__videoThread.stop()
        self.__updateControls()

    def __onThreadFinished(self):
        self.__videoThread = None
        self.__updateControls()

    def handleVideoThreadSignal(self, event, videoSignal):
        self.__latestImage = videoSignal.image
        if self.__videoViewModule is not None:
            self.__videoViewModule.handleVideoThreadSignal(videoSignal)
            width = videoSignal.image.width() if videoSignal.image is not None else None
            if width is not None and width != getattr(self, '_DevMeasurementBenchViewModule__previewRoiWidth', None):
                self.__previewRoiWidth = width
                self.__applyPreviewRoiOverlay(width)
        event.set()

    def __applyPreviewRoiOverlay(self, imageWidth):
        # Draw the extended 400–700 window on the live acquisition preview — the same window the bench
        # analyses, shared with the capture view (SPEC_dev_measure_bench.md §14).
        calibration = self.__calibration()
        extended = ExtendedRoiLogicModule().extendedRoi(calibration, imageWidth) if calibration is not None else None
        if extended is None:
            self.__videoViewModule.clearRoi()
        else:
            self.__videoViewModule.setRoi(*extended)

    # --- auto-exposure (bisection over the live stream — mirrors DevCaptureViewModule) ---

    def __runAutoExposure(self):
        if self.__videoThread is None or self.__autoExposing:
            return
        self.__autoExposing = True
        if self.__innerTabs is not None:
            self.__innerTabs.setCurrentIndex(self.__IMAGE_TAB)  # E3: watch the frame while exposure converges
        self.__updateControls()
        self.__waitForFirstFrame()
        probe = {"i": 0}

        def measure(exposure):
            probe["i"] += 1
            self.__emitAutoExposeProgress(probe["i"])
            self.__exposureSlider.setValue(exposure)
            self.__pumpFrames(350)
            return self.__brightness(self.__latestImage)

        try:
            result = AutoExposureLogicModule().findExposure(
                measure, self.__EXPOSURE_MIN, self.__EXPOSURE_MAX, iterations=self.__AUTO_EXPOSE_MAX_PROBES)
            self.__exposureSlider.setValue(result)
        finally:
            self.__autoExposing = False
            self.__clearStatus()
            self.__updateControls()

    def __waitForFirstFrame(self):
        for _ in range(12):
            if self.__latestImage is not None:
                return
            self.__pumpFrames(150)

    def __emitAutoExposeProgress(self, probeIndex):
        signal = ApplicationStatusSignal()
        signal.isStatusReset = False
        signal.stepsCount = self.__AUTO_EXPOSE_MAX_PROBES
        signal.currentStepIndex = min(probeIndex, self.__AUTO_EXPOSE_MAX_PROBES)
        signal.text = "Auto-exposing… finding best exposure [%d/%d]" % (signal.currentStepIndex,
                                                                        self.__AUTO_EXPOSE_MAX_PROBES)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(signal)

    def __clearStatus(self):
        signal = ApplicationStatusSignal()
        signal.isStatusReset = True
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(signal)

    def __pumpFrames(self, milliseconds):
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

    # --- navigation ---

    def __goToSettings(self):
        self.__stopStream()
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        signal = NavigationSignal(None)
        signal.setTarget("SettingsViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(signal)


class _ReportTab(QWidget):
    # The EVALUATION Report step's tab body (SPEC_bench_pdf_export.md §1): a Save row + the fit-to-width PDF
    # preview, with NO padding (the preview hugs the pane). An "Open bigger" button (Edwin) opens the same pages
    # in a full-window in-window view where the tab/pane chrome is gone and the pages get the whole window width.
    # Offered on EVERY device — on the phone to escape the cramped tab, on desktop to inspect a page up close.

    def __init__(self, pixmaps, onSave, onOpenBigger):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)   # no padding — the preview spans the full width (Edwin)
        layout.setSpacing(Metrics.S)
        self.setLayout(layout)

        buttonRow = QWidget()
        buttonRowLayout = QHBoxLayout()
        buttonRowLayout.setContentsMargins(0, 0, 0, 0)
        buttonRowLayout.setSpacing(Metrics.S)
        buttonRow.setLayout(buttonRowLayout)
        saveButton = QPushButton("Save PDF…")
        saveButton.clicked.connect(lambda: onSave())
        buttonRowLayout.addWidget(saveButton, 1)
        openBiggerButton = QPushButton("Open bigger")
        openBiggerButton.setProperty("buttonType", "secondary")
        openBiggerButton.clicked.connect(lambda: onOpenBigger())
        buttonRowLayout.addWidget(openBiggerButton, 1)
        layout.addWidget(buttonRow)

        layout.addWidget(PdfPreviewWidget(pixmaps), 1)


class _PublishTab(QWidget):
    # L6 (SPEC_lims_integration.md §3): the PUBLISHING "Send to LIMS" step body — a short summary of what will
    # be sent, a Publish button, and a status line the host updates with the returned sample id (or the error).

    def __init__(self, view):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(Metrics.M, Metrics.M, Metrics.M, Metrics.M)
        layout.setSpacing(Metrics.S)
        self.setLayout(layout)

        analyses = ", ".join(analysis.get("name", "") for analysis in view.analyses) or "—"
        summary = QLabel("Send this measurement to the LIMS as a new sample.\n"
                         "Sample type: %s     Analyses: %s" % (view.sampleTypeName, analyses))
        summary.setWordWrap(True)
        layout.addWidget(summary)

        self.publishButton = QPushButton("Publish to LIMS")
        layout.addWidget(self.publishButton)

        self.__status = QLabel("")
        self.__status.setWordWrap(True)
        layout.addWidget(self.__status)
        layout.addStretch(1)

    def setBusy(self, message):
        self.publishButton.setEnabled(False)
        self.__status.setText(message)

    def setResult(self, ok, message):
        self.publishButton.setEnabled(True)
        self.__status.setText(("✓ " if ok else "✗ ") + message)
