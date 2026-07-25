from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton, QLabel, QWidget, QVBoxLayout

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.application.style.Metrics import Metrics
from sciens.spectracs.view.spectral.workflow.AbstractPluginExecutionView import AbstractPluginExecutionView
from sciens.spectracs.view.spectral.workflow.AcquisitionGuidance import AcquisitionGuidance
from sciens.spectracs.view.spectral.workflow.CapturePanel import CapturePanel
from sciens.spectracs.logic.persistence.database.spectral.PersistSpectralWorkflowLogicModule import PersistSpectralWorkflowLogicModule
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.logic.spectral.workflow.SpectralWorkflowEngine import SpectralWorkflowEngine
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.view.application.widgets.InWindowDialog import InWindowDialog
from sciens.spectracs.view.spectral.workflow.SpectrumPlotWidget import SpectrumPlotWidget
from sciens.spectracs.view.spectral.workflow.render.WorkflowPhaseRenderer import WorkflowPhaseRenderer

_PHASE_TITLES = {
    SpectralWorkflowPhaseType.ACQUISITION: "ACQUISITION",
    SpectralWorkflowPhaseType.PROCESSING: "PROCESSING",
    SpectralWorkflowPhaseType.EVALUATION: "EVALUATION",
    SpectralWorkflowPhaseType.METADATA: "METADATA",
}


class WizardViewModule(AbstractPluginExecutionView):
    # The end-user measurement view (M2 B2): a thin subclass of AbstractPluginExecutionView. The base owns
    # navigation, the metadata form and persistence; this class provides the end-user specifics — the assigned
    # plugin, the acquisition capture UI (real live camera or virtual per-step Measure), the acquisition-guidance
    # cues, and Cancel/Delete + the VIEW mode of a saved run. (SPEC_workflow_persistence.md §6 behaviour is
    # preserved; the previously bespoke navigation is now the shared model.)

    __mode = "new"
    __viewWorkflowId = None
    __guidanceHelper = None
    __capturePanel = None

    def _getPageTitle(self):
        return "Measurement"

    def setViewWorkflow(self, workflowId):
        self.__mode = "view"
        self.__viewWorkflowId = workflowId

    def resetToNewMode(self):
        self.__mode = "new"
        self.__viewWorkflowId = None

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()
        # SPEC_acquisition_guidance §3: the amber target depends on the active tab; re-derive on tab change
        # (guarded by the base's _rendering flag so the churn during a re-render is ignored).
        self._tabWidget.currentChanged.connect(self.__onTabChanged)
        self.__acqSteps = []
        self.__measureButtons = {}
        self.__stepTabIndexByRole = {}
        return result

    def createNavigationGroupBox(self):
        result = super().createNavigationGroupBox()   # Back (col 0) + Next (col 3)
        layout = result.layout()
        self.__cancelButton = QPushButton("Cancel")
        self.__cancelButton.setProperty("buttonType", "secondary")
        self.__cancelButton.clicked.connect(self.onClickedCancel)
        layout.addWidget(self.__cancelButton, 0, 1, 1, 1)
        self.__deleteButton = QPushButton("🗑 Delete")
        self.__deleteButton.setProperty("buttonType", "secondary")
        self.__deleteButton.clicked.connect(self.onClickedDelete)
        self.__deleteButton.setVisible(False)  # VIEW mode only
        layout.addWidget(self.__deleteButton, 0, 2, 1, 1)
        return result

    def showEvent(self, event):
        super().showEvent(event)
        # Start a fresh run only on real navigation TO this view (non-spontaneous), so a desktop-switch restore
        # does not reset the in-progress workflow.
        if not event.spontaneous():
            self.__startRun()

    def hideEvent(self, event):
        super().hideEvent(event)
        if not event.spontaneous() and self.__capturePanel is not None:
            self.__capturePanel.stopStream()
            self.__capturePanel.restoreRoi()

    def __startRun(self):
        if self.__mode == "view":
            loaded = PersistSpectralWorkflowLogicModule().findById(self.__viewWorkflowId)
            if loaded is None:
                self._messageLabel.setText("Measurement not found.")
                self._stepBar.setSteps([])
                self._tabWidget.clear()
                return
            self._startViewRun(loaded)
            self.__deleteButton.setVisible(True)
        else:
            self._startNewRun()
            self.__deleteButton.setVisible(False)

    # --- base seams ---

    def _resolvePlugin(self):
        session = CurrentUserSession()
        codeRef = session.getPluginCodeRef()
        if not codeRef:
            return None
        return SpectralWorkflowEngine.importPlugin(codeRef, session.getPluginVersion())

    def _leave(self):
        self.__goHome()

    def _canAdvanceFrom(self, navStop):
        if navStop.phaseType == SpectralWorkflowPhaseType.ACQUISITION and not self._isView():
            return self.__acquisitionComplete()
        return True

    def _beforeRender(self):
        # Reset guidance refs + free the camera BEFORE the base clears the tab area.
        self.__acqSteps = []
        self.__measureButtons = {}
        self.__stepTabIndexByRole = {}
        if self.__capturePanel is not None:
            self.__capturePanel.stopStream()
            self.__capturePanel.restoreRoi()
            self.__capturePanel = None

    def _afterNav(self):
        self.__refreshGuidance()

    def _decorateNav(self, terminal):
        # The proceed action carries a permanent muted-amber ▶; terminal actions (Save / Save changes) drop it.
        self._nextButton.setIcon(QIcon() if terminal else self.__amberArrowIcon())

    def _renderStop(self, navStop, container):
        phaseType = navStop.phaseType
        if (phaseType == SpectralWorkflowPhaseType.ACQUISITION and not self._isView()
                and self.__useRealCapture()):
            self.__renderRealAcquisition(container)
            return
        phase = self._workflow().getPhase(phaseType)
        renderer = WorkflowPhaseRenderer(captureHandler=self.__buildCapturePanel)
        for step in phase.getSteps().values():
            isAcquisitionStep = (phaseType == SpectralWorkflowPhaseType.ACQUISITION and step.getRole() is not None)
            if isAcquisitionStep and not self._isView():
                widget = renderer.renderStep(step)   # NEW mode virtual: live capture seam
            else:
                widget = self.__computedPanel(step)  # computed step, or VIEW-mode acquisition plot
            if widget is not None:
                index = container.addTab(widget, step.getLabel() or _PHASE_TITLES.get(phaseType, ""))
                if isAcquisitionStep and not self._isView():
                    self.__acqSteps.append(step)
                    self.__stepTabIndexByRole[step.getRole()] = index

    # --- acquisition (real live camera) ---

    def __useRealCapture(self):
        profile = ApplicationContextLogicModule().getApplicationSettings().getSpectrometerProfile()
        try:
            sensor = profile.spectrometer.spectrometerSensor
        except AttributeError:
            return False
        return sensor is not None and not sensor.isVirtual

    def __renderRealAcquisition(self, container):
        phase = self._workflow().getPhase(SpectralWorkflowPhaseType.ACQUISITION)
        steps = [step for step in phase.getSteps().values() if step.getRole() is not None]
        self.__acqSteps = steps
        self.__capturePanel = CapturePanel(
            steps, self._engine,
            onCaptured=self.__onRealCaptured, onRoleChanged=self.__refreshGuidance,
            onCaptureFailed=self.__onRealCaptureFailed)
        container.addTab(self.__capturePanel,
                         _PHASE_TITLES.get(SpectralWorkflowPhaseType.ACQUISITION, "Acquisition"))
        self.__capturePanel.startStream()
        self.__capturePanel.plotActiveRole()

    def __onRealCaptured(self, step):
        self._onCapture()   # Option C (§4.4a): invalidate computed phases + refresh nav

    def __onRealCaptureFailed(self):
        self._messageLabel.setText("Capture failed — no frames were delivered by the camera.")

    def __acquisitionComplete(self):
        phase = self._engine.getWorkflow().getPhase(SpectralWorkflowPhaseType.ACQUISITION)
        for step in phase.getSteps().values():
            if step.getRole() is not None and step.getContainer() is None:
                return False
        return True

    # --- acquisition (virtual per-step Measure) + computed panels ---

    def __buildCapturePanel(self, step, captureView):
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(Metrics.M, Metrics.M, Metrics.M, Metrics.M)
        panel.setLayout(layout)
        plot = SpectrumPlotWidget()
        captured = step.getContainer()
        if not self._isView():
            measureButton = QPushButton("Measure")
            measureButton.setObjectName("WizardViewModule.measureButton.%s" % step.getRole().lower())
            self.__measureButtons[step.getRole()] = measureButton
            statusLabel = QLabel("Not measured")
            layout.addWidget(measureButton)
            layout.addWidget(statusLabel)
            layout.addWidget(plot)

            def onMeasure():
                self._engine.captureAcquisitionStep(step)
                spectrum = step.getContainer().getSpectra()[step.getRole()]
                plot.plotSpectrum(spectrum, title=step.getLabel())
                statusLabel.setText("Measured (%s frames)" % step.getFrames())
                self._onCapture()   # Option C (§4.4a): invalidate computed phases + refresh nav

            measureButton.clicked.connect(onMeasure)
            if captured is not None:
                plot.plotSpectrum(captured.getSpectra()[step.getRole()], title=step.getLabel())
                statusLabel.setText("Measured (%s frames)" % step.getFrames())
        else:
            layout.addWidget(plot)
            if captured is not None and step.getRole() in captured.getSpectra():
                plot.plotSpectrum(captured.getSpectra()[step.getRole()], title=step.getLabel())
        return panel

    def __computedPanel(self, step):
        content = WorkflowPhaseRenderer().renderStep(step)
        if content is not None:
            return content
        container = step.getContainer()  # VIEW mode: `_view` is transient/None -> plot from the container
        if container is not None and len(container.getSpectra()) > 0:
            spectrum = next(iter(container.getSpectra().values()))
            plot = SpectrumPlotWidget()
            plot.plotSpectrum(spectrum, title=step.getLabel())
            return plot
        return None

    # --- acquisition guidance (SPEC_acquisition_guidance.md) ---

    def __onTabChanged(self, _index):
        if not self._rendering:
            self.__refreshGuidance()

    def __refreshGuidance(self):
        if self._isView() or not self._plan:
            self.__emitStatusReset()
            return
        phaseType = self._plan[self._cursor].phaseType
        if phaseType == SpectralWorkflowPhaseType.ACQUISITION and self.__acqSteps:
            action = self.__deriveNextAction()
            self.__applyGuidanceHighlights(action)
            self.__emitGuidance(action["coach"])
            return
        self.__emitGuidance(self.__currentPhaseHint(phaseType))

    def __currentPhaseHint(self, phaseType):
        workflow = self._workflow()
        phase = workflow.getPhase(phaseType) if workflow is not None else None
        return phase.getHint() if phase is not None else None

    def __deriveNextAction(self):
        phase = self._workflow().getPhase(SpectralWorkflowPhaseType.ACQUISITION)
        completeHint = phase.getHint() if phase is not None else None
        return self.__guidance().deriveAction(self.__acqSteps, completeHint)

    def __applyGuidanceHighlights(self, action):
        if self.__capturePanel is not None:
            self.__guidance().applyPanelHighlights(self.__capturePanel, action)
            return
        bar = self._tabWidget.tabBar()
        currentIndex = self._tabWidget.currentIndex()
        for step in action["steps"]:
            index = self.__stepTabIndexByRole.get(step.getRole())
            if index is None:
                continue
            button = self.__measureButtons.get(step.getRole())
            self.__setButtonDot(button, False)
            baseLabel = step.getLabel() or ""
            self._tabWidget.setTabText(index, ("✓ " + baseLabel) if step.getContainer() is not None else baseLabel)
            bar.setTabIcon(index, QIcon())
        nextStep = action["nextStep"]
        if nextStep is None:
            return
        index = self.__stepTabIndexByRole.get(nextStep.getRole())
        if index is None:
            return
        if index == currentIndex:
            self.__setButtonDot(self.__measureButtons.get(nextStep.getRole()), True)
        else:
            bar.setTabIcon(index, self.__amberDotIcon())

    def __setButtonDot(self, button, on):
        self.__guidance().setButtonDot(button, on)

    def __amberDotIcon(self):
        return self.__guidance().amberDotIcon()

    def __amberArrowIcon(self):
        return self.__guidance().amberArrowIcon()

    def __guidance(self):
        if self.__guidanceHelper is None:
            self.__guidanceHelper = AcquisitionGuidance()
        return self.__guidanceHelper

    def __emitGuidance(self, text):
        self.__guidance().emit(text)

    def __emitStatusReset(self):
        self.__guidance().emit(None)

    # --- actions ---

    def onClickedCancel(self):
        message = ("Discard unsaved changes to this measurement?" if self._isView()
                   else "Discard this measurement? It will not be saved.")
        if not InWindowDialog.confirm(self, "Cancel", message):
            return
        self.resetToNewMode()
        self.__goHome()

    def onClickedDelete(self):
        if not InWindowDialog.confirm(self, "Delete measurement",
                                      "This measurement will be permanently deleted. Continue?",
                                      destructive=True):
            return
        PersistSpectralWorkflowLogicModule().delete(self.__viewWorkflowId, userId=CurrentUserSession().userId)
        self.resetToNewMode()
        self.__goHome()

    def __goHome(self):
        self.__emitStatusReset()  # SPEC_acquisition_guidance §4.1: don't leave a stale coach line on Home
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        signal = NavigationSignal(None)
        signal.setTarget("Home")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(signal)
