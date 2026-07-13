import datetime

from PySide6.QtCore import QDate, QPoint, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap, QPolygon
from PySide6.QtWidgets import (QPushButton, QTabWidget, QLabel, QWidget, QVBoxLayout, QLineEdit,
                               QDateEdit)

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from sciens.spectracs.logic.appliction.style.Metrics import Metrics
from sciens.spectracs.model.application.applicationStatus.ApplicationStatusSignal import ApplicationStatusSignal
from sciens.spectracs.view.spectral.workflow.AcquisitionGuidance import AcquisitionGuidance
from sciens.spectracs.logic.persistence.database.spectral.PersistSpectralWorkflowLogicModule import PersistSpectralWorkflowLogicModule
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.logic.spectral.workflow.SpectralWorkflowEngine import SpectralWorkflowEngine
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.model.spectral.SpectralWorkflowMetadata import SpectralWorkflowMetadata
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.model.spectral.plugin.view.SpectrumPlotView import SpectrumPlotView
from sciens.spectracs.view.application.widgets.InWindowDialog import InWindowDialog
from sciens.spectracs.view.application.widgets.StepBarWidget import StepBarWidget
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget
from sciens.spectracs.view.spectral.workflow.EvaluationResultRenderer import EvaluationResultRenderer
from sciens.spectracs.view.spectral.workflow.SpectrumPlotWidget import SpectrumPlotWidget
from sciens.spectracs.view.spectral.workflow.render.WorkflowPhaseRenderer import WorkflowPhaseRenderer

_PHASE_TITLES = {
    SpectralWorkflowPhaseType.ACQUISITION: "ACQUISITION",
    SpectralWorkflowPhaseType.PROCESSING: "PROCESSING",
    SpectralWorkflowPhaseType.EVALUATION: "EVALUATION",
    SpectralWorkflowPhaseType.METADATA: "METADATA",
}
# Title-case labels for the chevron step bar.
_PHASE_LABELS = {
    SpectralWorkflowPhaseType.ACQUISITION: "Acquisition",
    SpectralWorkflowPhaseType.PROCESSING: "Processing",
    SpectralWorkflowPhaseType.EVALUATION: "Evaluation",
    SpectralWorkflowPhaseType.METADATA: "Metadata",
}
_METADATA_TAB = "Metadata"


class WizardViewModule(PageWidget):
    # Two modes (SPEC_workflow_persistence.md §6): NEW runs the engine phase-by-phase (Measure/Next/Save);
    # VIEW loads a saved SpectralWorkflow read-only, everything read-only EXCEPT the METADATA tab, with
    # Back / Delete / Save-changes. Save (NEW) persists the graph; Save-changes updates metadata only.
    # NOTE: offscreen-verified; a live click-through is still worthwhile.

    __messageLabel: QLabel = None
    __stepBar: StepBarWidget = None
    __tabWidget: QTabWidget = None
    __backButton: QPushButton = None
    __cancelButton: QPushButton = None
    __deleteButton: QPushButton = None
    __nextButton: QPushButton = None
    __mode = "new"
    __viewWorkflowId = None
    # SPEC_acquisition_guidance.md — per-render guidance state (NEW+ACQUISITION only). Rebuilt each render.
    __rendering = False
    __guidanceHelper = None   # shared AcquisitionGuidance primitives (S1a), lazily created

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
        self.__messageLabel = QLabel("")
        result['message'] = self.__messageLabel
        self.__stepBar = StepBarWidget()
        result['stepBar'] = self.__stepBar
        self.__tabWidget = QTabWidget()
        self.__tabWidget.setObjectName("WizardViewModule.tabWidget")  # SPEC_doc_automation §7.2
        # SPEC_acquisition_guidance §3: the amber target depends on the ACTIVE tab, so re-derive on tab change
        # (not only after a capture). Guarded by __rendering so the churn during a re-render is ignored.
        self.__tabWidget.currentChanged.connect(self.__onTabChanged)
        self.__acqSteps = []            # ordered role-bearing ACQUISITION steps for the current render
        self.__measureButtons = {}      # role -> its Measure QPushButton
        self.__stepTabIndexByRole = {}  # role -> its tab index
        result['tabs'] = self.__tabWidget
        return result

    def createNavigationGroupBox(self):
        result = super().createNavigationGroupBox()
        layout = result.layout()
        self.__backButton = QPushButton("← Back")
        self.__backButton.setObjectName("WizardViewModule.backButton")  # SPEC_doc_automation §7.2
        self.__backButton.clicked.connect(self.onClickedBack)
        layout.addWidget(self.__backButton, 0, 0, 1, 1)
        self.__cancelButton = QPushButton("Cancel")
        self.__cancelButton.setProperty("buttonType", "secondary")  # Bootstrap 'secondary' (gray)
        self.__cancelButton.clicked.connect(self.onClickedCancel)
        layout.addWidget(self.__cancelButton, 0, 1, 1, 1)
        self.__deleteButton = QPushButton("🗑 Delete")
        self.__deleteButton.setProperty("buttonType", "secondary")
        self.__deleteButton.clicked.connect(self.onClickedDelete)
        self.__deleteButton.setVisible(False)  # VIEW mode only
        layout.addWidget(self.__deleteButton, 0, 2, 1, 1)
        self.__nextButton = QPushButton("Next →")
        self.__nextButton.setObjectName("WizardViewModule.nextButton")  # SPEC_doc_automation §7.2
        self.__nextButton.clicked.connect(self.onClickedNext)
        layout.addWidget(self.__nextButton, 0, 3, 1, 1)
        return result

    def showEvent(self, event):
        super().showEvent(event)
        # Start a fresh run only on real navigation TO this view (non-spontaneous). A spontaneous show comes
        # from the window system — a virtual-desktop switch back, a minimise/restore — and must NOT reset the
        # wizard to ACQUISITION or discard the in-progress workflow (Edwin's desktop-switch bug).
        if not event.spontaneous():
            self.__startRun()

    # --- setup ---

    def __startRun(self):
        self.__shownPhases = []
        self.__cursor = 0
        self.__hooksRun = set()
        self.__engine = None
        self.__plugin = None
        self.__loadedWorkflow = None
        self.__metadataWidgets = {}
        if self.__mode == "view":
            self.__startView()
        else:
            self.__startNew()

    def __startNew(self):
        self.__messageLabel.setText("")
        codeRef = CurrentUserSession().getPluginCodeRef()
        if not codeRef:
            self.__messageLabel.setText("No plugin configured for this user.")
            self.__stepBar.setSteps([])
            self.__tabWidget.clear()
            return
        self.__plugin = SpectralWorkflowEngine.importPlugin(codeRef)
        self.__engine = SpectralWorkflowEngine(self.__plugin)
        firstPhase = self.__runHookOnce(SpectralWorkflowPhaseType.ACQUISITION)
        if len(firstPhase.getSteps()) > 0:
            self.__shownPhases = [SpectralWorkflowPhaseType.ACQUISITION]
            self.__setupStepBar()
            self.__renderCurrentPhase()

    def __startView(self):
        self.__messageLabel.setText("")
        self.__loadedWorkflow = PersistSpectralWorkflowLogicModule().findById(self.__viewWorkflowId)
        if self.__loadedWorkflow is None:
            self.__messageLabel.setText("Measurement not found.")
            self.__stepBar.setSteps([])
            self.__tabWidget.clear()
            return
        self.__shownPhases = [pt for pt in SpectralWorkflowEngine.PHASE_ORDER
                              if self.__phaseHasSteps(self.__loadedWorkflow, pt)]
        if len(self.__loadedWorkflow.getMetadataFields()) > 0:
            self.__shownPhases.append(SpectralWorkflowPhaseType.METADATA)
        self.__setupStepBar()
        self.__renderCurrentPhase()

    def __setupStepBar(self):
        # The FULL phase sequence, shown all at once (the current one is highlighted per render).
        self.__fullSequence = self.__fullPhaseSequence()
        self.__stepBar.setSteps([_PHASE_LABELS.get(pt, str(pt)) for pt in self.__fullSequence])

    def __fullPhaseSequence(self):
        if self.__isView():
            return list(self.__shownPhases)  # already the full persisted set (+ METADATA)
        sequence = [SpectralWorkflowPhaseType.ACQUISITION, SpectralWorkflowPhaseType.PROCESSING,
                    SpectralWorkflowPhaseType.EVALUATION]
        if self.__hasMetadataFields():
            sequence.append(SpectralWorkflowPhaseType.METADATA)
        return sequence

    def __phaseHasSteps(self, workflow, phaseType):
        phase = workflow.getPhase(phaseType)
        return phase is not None and len(phase.getSteps()) > 0

    def __isView(self):
        return self.__mode == "view"

    def __workflow(self):
        return self.__loadedWorkflow if self.__isView() else self.__engine.getWorkflow()

    # --- new-mode phase discovery ---

    def __runHookOnce(self, phaseType):
        if phaseType not in self.__hooksRun:
            self.__engine.runPhaseHook(phaseType)
            self.__hooksRun.add(phaseType)
        return self.__engine.getWorkflow().getPhase(phaseType)

    def __nextVisibleAfter(self, phaseType):
        # METADATA is a synthetic terminal phase (form built from plugin specs); it has no engine steps.
        if phaseType == SpectralWorkflowPhaseType.METADATA:
            return None
        order = SpectralWorkflowEngine.PHASE_ORDER
        for nextType in order[order.index(phaseType) + 1:]:
            if nextType == SpectralWorkflowPhaseType.METADATA:
                if self.__hasMetadataFields():
                    return SpectralWorkflowPhaseType.METADATA
                continue
            if len(self.__runHookOnce(nextType).getSteps()) > 0:
                return nextType
        return None

    def __hasMetadataFields(self):
        if self.__isView():
            return len(self.__loadedWorkflow.getMetadataFields()) > 0
        return len(self.__plugin.metadata(self.__engine.getWorkflow())) > 0

    def __isTerminalCursor(self):
        if self.__isView():
            return self.__cursor >= len(self.__shownPhases) - 1
        phaseType = self.__shownPhases[self.__cursor]
        if phaseType == SpectralWorkflowPhaseType.ACQUISITION:
            return False
        return self.__nextVisibleAfter(phaseType) is None

    def __acquisitionComplete(self):
        phase = self.__engine.getWorkflow().getPhase(SpectralWorkflowPhaseType.ACQUISITION)
        for step in phase.getSteps().values():
            if step.getRole() is not None and step.getContainer() is None:
                return False
        return True

    # --- rendering ---

    def __renderCurrentPhase(self):
        # Reset the guidance refs BEFORE clear() so the currentChanged churn from clear()/addTab is ignored.
        self.__rendering = True
        self.__acqSteps = []
        self.__measureButtons = {}
        self.__stepTabIndexByRole = {}
        self.__tabWidget.clear()
        if not self.__shownPhases:
            self.__rendering = False
            self.__setGuidanceProperty(self.__nextButton, False)
            self.__emitStatusReset()
            return
        phaseType = self.__shownPhases[self.__cursor]
        if phaseType == SpectralWorkflowPhaseType.METADATA:
            self.__tabWidget.addTab(self.__metadataPanel(), _METADATA_TAB)
        else:
            phase = self.__workflow().getPhase(phaseType)
            # S1c: acquisition steps flow through the SHARED capture seam — a CaptureView step routes to the
            # wizard's captureHandler (__buildCapturePanel). The wizard has no dev-chrome, so
            # decorateCapturePanel stays empty. Computed steps keep __computedPanel (its VIEW-mode container
            # fallback isn't in the generic renderer).
            renderer = WorkflowPhaseRenderer(captureHandler=self.__buildCapturePanel)
            for step in phase.getSteps().values():
                isAcquisitionStep = (phaseType == SpectralWorkflowPhaseType.ACQUISITION
                                     and step.getRole() is not None)
                if isAcquisitionStep:
                    widget = renderer.renderStep(step)
                else:
                    widget = self.__computedPanel(step)
                if widget is not None:
                    index = self.__tabWidget.addTab(widget, step.getLabel() or _PHASE_TITLES.get(phaseType, ""))
                    if isAcquisitionStep and not self.__isView():
                        self.__acqSteps.append(step)
                        self.__stepTabIndexByRole[step.getRole()] = index
        if phaseType in self.__fullSequence:
            self.__stepBar.setCurrentIndex(self.__fullSequence.index(phaseType))
        self.__rendering = False
        self.__refreshNav()

    def __refreshNav(self):
        terminal = self.__isTerminalCursor()
        self.__backButton.setEnabled(self.__cursor > 0)
        self.__deleteButton.setVisible(self.__isView())  # Delete only exists for a saved run
        if self.__isView():
            self.__setNextButtonLabel("Save changes", terminal)
            self.__nextButton.setEnabled(True)
        else:
            self.__setNextButtonLabel("Save", terminal)
            phaseType = self.__shownPhases[self.__cursor]
            if phaseType == SpectralWorkflowPhaseType.ACQUISITION:
                self.__nextButton.setEnabled(self.__acquisitionComplete())
            else:
                self.__nextButton.setEnabled(True)
        self.__refreshGuidance()

    def __setNextButtonLabel(self, terminalText, terminal):
        # The proceed action carries a permanent muted-amber ▶ (dims automatically when the button is disabled,
        # brightens when enabled). Terminal actions (Save / Close / Save changes) drop the arrow.
        if terminal:
            self.__nextButton.setText(terminalText)
            self.__nextButton.setIcon(QIcon())
        else:
            self.__nextButton.setText("Next")
            self.__nextButton.setIcon(self.__amberArrowIcon())

    # --- acquisition guidance (SPEC_acquisition_guidance.md) ---

    def __onTabChanged(self, _index):
        # The amber target moves when the user switches tabs; ignore the churn during a re-render.
        if not self.__rendering:
            self.__refreshGuidance()

    def __refreshGuidance(self):
        # NEW-mode ACQUISITION → the next-action coach + amber cues. NEW-mode later phases → the plugin's
        # phase hint (if any). VIEW mode / no run → nothing.
        if self.__isView() or not self.__shownPhases:
            self.__emitStatusReset()
            return
        phaseType = self.__shownPhases[self.__cursor]
        if phaseType == SpectralWorkflowPhaseType.ACQUISITION and self.__acqSteps:
            action = self.__deriveNextAction()
            self.__applyGuidanceHighlights(action)
            self.__emitGuidance(action["coach"])  # verbatim plugin prompt, or None -> resting when all captured
            return
        # A computed phase — no amber (nothing to act on), just the plugin's authored phase hint (or resting).
        self.__emitGuidance(self.__currentPhaseHint(phaseType))

    def __currentPhaseHint(self, phaseType):
        workflow = self.__workflow()
        phase = workflow.getPhase(phaseType) if workflow is not None else None
        return phase.getHint() if phase is not None else None

    def __deriveNextAction(self):
        # The single source of truth: the first still-uncaptured acquisition step (order-independent).
        steps = self.__acqSteps
        total = len(steps)
        capturedCount = sum(1 for step in steps if step.getContainer() is not None)
        nextStep = next((step for step in steps if step.getContainer() is None), None)
        if nextStep is not None:
            view = nextStep.getView()
            hint = getattr(view, "prompt", None) if view is not None else None
            if not hint:
                hint = "Press %s" % (getattr(view, "captureLabel", "Measure") if view is not None else "Measure")
            coach = hint  # the plugin's prompt, verbatim — no "Step N of M" wrapper (Edwin, 2026-07-13)
        else:
            phase = self.__workflow().getPhase(SpectralWorkflowPhaseType.ACQUISITION)  # all captured
            coach = phase.getHint() if phase is not None else None  # plugin's "measurement complete" (or resting)
        return {"steps": steps, "total": total, "capturedCount": capturedCount,
                "nextStep": nextStep, "coach": coach}

    def __applyGuidanceHighlights(self, action):
        # Exactly ONE amber target at a time. Reset every acquisition tab/button to baseline first, then paint it.
        bar = self.__tabWidget.tabBar()
        currentIndex = self.__tabWidget.currentIndex()
        for step in action["steps"]:
            index = self.__stepTabIndexByRole.get(step.getRole())
            if index is None:
                continue
            button = self.__measureButtons.get(step.getRole())
            self.__setButtonDot(button, False)
            baseLabel = step.getLabel() or ""
            # ✓ glyph (not colour) marks done, so it never clashes with the green selected-tab.
            self.__tabWidget.setTabText(index, ("✓ " + baseLabel) if step.getContainer() is not None else baseLabel)
            bar.setTabIcon(index, QIcon())
        # The Next arrow is a permanent part of the button (set in __refreshNav), not a per-state cue.
        nextStep = action["nextStep"]
        if nextStep is None:
            return
        index = self.__stepTabIndexByRole.get(nextStep.getRole())
        if index is None:
            return
        if index == currentIndex:
            self.__setButtonDot(self.__measureButtons.get(nextStep.getRole()), True)  # on tab -> amber ● Measure
        else:
            bar.setTabIcon(index, self.__amberDotIcon())  # wrong tab -> amber ● on the tab to switch to

    # --- the amber cue icons: delegated to the shared AcquisitionGuidance util (S1a). The derivation +
    #     highlight application above stay host-specific (S4a folds them in). ---

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
        # Plugin/guidance text → muted-amber font, no progress bar. A None/empty text rests the bar instead.
        self.__guidance().emit(text)

    def __emitStatusReset(self):
        self.__guidance().emit(None)

    def __buildCapturePanel(self, step, captureView):
        # The wizard's captureHandler (S1c) — invoked BY WorkflowPhaseRenderer's capture seam, not directly.
        # Builds the interactive Measure panel (plot + Measure + status). `captureView` carries the plugin's
        # shell (prompt/captureLabel); the wizard keeps the button as "Measure" and surfaces the prompt via
        # the guidance coach line, so it's unused here for now (the shared panel + prompt wiring is S2a).
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(Metrics.M, Metrics.M, Metrics.M, Metrics.M)
        panel.setLayout(layout)
        plot = SpectrumPlotWidget()
        captured = step.getContainer()

        if not self.__isView():
            measureButton = QPushButton("Measure")
            # SPEC_doc_automation §7.2: role-qualified so both acquisition tabs' Measure buttons (which
            # coexist in the tree) are individually resolvable by the Director's locate.
            measureButton.setObjectName("WizardViewModule.measureButton.%s" % step.getRole().lower())
            self.__measureButtons[step.getRole()] = measureButton  # SPEC_acquisition_guidance: amber cue target
            statusLabel = QLabel("Not measured")
            layout.addWidget(measureButton)
            layout.addWidget(statusLabel)
            layout.addWidget(plot)

            def onMeasure():
                self.__engine.captureAcquisitionStep(step)
                spectrum = step.getContainer().getSpectra()[step.getRole()]
                plot.plotSpectrum(spectrum, title=step.getLabel())
                statusLabel.setText("Measured (%s frames)" % step.getFrames())
                self.__refreshNav()

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
        # M1: route EvaluationResult + the declared _view (SpectrumPlotView incl. traces/bands/markers,
        # SpectrumCaptureView) through the shared render seam — same generic path the bench uses.
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

    # --- metadata form (editable in both modes) ---

    def __metadataPanel(self):
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(Metrics.M, Metrics.M, Metrics.M, Metrics.M)
        panel.setLayout(layout)
        self.__metadataWidgets = {}
        for name, label, fieldType, value in self.__metadataSpecs():
            if fieldType == "DATE":
                widget = QDateEdit()
                widget.setDisplayFormat("yyyy-MM-dd")
                widget.setCalendarPopup(True)  # modern calendar dropdown
                widget.setDate(QDate.fromString(value, "yyyy-MM-dd") if value else QDate.currentDate())
            else:
                widget = QLineEdit()
                widget.setText("" if value is None else str(value))
            self.__metadataWidgets[name] = (widget, fieldType)
            layout.addWidget(self.createLabeledComponent(label, widget))
        layout.addStretch(1)
        return panel

    def __metadataSpecs(self):
        # (name, label, type, value) — from the loaded rows (VIEW) or the plugin's MetadataFields (NEW).
        if self.__isView():
            rows = sorted(self.__loadedWorkflow.getMetadataFields(), key=lambda field: field.order or 0)
            return [(row.name, row.label, row.type, row.value) for row in rows]
        specs = sorted(self.__plugin.metadata(self.__engine.getWorkflow()), key=lambda spec: spec.order)
        return [(spec.name, spec.label, spec.type, "") for spec in specs]

    def __readMetadata(self):
        result = {}
        for name, (widget, fieldType) in self.__metadataWidgets.items():
            if fieldType == "DATE":
                result[name] = widget.date().toString("yyyy-MM-dd")
            else:
                result[name] = widget.text()
        return result

    # --- navigation / actions ---

    def onClickedBack(self):
        if self.__cursor > 0:
            self.__cursor -= 1
            self.__renderCurrentPhase()

    def onClickedNext(self):
        if self.__cursor < len(self.__shownPhases) - 1:
            self.__cursor += 1
            self.__renderCurrentPhase()
            return
        if self.__isView():
            self.__saveMetadataEdits()
            return
        if self.__isTerminalCursor():
            self.__saveNewRun()
            return
        nextType = self.__nextVisibleAfter(self.__shownPhases[self.__cursor])
        if nextType is None:
            self.__saveNewRun()
            return
        self.__shownPhases.append(nextType)
        self.__cursor = len(self.__shownPhases) - 1
        self.__renderCurrentPhase()

    def onClickedCancel(self):
        # Available in BOTH modes: leave without saving (a new run is discarded; metadata edits are dropped).
        message = ("Discard unsaved changes to this measurement?" if self.__isView()
                   else "Discard this measurement? It will not be saved.")
        if not InWindowDialog.confirm(self, "Cancel", message):
            return
        self.resetToNewMode()
        self.__goHome()

    def onClickedDelete(self):
        self.__deleteWorkflow()

    def __saveNewRun(self):
        workflow = self.__engine.getWorkflow()
        session = CurrentUserSession()
        workflow.username = session.username
        workflow.userId = session.userId
        workflow.pluginCodeRef = session.getPluginCodeRef()
        workflow.timestampIso = datetime.datetime.now().isoformat()
        specsByName = {spec.name: spec for spec in self.__plugin.metadata(workflow)}
        for name, value in self.__readMetadata().items():
            spec = specsByName.get(name)
            field = SpectralWorkflowMetadata()
            field.name = name
            field.label = spec.label if spec else name
            field.type = spec.type if spec else "TEXT"
            field.value = value
            field.showInWorkflowsTable = spec.showInWorkflowsTable if spec else False
            field.order = spec.order if spec else 0
            workflow.addToMetadataFields(field)
        PersistSpectralWorkflowLogicModule().save(workflow)
        self.resetToNewMode()
        self.__goHome()

    def __saveMetadataEdits(self):
        PersistSpectralWorkflowLogicModule().updateMetadata(
            self.__viewWorkflowId, self.__readMetadata(), userId=CurrentUserSession().userId)
        self.resetToNewMode()
        self.__goHome()

    def __deleteWorkflow(self):
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
