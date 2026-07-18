import numpy as np
import pyqtgraph as pg

from PySide6.QtCore import QRect
from PySide6.QtGui import QPixmap, QImage, QColor, QPainter, QIcon
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QSlider, QCheckBox, QTabWidget, QStackedWidget, QScrollArea, QFrame, QSizePolicy, QFileDialog

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.application.style.Metrics import Metrics
from sciens.spectracs.logic.application.video.capture.SensorCaptureIndexResolver import SensorCaptureIndexResolver
from sciens.spectracs.logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModule import ImageSpectrumAcquisitionLogicModule
from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModule import MeanSpectrumLogicModule
from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModuleParameters import MeanSpectrumLogicModuleParameters
from sciens.spectracs.logic.session.ActiveSpectrometerProfileLogicModule import ActiveSpectrometerProfileLogicModule
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
from sciens.spectracs.logic.spectral.plugin.PluginRegistry import PluginRegistry
from sciens.spectracs.logic.spectral.workflow.SpectralWorkflowEngine import SpectralWorkflowEngine
from sciens.spectracs.model.application.applicationStatus.ApplicationStatusSignal import ApplicationStatusSignal
from sciens.spectracs.view.spectral.workflow.AcquisitionGuidance import AcquisitionGuidance
from sciens.spectracs.view.spectral.workflow.CapturePanel import CapturePanel
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.model.spectral.plugin.view.ReportView import ReportView
from sciens.spectracs.model.spectral.plugin.view.LimsPublishView import LimsPublishView
from sciens.spectracs.model.spectral.plugin.view.SpectrumCaptureView import SpectrumCaptureView
from sciens.spectracs.model.spectral.plugin.view.SpectrumPlotView import SpectrumPlotView
from sciens.spectracs.plugin_sdk.roles import REFERENCE, SAMPLE
from sciens.spectracs.view.application.widgets.InWindowDialog import InWindowDialog
from sciens.spectracs.view.application.widgets.ScaledImageLabel import ScaledImageLabel
from sciens.spectracs.view.application.widgets.PdfPreviewWidget import PdfPreviewWidget
from sciens.spectracs.view.application.widgets.StepBarWidget import StepBarWidget
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget
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

        self.__engine = None
        self.__workflow = None
        # P7: which plugin drives the bench (master-selectable, decoupled from SpectrometerSetup). A1: the
        # bench enumerates the PluginRegistry (all entries, incl. the benchOnly Dev plugin) instead of a
        # hard-coded class list, and resolves a codeRef to an instance per run.
        self.__pluginEntries = PluginRegistry.entries()
        self.__selectedCodeRef = self.__pluginEntries[0].codeRef
        self.__pluginSelect = None
        self.__cursor = 0
        self.__phases = [SpectralWorkflowPhaseType.ACQUISITION, SpectralWorkflowPhaseType.PROCESSING,
                         SpectralWorkflowPhaseType.EVALUATION]


        # widgets
        self.__messageLabel = None
        self.__stepBar = None
        self.__stack = None
        self.__capturePanel = None          # S2c: the shared CapturePanel (built per run in __startRun)
        self.__acquisitionContainer = None  # its host page in the phase stack
        self.__captureButton = None
        self.__guidance = AcquisitionGuidance()   # shared guidance primitives (S1a); painters/emit live here
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
        for entry in self.__pluginEntries:
            self.__pluginSelect.addItem(entry.title)
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
        self.__backButton.setObjectName("DevMeasurementBenchViewModule.backButton")  # SPEC_doc_automation §7.1
        self.__backButton.clicked.connect(self.onClickedBack)
        layout.addWidget(self.__backButton, 0, 0, 1, 1)
        self.__cancelButton = QPushButton("Cancel")
        self.__cancelButton.setProperty("buttonType", "secondary")
        self.__cancelButton.clicked.connect(self.__goToSettings)
        layout.addWidget(self.__cancelButton, 0, 1, 1, 1)
        self.__nextButton = QPushButton("Next →")
        self.__nextButton.setObjectName("DevMeasurementBenchViewModule.nextButton")  # SPEC_doc_automation §7.1
        self.__nextButton.clicked.connect(self.onClickedNext)
        layout.addWidget(self.__nextButton, 0, 2, 1, 1)
        return result

    # --- acquisition panel (role tab-bar + shared [Captured image | Spectrum] — Option A, §15) ---

    __IMAGE_TAB = 0
    __SPECTRUM_TAB = 1

    def __buildAcquisitionPanel(self):
        # S2c: the acquisition UI is the shared CapturePanel now, built per run in __startRun (it needs the
        # plugin's declared steps). This returns just its host container in the phase stack; the legacy inline
        # capture UI below is dead (renamed, never called — S4b removes it).
        self.__acquisitionContainer = QWidget()
        containerLayout = QVBoxLayout()
        containerLayout.setContentsMargins(0, Metrics.S, 0, 0)
        containerLayout.setSpacing(Metrics.S)
        self.__acquisitionContainer.setLayout(containerLayout)
        return self.__acquisitionContainer

    def __buildEvaluationPage(self):
        # E1: EVALUATION is its own phase/page. S4: two step-tabs — Metrics | Spectrum — so the metric list and
        # the bands plot no longer compete for height (no vertical scrollbar). Populated by __runEvaluation.
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, Metrics.S, 0, 0)
        page.setLayout(layout)
        self.__evaluationTabs = QTabWidget()
        self.__evaluationTabs.setObjectName("DevMeasurementBenchViewModule.evaluationTabs")  # doc-automation §16
        layout.addWidget(self.__evaluationTabs)
        return page

    def __buildProcessingPage(self):
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, Metrics.S, 0, 0)
        page.setLayout(layout)
        self.__processingTabs = QTabWidget()
        self.__processingTabs.setObjectName("DevMeasurementBenchViewModule.processingTabs")  # doc-automation §16
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
        self.__publishingTabs.setObjectName("DevMeasurementBenchViewModule.publishingTabs")  # doc-automation §16
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
        self.__engine = SpectralWorkflowEngine(PluginRegistry.resolve(self.__selectedCodeRef))  # P7: selected plugin
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
        self.__buildCapturePanel()   # S2c: the shared CapturePanel replaces the bench's inline capture UI
        self.__renderPhase()
        self.__capturePanel.startStream()

    def __buildCapturePanel(self):
        # S2c: (re)build the shared CapturePanel for this run's acquisition steps and swap it into the phase
        # stack's acquisition page. One panel per run; the plugin's CaptureView flags drive its dev-chrome.
        self.__capturePanel = CapturePanel(
            self.__acquisitionSteps(), self.__engine,
            onCaptured=self.__onCaptured, onRoleChanged=self.__refreshGuidance,
            onCaptureFailed=self.__onCaptureFailed)
        layout = self.__acquisitionContainer.layout()
        while layout.count():
            widget = layout.takeAt(0).widget()
            if widget is not None:
                widget.deleteLater()
        layout.addWidget(self.__capturePanel)

    def __acquisitionSteps(self):
        if self.__workflow is None:
            return []
        phase = self.__workflow.getPhase(SpectralWorkflowPhaseType.ACQUISITION)
        return [step for step in phase.getSteps().values() if step.getRole() is not None]

    def __onCaptured(self, step):
        # A role finished capturing (CapturePanel callback) — refresh nav (Next enables once both captured) + guidance.
        self.__refreshNav()

    def __onCaptureFailed(self):
        InWindowDialog.notify(self, "Capture failed", "No frames were delivered by the camera.")

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
        self.__setNextButtonLabel("Close", terminal)
        if terminal:
            self.__nextButton.setEnabled(True)
        else:
            self.__nextButton.setEnabled(self.__acquisitionComplete())
        self.__updateControls()
        self.__refreshGuidance()

    def __setNextButtonLabel(self, terminalText, terminal):
        # Permanent muted-amber ▶ on the proceed action (dims when disabled, brightens when enabled); terminal
        # actions (Close) drop the arrow. See SPEC_acquisition_guidance.
        if terminal:
            self.__nextButton.setText(terminalText)
            self.__nextButton.setIcon(QIcon())
        else:
            self.__nextButton.setText("Next")
            self.__nextButton.setIcon(self.__amberArrowIcon())

    def __acquisitionComplete(self):
        steps = self.__acquisitionSteps()
        return len(steps) > 0 and all(step.getContainer() is not None for step in steps)

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
    def __plotActiveRole(self):
        if self.__capturePanel is not None:
            self.__capturePanel.plotActiveRole()

    # --- acquisition guidance (SPEC_acquisition_guidance.md — Decision B: the bench host renders it too, until
    # the capture-panel convergence lets both hosts share ONE path). Mirrors WizardViewModule, bound to the
    # bench's single capture button + Reference/Sample role-tabs. Reuses `__clearStatus` as the coach reset. ---

    def __refreshGuidance(self):
        panel = self.__capturePanel
        inAcquisition = (self.__workflow is not None
                         and self.__phases[self.__cursor] == SpectralWorkflowPhaseType.ACQUISITION)
        if inAcquisition:
            if panel is None or not panel.isCameraReady():
                # Camera not ready — leave the not-connected diagnostic in place; no coach/amber.
                if panel is not None:
                    self.__setButtonDot(panel.getCaptureButton(), False)
                return
            action = self.__guidanceAction()
            self.__applyGuidanceHighlights(action)
            self.__emitGuidance(action["coach"])  # verbatim plugin prompt, or None -> resting when all captured
            return
        # A computed phase — no amber; show the plugin's authored phase hint (if any), else clear the coach line.
        if panel is not None:
            self.__setButtonDot(panel.getCaptureButton(), False)
        phase = self.__workflow.getPhase(self.__phases[self.__cursor]) if self.__workflow is not None else None
        self.__emitGuidance(phase.getHint() if phase is not None else None)

    def __guidanceAction(self):
        # S4a: the derivation is shared (AcquisitionGuidance.deriveAction). Host only supplies the steps + the
        # "all captured" completion hint.
        phase = self.__workflow.getPhase(SpectralWorkflowPhaseType.ACQUISITION) \
            if self.__workflow is not None else None
        completeHint = phase.getHint() if phase is not None else None
        return self.__guidance.deriveAction(self.__acquisitionSteps(), completeHint)

    def __applyGuidanceHighlights(self, action):
        # S4a: shared CapturePanel highlight logic (the amber cue targets the panel's button + role-tabs).
        if self.__capturePanel is not None:
            self.__guidance.applyPanelHighlights(self.__capturePanel, action)

    # --- the amber cue icons: delegated to the shared AcquisitionGuidance util (S1a). ---

    def __setButtonDot(self, button, on):
        self.__guidance.setButtonDot(button, on)

    def __amberDotIcon(self):
        return self.__guidance.amberDotIcon()

    def __amberArrowIcon(self):
        return self.__guidance.amberArrowIcon()

    def __emitGuidance(self, text):
        # Plugin/guidance text → muted-amber font, no progress bar. A None/empty text rests the bar instead.
        self.__guidance.emit(text)

    # --- capture progress bar (F1) ---

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
            frame = self.__capturePanel.getRepresentativeFrame(role) if self.__capturePanel is not None else None
            container = step.getContainer()
            spectrum = container.getSpectra().get(role) if container is not None else None
            result = step.getEvaluationResult()
            if result is None:
                continue
            for item in result.getItems():
                if isinstance(item, SpectrumCaptureView) and frame is not None:
                    item.image = self.__cropToRoi(frame, roi) if item.cropped \
                        else self.__maskOutsideRoi(frame, roi)
                    # S2: the host owns the QImage → Qt-free hand-off. SpectrumCaptureView always said
                    # `.reportImage` is "the Qt-free rendition the host derives from .image"; deriving it here,
                    # where .image is set, is what lets WorkflowReportBuilder stay Qt-free.
                    item.reportImage = self.__qImageToPil(item.image)
                elif isinstance(item, SpectrumPlotView) and spectrum is not None:
                    item.spectrum = self.__meanSpectrum(spectrum)

    @staticmethod
    def __qImageToPil(image):
        # Moved here from WorkflowReportBuilder (S2) unchanged.
        if image is None:
            return None
        from PIL import Image
        qimage = image if isinstance(image, QImage) else \
            (image.toImage() if isinstance(image, QPixmap) else None)
        if qimage is None:
            return None
        qimage = qimage.convertToFormat(QImage.Format.Format_RGBA8888)
        width, height = qimage.width(), qimage.height()
        pointer = qimage.constBits()
        array = np.frombuffer(pointer, np.uint8).reshape(height, qimage.bytesPerLine())
        array = array[:, :width * 4].reshape(height, width, 4)
        return Image.fromarray(array.copy(), "RGBA")

    def __buildReportTab(self, reportView):
        from sciens.spectracs.logic.spectral.report.WorkflowReportBuilder import WorkflowReportBuilder
        builder = WorkflowReportBuilder(self.__workflow, reportView).build()
        pixmaps = self.__previewPixmaps(builder)  # rasterise once; reused by the tab preview and "Open bigger"
        return _ReportTab(pixmaps,
                          onSave=lambda: self.__onSaveReport(builder),
                          onOpenBigger=lambda: self.__openReportBigger(pixmaps))

    @staticmethod
    def __previewPixmaps(builder):
        # S2: the builder hands back matplotlib figures; turning them into something Qt can paint is the host's
        # job. rasterize() is already Qt-free — it returns (width, height, rgba bytes).
        from sciens.spectracs.logic.spectral.report.MatplotlibWorkflowRenderer import MatplotlibWorkflowRenderer
        pixmaps = []
        for figure in builder.figures():
            width, height, rgba = MatplotlibWorkflowRenderer.rasterize(figure)
            image = QImage(rgba, width, height, QImage.Format.Format_RGBA8888).copy()
            pixmaps.append(QPixmap.fromImage(image))
        return pixmaps

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
        from sciens.spectracs.logic.spectral.report.WorkflowReportBuilder import WorkflowReportBuilder
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
        if 0 <= index < len(self.__pluginEntries):
            self.__selectedCodeRef = self.__pluginEntries[index].codeRef
            if self.__stack is not None:
                self.__stopStream()
                self.__startRun()

    def __rasterTab(self, role):
        # I1: the full masked frame and the cropped ROI go into TWO sub-tabs (one image each → fits the
        # panel width AND height, no scrollbar) instead of stacking both in a scrolled column.
        image = self.__capturePanel.getRepresentativeFrame(role) if self.__capturePanel is not None else None
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

        # S6: the "Analysis window: N–N nm" readout was removed (not wanted); the ROI clamp itself stays.

    def __restoreRoi(self):
        if self.__capturePanel is not None:
            self.__capturePanel.restoreRoi()

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

    def __updateControls(self):
        # S2c: the CapturePanel self-manages its own capture/exposure controls now — nothing host-side to do.
        pass

    # --- streaming ---

    def __startStream(self):
        if self.__capturePanel is not None:
            self.__capturePanel.startStream()

    def __stopStream(self):
        if self.__capturePanel is not None:
            self.__capturePanel.stopStream()

    # --- auto-exposure (bisection over the live stream — mirrors DevCaptureViewModule) ---

    def __clearStatus(self):
        self.__guidance.emit(None)

    # --- navigation ---

    def __goToSettings(self):
        # SPEC_acquisition_guidance §4.1: clear the coach line + capture-button cue so nothing lingers in Settings.
        # (The Next arrow is a permanent button icon owned by __refreshNav — no need to clear it on leave.)
        self.__setButtonDot(self.__captureButton, False)
        self.__clearStatus()
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
        self.publishButton.setObjectName("DevMeasurementBenchViewModule.sendToLimsButton")  # SPEC_doc_automation §7.1
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
