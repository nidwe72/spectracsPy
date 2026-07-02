from PySide6.QtWidgets import QPushButton, QTabWidget, QLabel, QWidget, QVBoxLayout

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.appliction.style.Metrics import Metrics
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.logic.spectral.workflow.SpectralWorkflowEngine import SpectralWorkflowEngine
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.model.spectral.evaluation.SpectrumPlotView import SpectrumPlotView
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget
from sciens.spectracs.view.spectral.workflow.EvaluationResultRenderer import EvaluationResultRenderer
from sciens.spectracs.view.spectral.workflow.SpectrumPlotWidget import SpectrumPlotWidget

_PHASE_TITLES = {
    SpectralWorkflowPhaseType.ACQUISITION: "ACQUISITION",
    SpectralWorkflowPhaseType.PROCESSING: "PROCESSING",
    SpectralWorkflowPhaseType.EVALUATION: "EVALUATION",
    SpectralWorkflowPhaseType.METADATA: "METADATA",
    SpectralWorkflowPhaseType.PUBLISHING: "PUBLISHING",
}


class WizardViewModule(PageWidget):
    # Interactive nested-wizard run page (SPEC_pumpkin_integration.md C.3/C.5). ACQUISITION declares
    # measurement steps the user captures with a Measure button (matches real-device usage); PROCESSING /
    # EVALUATION compute on Next. Real spectra are plotted (capture preview + absorption curve). Read-only
    # phase rail; Back / Cancel / Next→Save (EVALUATION terminal). NOTE: compile + offscreen verified; a
    # live click-through is still worthwhile.

    __railLabel: QLabel = None
    __tabWidget: QTabWidget = None
    __backButton: QPushButton = None
    __cancelButton: QPushButton = None
    __nextButton: QPushButton = None

    def _getPageTitle(self):
        return "Measurement"

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()
        self.__railLabel = QLabel("")
        result['rail'] = self.__railLabel
        self.__tabWidget = QTabWidget()
        result['tabs'] = self.__tabWidget
        return result

    def createNavigationGroupBox(self):
        result = super().createNavigationGroupBox()
        layout = result.layout()
        self.__backButton = QPushButton("◀ Back")
        self.__backButton.clicked.connect(self.onClickedBack)
        layout.addWidget(self.__backButton, 0, 0, 1, 1)
        self.__cancelButton = QPushButton("Cancel")
        self.__cancelButton.clicked.connect(self.onClickedCancel)
        layout.addWidget(self.__cancelButton, 0, 1, 1, 1)
        self.__nextButton = QPushButton("Next ▶")
        self.__nextButton.clicked.connect(self.onClickedNext)
        layout.addWidget(self.__nextButton, 0, 2, 1, 1)
        return result

    def showEvent(self, event):
        super().showEvent(event)
        self.__startRun()

    # --- run + navigation ---

    def __startRun(self):
        self.__engine = None
        self.__hooksRun = set()
        self.__shownPhases = []
        self.__cursor = 0
        codeRef = CurrentUserSession().getPluginCodeRef()
        if not codeRef:
            self.__railLabel.setText("No plugin configured for this user.")
            self.__tabWidget.clear()
            return
        self.__engine = SpectralWorkflowEngine(SpectralWorkflowEngine.importPlugin(codeRef))
        firstPhase = self.__runHookOnce(SpectralWorkflowPhaseType.ACQUISITION)
        if len(firstPhase.getSteps()) > 0:
            self.__shownPhases = [SpectralWorkflowPhaseType.ACQUISITION]
            self.__cursor = 0
            self.__renderCurrentPhase()

    def __runHookOnce(self, phaseType):
        if phaseType not in self.__hooksRun:
            self.__engine.runPhaseHook(phaseType)
            self.__hooksRun.add(phaseType)
        return self.__engine.getWorkflow().getPhase(phaseType)

    def __nextVisibleAfter(self, phaseType):
        order = SpectralWorkflowEngine.PHASE_ORDER
        for nextType in order[order.index(phaseType) + 1:]:
            phase = self.__runHookOnce(nextType)  # safe: earlier phases are complete before we peek
            if len(phase.getSteps()) > 0:
                return nextType
        return None

    def __isTerminal(self, phaseType):
        # ACQUISITION never terminal (and we must not peek PROCESSING before capture); otherwise a phase is
        # terminal when no later phase produces steps.
        if phaseType == SpectralWorkflowPhaseType.ACQUISITION:
            return False
        return self.__nextVisibleAfter(phaseType) is None

    def __acquisitionComplete(self):
        phase = self.__engine.getWorkflow().getPhase(SpectralWorkflowPhaseType.ACQUISITION)
        for step in phase.getSteps().values():
            if step.getRole() is not None and step.getContainer() is None:
                return False
        return True

    def __renderCurrentPhase(self):
        self.__tabWidget.clear()
        if not self.__shownPhases:
            return
        phaseType = self.__shownPhases[self.__cursor]
        phase = self.__engine.getWorkflow().getPhase(phaseType)
        for step in phase.getSteps().values():
            if phaseType == SpectralWorkflowPhaseType.ACQUISITION and step.getRole() is not None:
                widget = self.__acquisitionPanel(step)
            else:
                widget = self.__computedPanel(step)
            if widget is not None:
                self.__tabWidget.addTab(widget, step.getLabel() or _PHASE_TITLES.get(phaseType, ""))
        self.__railLabel.setText(self.__railText())
        self.__refreshNav()

    def __railText(self):
        marks = []
        for index, phaseType in enumerate(self.__shownPhases):
            marker = "●" if index < self.__cursor else ("◉" if index == self.__cursor else "○")
            marks.append("%s %s" % (marker, _PHASE_TITLES.get(phaseType, "")))
        return "     ".join(marks)

    def __refreshNav(self):
        phaseType = self.__shownPhases[self.__cursor]
        terminal = self.__isTerminal(phaseType)
        self.__backButton.setEnabled(self.__cursor > 0)
        self.__nextButton.setText("Save" if terminal else "Next ▶")
        if phaseType == SpectralWorkflowPhaseType.ACQUISITION:
            self.__nextButton.setEnabled(self.__acquisitionComplete())
        else:
            self.__nextButton.setEnabled(True)

    def __acquisitionPanel(self, step):
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(Metrics.M, Metrics.M, Metrics.M, Metrics.M)
        panel.setLayout(layout)

        measureButton = QPushButton("Measure")
        statusLabel = QLabel("Not measured")
        plot = SpectrumPlotWidget()
        layout.addWidget(measureButton)
        layout.addWidget(statusLabel)
        layout.addWidget(plot)

        def onMeasure():
            self.__engine.captureAcquisitionStep(step)
            container = step.getContainer()
            spectrum = container.getSpectra()[step.getRole()] if container is not None else None
            plot.plotSpectrum(spectrum, title=step.getLabel())
            statusLabel.setText("Measured (%s frames)" % step.getFrames())
            self.__refreshNav()

        measureButton.clicked.connect(onMeasure)
        if step.getContainer() is not None:  # revisited via Back — show what was captured
            plot.plotSpectrum(step.getContainer().getSpectra()[step.getRole()], title=step.getLabel())
            statusLabel.setText("Measured (%s frames)" % step.getFrames())
        return panel

    def __computedPanel(self, step):
        if step.getEvaluationResult() is not None:
            return EvaluationResultRenderer().render(step.getEvaluationResult())
        view = step.getView()
        if isinstance(view, SpectrumPlotView):
            plot = SpectrumPlotWidget()
            plot.plotSpectrum(view.spectrum, title=view.title)
            return plot
        return None  # headless carrier step (e.g. transmission) — no tab

    def onClickedBack(self):
        if self.__cursor > 0:
            self.__cursor -= 1
            self.__renderCurrentPhase()

    def onClickedNext(self):
        if self.__cursor < len(self.__shownPhases) - 1:  # already-shown phase ahead (after a Back)
            self.__cursor += 1
            self.__renderCurrentPhase()
            return
        phaseType = self.__shownPhases[self.__cursor]
        if self.__isTerminal(phaseType):
            self.__goHome()  # Save — no-op persistence for now (D2/D-UI-2)
            return
        nextType = self.__nextVisibleAfter(phaseType)
        if nextType is None:
            self.__goHome()
            return
        self.__shownPhases.append(nextType)
        self.__cursor = len(self.__shownPhases) - 1
        self.__renderCurrentPhase()

    def onClickedCancel(self):
        self.__goHome()

    def __goHome(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        signal = NavigationSignal(None)
        signal.setTarget("Home")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(signal)
