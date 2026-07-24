import numpy as np

from PySide6.QtCore import QRect
from PySide6.QtGui import QPixmap, QImage, QColor, QPainter, QIcon
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QTabWidget, QFileDialog

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.application.style.Metrics import Metrics
from sciens.spectracs.logic.application.video.capture.SensorCaptureIndexResolver import SensorCaptureIndexResolver
from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModule import MeanSpectrumLogicModule
from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModuleParameters import MeanSpectrumLogicModuleParameters
from sciens.spectracs.logic.session.ActiveSpectrometerProfileLogicModule import ActiveSpectrometerProfileLogicModule
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
from sciens.spectracs.logic.spectral.plugin.PluginRegistry import PluginRegistry
from sciens.spectracs.model.application.applicationStatus.ApplicationStatusSignal import ApplicationStatusSignal
from sciens.spectracs.view.spectral.workflow.AbstractPluginExecutionView import AbstractPluginExecutionView
from sciens.spectracs.view.spectral.workflow.AcquisitionGuidance import AcquisitionGuidance
from sciens.spectracs.view.spectral.workflow.CapturePanel import CapturePanel
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.model.spectral.plugin.view.ReportView import ReportView
from sciens.spectracs.model.spectral.plugin.view.LimsPublishView import LimsPublishView
from sciens.spectracs.model.spectral.plugin.view.SpectrumCaptureView import SpectrumCaptureView
from sciens.spectracs.model.spectral.plugin.view.SpectrumPlotView import SpectrumPlotView
from sciens.spectracs.plugin_sdk.roles import REFERENCE, SAMPLE
from sciens.spectracs.view.application.widgets.InWindowDialog import InWindowDialog
from sciens.spectracs.view.application.widgets.ScaledImageLabel import ScaledImageLabel
from sciens.spectracs.view.application.widgets.PdfPreviewWidget import PdfPreviewWidget
from sciens.spectracs.view.spectral.workflow.render.WorkflowPhaseRenderer import WorkflowPhaseRenderer


class DevMeasurementBenchViewModule(AbstractPluginExecutionView):
    """Master "Swiss-knife" measurement bench (SPEC_dev_measure_bench.md). A generic real-camera run of the
    same pipeline an end-user plugin drives — capture REFERENCE + SAMPLE, compute transmission + absorption —
    without any use-case verdict. M2 B3: now a thin subclass of AbstractPluginExecutionView (the shared nav +
    save), so the bespoke fixed phase-stack is gone; the bench provides only its master specifics — the plugin
    picker, the real-camera capture + dev-chrome, the raster/report/publish dev tabs, and the acquisition
    guidance. Master-only; runs on a real camera (gates on a calibrated non-virtual setup)."""

    __NM_MIN = 400.0
    __NM_MAX = 700.0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__resolver = SensorCaptureIndexResolver()
        self.__sensor = None
        self.__resolvedIndex = None
        self.__pluginEntries = PluginRegistry.entries()
        self.__selectedEntry = self.__pluginEntries[0]
        self.__pluginSelect = None
        self.__capturePanel = None   # a persistent per-run singleton (holds captured frames for report/raster)
        self.__guidance = AcquisitionGuidance()
        self.__cancelButton = None

    def _getPageTitle(self):
        return "Settings > Development > Measurement bench"

    # --- page scaffold ---

    def getMainContainerWidgets(self):
        base = super().getMainContainerWidgets()   # creates _messageLabel, _stepBar, _tabWidget
        # P7: master-only plugin selector — run ANY plugin on the bench. B6.1: built-ins + DB-published rows.
        self.__pluginEntries = PluginRegistry.listAll()
        self.__selectedEntry = self.__pluginEntries[0]
        self.__pluginSelect = QComboBox()
        for entry in self.__pluginEntries:
            self.__pluginSelect.addItem(self.__entryLabel(entry))
        self.__pluginSelect.currentIndexChanged.connect(self.__onPluginChanged)
        return {
            "message": base["message"],
            "pluginSelect": self.createLabeledComponent("Plugin", self.__pluginSelect),
            "stepBar": base["stepBar"],
            "tabs": base["tabs"],
        }

    def createNavigationGroupBox(self):
        result = super().createNavigationGroupBox()   # Back (col 0) + Next (col 3)
        layout = result.layout()
        self.__cancelButton = QPushButton("Cancel")
        self.__cancelButton.setProperty("buttonType", "secondary")
        self.__cancelButton.clicked.connect(self.__goToSettings)
        layout.addWidget(self.__cancelButton, 0, 1, 1, 1)
        return result

    # --- lifecycle ---

    def showEvent(self, event):
        super().showEvent(event)
        if not event.spontaneous():
            self.__enterRun()

    def hideEvent(self, event):
        super().hideEvent(event)
        if not event.spontaneous():
            self.__stopStream()
            self.__restoreRoi()

    def __enterRun(self):
        self.__restoreRoi()  # defensive: never start with a leftover widened ROI
        # The user may have just authored calibration; re-fetch the active profile by serial (SPEC §11).
        ActiveSpectrometerProfileLogicModule().installFromSession()
        if not self.__hasCalibratedSetup():
            InWindowDialog.notify(self, "Calibration required",
                                  "No calibrated spectrometer setup is active. Set up and calibrate the "
                                  "spectrometer in Settings, then reopen the measurement bench.")
            self.__goToSettings()
            return
        self.__resolveCamera()
        self.__capturePanel = None   # fresh capture panel for this run's engine
        self._startNewRun()          # base: resolve plugin -> engine -> hooks -> plan -> render (builds the panel)

    # --- base seams ---

    def _resolvePlugin(self):
        entry = self.__selectedEntry
        return PluginRegistry.resolve(entry.codeRef, entry.version)

    def _pluginProvenance(self):
        return self.__selectedEntry.codeRef, self.__selectedEntry.version

    def _leave(self):
        self.__goToSettings()

    def _canAdvanceFrom(self, navStop):
        if navStop.phaseType == SpectralWorkflowPhaseType.ACQUISITION:
            return self.__acquisitionComplete()
        return True

    def _beforeRender(self):
        # Stop the live stream before the tab area is cleared, but KEEP the panel object alive — it holds the
        # captured frames the raster/report tabs read after leaving acquisition.
        if self.__capturePanel is not None:
            self.__capturePanel.stopStream()

    def _afterNav(self):
        self.__refreshGuidance()

    def _decorateNav(self, terminal):
        self._nextButton.setIcon(QIcon() if terminal else self.__amberArrowIcon())

    def _renderStop(self, navStop, container):
        phaseType = navStop.phaseType
        if phaseType == SpectralWorkflowPhaseType.ACQUISITION:
            self.__renderAcquisition(container)
        elif phaseType == SpectralWorkflowPhaseType.PROCESSING:
            self.__renderProcessing(container)
        elif phaseType == SpectralWorkflowPhaseType.EVALUATION:
            self.__renderEvaluation(container)
        elif phaseType == SpectralWorkflowPhaseType.PUBLISHING:
            self.__renderPublishing(container)

    # --- acquisition ---

    def __renderAcquisition(self, container):
        if self.__capturePanel is None:
            self.__capturePanel = CapturePanel(
                self.__acquisitionSteps(), self._engine,
                onCaptured=self.__onCaptured, onRoleChanged=self.__refreshGuidance,
                onCaptureFailed=self.__onCaptureFailed)
        container.addTab(self.__capturePanel, "Acquisition")
        self.__capturePanel.startStream()
        self.__capturePanel.plotActiveRole()

    def __acquisitionSteps(self):
        workflow = self._workflow()
        if workflow is None:
            return []
        phase = workflow.getPhase(SpectralWorkflowPhaseType.ACQUISITION)
        return [step for step in phase.getSteps().values() if step.getRole() is not None]

    def __onCaptured(self, step):
        self._refreshNav()

    def __onCaptureFailed(self):
        InWindowDialog.notify(self, "Capture failed", "No frames were delivered by the camera.")

    def __acquisitionComplete(self):
        steps = self.__acquisitionSteps()
        return len(steps) > 0 and all(step.getContainer() is not None for step in steps)

    # --- processing (raster dev-chrome tabs + plugin steps) ---

    def __renderProcessing(self, container):
        phase = self._workflow().getPhase(SpectralWorkflowPhaseType.PROCESSING)
        # The raster inspection tabs stay host dev-chrome for now (plugin-declared rasters = Change G / M3).
        container.addTab(self.__rasterTab(REFERENCE), "Reference raster")
        container.addTab(self.__rasterTab(SAMPLE), "Sample raster")
        renderer = WorkflowPhaseRenderer()
        for step in phase.getSteps().values():
            content = renderer.renderStep(step)
            if content is not None:
                container.addTab(content, step.getLabel())

    # --- evaluation (plugin steps + the M2 Report tab) ---

    def __renderEvaluation(self, container):
        phase = self._workflow().getPhase(SpectralWorkflowPhaseType.EVALUATION)
        steps = list(phase.getSteps().values())
        if not steps:
            placeholder = QWidget()
            placeholderLayout = QVBoxLayout()
            placeholder.setLayout(placeholderLayout)
            placeholderLayout.addWidget(QLabel("No evaluation produced (insufficient signal)."))
            container.addTab(placeholder, "Metrics")
            return
        renderer = WorkflowPhaseRenderer()
        for step in steps:
            view = step.getView() if hasattr(step, "getView") else None
            if isinstance(view, ReportView):
                self.__fillReportCaptures()  # inject the real captured frames before the report renders/embeds
                content = self.__buildReportTab(view)
            else:
                content = renderer.renderStep(step)
            if content is not None:
                container.addTab(content, step.getLabel())

    # --- publishing (re-run with data so the verdict badge is populated) ---

    def __renderPublishing(self, container):
        phase = self._workflow().getPhase(SpectralWorkflowPhaseType.PUBLISHING)
        phase.getSteps().clear()
        self._engine.runPhaseHook(SpectralWorkflowPhaseType.PUBLISHING)  # fresh: badge depends on the evaluation
        for step in phase.getSteps().values():
            view = step.getView() if hasattr(step, "getView") else None
            if isinstance(view, LimsPublishView):
                result = step.getEvaluationResult() if hasattr(step, "getEvaluationResult") else None
                badgeItems = result.getItems() if result is not None else []
                tab = _PublishTab(view, badgeItems)
                tab.publishButton.clicked.connect(
                    lambda checked=False, t=tab, v=view: self.__onPublish(t, v))
                container.addTab(tab, step.getLabel())

    # --- calibration / camera ---

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
        signal = ApplicationStatusSignal()
        signal.isStatusReset = False
        signal.stepsCount = 1
        signal.currentStepIndex = 0
        signal.text = text
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(signal)

    # --- acquisition guidance ---

    def __refreshGuidance(self):
        panel = self.__capturePanel
        inAcquisition = (self._plan and self._plan[self._cursor].phaseType == SpectralWorkflowPhaseType.ACQUISITION)
        if inAcquisition:
            if panel is None or not panel.isCameraReady():
                if panel is not None:
                    self.__setButtonDot(panel.getCaptureButton(), False)
                return
            action = self.__guidanceAction()
            self.__applyGuidanceHighlights(action)
            self.__emitGuidance(action["coach"])
            return
        if panel is not None:
            self.__setButtonDot(panel.getCaptureButton(), False)
        workflow = self._workflow()
        phase = workflow.getPhase(self._plan[self._cursor].phaseType) if (workflow is not None and self._plan) else None
        self.__emitGuidance(phase.getHint() if phase is not None else None)

    def __guidanceAction(self):
        workflow = self._workflow()
        phase = workflow.getPhase(SpectralWorkflowPhaseType.ACQUISITION) if workflow is not None else None
        completeHint = phase.getHint() if phase is not None else None
        return self.__guidance.deriveAction(self.__acquisitionSteps(), completeHint)

    def __applyGuidanceHighlights(self, action):
        if self.__capturePanel is not None:
            self.__guidance.applyPanelHighlights(self.__capturePanel, action)

    def __setButtonDot(self, button, on):
        self.__guidance.setButtonDot(button, on)

    def __amberDotIcon(self):
        return self.__guidance.amberDotIcon()

    def __amberArrowIcon(self):
        return self.__guidance.amberArrowIcon()

    def __emitGuidance(self, text):
        self.__guidance.emit(text)

    def __clearStatus(self):
        self.__guidance.emit(None)

    def __meanSpectrum(self, spectrum):
        parameters = MeanSpectrumLogicModuleParameters()
        parameters.setSpectrum(spectrum)
        return MeanSpectrumLogicModule().meanSpectrum(parameters).getSpectrum()

    # --- report (M2 — SPEC_bench_pdf_export.md §1/§6) ---

    def __fillReportCaptures(self):
        acquisition = self._workflow().getPhase(SpectralWorkflowPhaseType.ACQUISITION)
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
                    item.reportImage = self.__qImageToPil(item.image)
                elif isinstance(item, SpectrumPlotView) and spectrum is not None:
                    item.spectrum = self.__meanSpectrum(spectrum)

    @staticmethod
    def __qImageToPil(image):
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
        builder = WorkflowReportBuilder(self._workflow(), reportView).build()
        pixmaps = self.__previewPixmaps(builder)
        return _ReportTab(pixmaps,
                          onSave=lambda: self.__onSaveReport(builder),
                          onOpenBigger=lambda: self.__openReportBigger(pixmaps))

    @staticmethod
    def __previewPixmaps(builder):
        from sciens.spectracs.logic.spectral.report.MatplotlibWorkflowRenderer import MatplotlibWorkflowRenderer
        pixmaps = []
        for figure in builder.figures():
            width, height, rgba = MatplotlibWorkflowRenderer.rasterize(figure)
            image = QImage(rgba, width, height, QImage.Format.Format_RGBA8888).copy()
            pixmaps.append(QPixmap.fromImage(image))
        return pixmaps

    def __openReportBigger(self, pixmaps):
        InWindowDialog.showWidget(self, "Report", PdfPreviewWidget(pixmaps))

    def __onSaveReport(self, builder):
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

    # --- publishing action (LIMS) ---

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
        from sciens.spectracs.logic.spectral.report.WorkflowReportBuilder import WorkflowReportBuilder
        evaluation = self._workflow().getPhase(SpectralWorkflowPhaseType.EVALUATION)
        reportView = None
        for step in evaluation.getSteps().values():
            view = step.getView() if hasattr(step, "getView") else None
            if isinstance(view, ReportView):
                reportView = view
                break
        if reportView is None:
            return None
        self.__fillReportCaptures()
        return WorkflowReportBuilder(self._workflow(), reportView).build().pdfBytes()

    # --- plugin selector ---

    def __entryLabel(self, entry):
        return entry.title if entry.version is None else "%s @ %s" % (entry.title, entry.version)

    def __onPluginChanged(self, index):
        if 0 <= index < len(self.__pluginEntries):
            self.__selectedEntry = self.__pluginEntries[index]
            if self._tabWidget is not None and self.isVisible():
                self.__stopStream()
                self.__enterRun()

    # --- raster / ROI dev tabs ---

    def __rasterTab(self, role):
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

    def __restoreRoi(self):
        if self.__capturePanel is not None:
            self.__capturePanel.restoreRoi()

    def __maskOutsideRoi(self, image, roi):
        masked = image.copy()
        painter = QPainter(masked)
        black = QColor(0, 0, 0)
        width, height = masked.width(), masked.height()
        painter.fillRect(0, 0, width, roi.top(), black)
        painter.fillRect(0, roi.bottom(), width, height - roi.bottom(), black)
        painter.fillRect(0, roi.top(), roi.left(), roi.height(), black)
        painter.fillRect(roi.right(), roi.top(), width - roi.right(), roi.height(), black)
        painter.end()
        return masked

    def __cropToRoi(self, image, roi):
        return image.copy(roi)

    def __imageLabel(self, image):
        label = ScaledImageLabel()
        label.setImagePixmap(QPixmap.fromImage(image))
        return label

    # --- streaming ---

    def __startStream(self):
        if self.__capturePanel is not None:
            self.__capturePanel.startStream()

    def __stopStream(self):
        if self.__capturePanel is not None:
            self.__capturePanel.stopStream()

    # --- navigation ---

    def __goToSettings(self):
        if self.__capturePanel is not None:
            self.__setButtonDot(self.__capturePanel.getCaptureButton(), False)
        self.__clearStatus()
        self.__stopStream()
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        signal = NavigationSignal(None)
        signal.setTarget("SettingsViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(signal)


class _ReportTab(QWidget):
    # The EVALUATION Report step's tab body (SPEC_bench_pdf_export.md §1): a Save row + the fit-to-width PDF
    # preview, with an "Open bigger" full-window view.

    def __init__(self, pixmaps, onSave, onOpenBigger):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
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
    # L6 (SPEC_lims_integration.md §3): the PUBLISHING "Send to LIMS" step body — verdict badge, summary, a
    # Publish button, and a status line the host updates with the returned sample id (or the error).

    def __init__(self, view, badgeItems=None):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(Metrics.M, Metrics.M, Metrics.M, Metrics.M)
        layout.setSpacing(Metrics.S)
        self.setLayout(layout)
        if badgeItems:
            from sciens.spectracs.view.spectral.workflow.render.QtWorkflowRenderer import QtWorkflowRenderer
            badgeWidget = QtWorkflowRenderer().render(badgeItems)
            if badgeWidget.layout() is not None:
                badgeWidget.layout().setContentsMargins(0, 0, 0, 0)
            layout.addWidget(badgeWidget)
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
