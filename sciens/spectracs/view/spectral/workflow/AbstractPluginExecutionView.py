import datetime

from PySide6.QtCore import QDate
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton, QTabWidget, QLabel, QWidget, QVBoxLayout, QLineEdit, QDateEdit

from sciens.spectracs.logic.application.style.Metrics import Metrics
from sciens.spectracs.logic.persistence.database.spectral.PersistSpectralWorkflowLogicModule import PersistSpectralWorkflowLogicModule
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.logic.spectral.workflow.SpectralWorkflowEngine import SpectralWorkflowEngine
from sciens.spectracs.logic.spectral.navigation.NavigationModel import NavigationModel
from sciens.spectracs.logic.spectral.navigation.NavigationFlow import NavigationFlow
from sciens.spectracs.logic.spectral.navigation.NavStop import NavStop, NavStopKind
from sciens.spectracs.model.spectral.SpectralWorkflowMetadata import SpectralWorkflowMetadata
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.plugin_sdk.policy.WorkflowPolicy import WorkflowPolicy
from sciens.spectracs.view.application.widgets.StepBarWidget import StepBarWidget
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget

_COMPUTED = (SpectralWorkflowPhaseType.PROCESSING, SpectralWorkflowPhaseType.EVALUATION)


class AbstractPluginExecutionView(PageWidget):
    # The shared host for running a plugin's SpectralWorkflow (SPEC_simplified_plugin_navigation.md §10, M2). It
    # owns the generic NAVIGATION (chevron plan, cursor, Back/Next, the AUTO_ADVANCE jump, terminal/finish) driven
    # by NavigationModel + NavigationFlow, PLUS the shared metadata form and run persistence (D-save: both hosts
    # save). The two thin subclasses (end-user view + dev bench) differ essentially only in how the plugin is
    # chosen (`_resolvePlugin`), where the content renders (`_renderStop`), and where "leave" goes (`_leave`).
    #
    # NEW mode: build the engine, run the declarative hooks, plan the chevron, populate computed phases lazily on
    # arrival (or all-at-once on the jump). VIEW mode: a loaded workflow renders read-only with an editable
    # metadata form; nothing runs.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # instance defaults so signal handlers wired during initialize() (before a run starts) are safe
        self._rendering = False
        self._loadedWorkflow = None
        self._plan = []

    # --- subclass seams ---

    def _resolvePlugin(self):
        raise NotImplementedError            # NEW: the SpectralPlugin to run

    def _renderStop(self, navStop, container):
        raise NotImplementedError            # build content for a non-metadata stop into `container` (a QTabWidget)

    def _leave(self):
        raise NotImplementedError            # navigate away after finish/cancel (end-user -> Home; bench -> Settings)

    def _canAdvanceFrom(self, navStop):
        return True                          # gate a forward Next (e.g. ACQUISITION requires captures)

    def _beforeRender(self):
        pass                                 # e.g. stop the live camera before the tab area is cleared

    def _afterNav(self):
        pass                                 # e.g. refresh acquisition guidance — runs on every nav refresh,
        #                                      including after a capture (not only on a full re-render)

    def _decorateNav(self, terminal):
        pass                                 # e.g. paint the amber Next-arrow on a non-terminal proceed

    # --- shared scaffolding ---

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()
        self._messageLabel = QLabel("")
        result['message'] = self._messageLabel
        self._stepBar = StepBarWidget()
        result['stepBar'] = self._stepBar
        self._tabWidget = QTabWidget()
        self._tabWidget.setObjectName("PluginExecutionView.tabWidget")  # Director anchor (§10)
        result['tabs'] = self._tabWidget
        return result

    def createNavigationGroupBox(self):
        result = super().createNavigationGroupBox()
        layout = result.layout()
        self._backButton = QPushButton("← Back")
        self._backButton.setObjectName("PluginExecutionView.backButton")
        self._backButton.clicked.connect(self.onClickedBack)
        layout.addWidget(self._backButton, 0, 0, 1, 1)
        self._nextButton = QPushButton("Next →")
        self._nextButton.setObjectName("PluginExecutionView.nextButton")
        self._nextButton.clicked.connect(self.onClickedNext)
        layout.addWidget(self._nextButton, 0, 3, 1, 1)
        return result

    # --- run lifecycle ---

    def _resetRunState(self):
        self._cursor = 0
        self._hooksRun = set()
        self._loadedWorkflow = None
        self._plugin = None
        self._engine = None
        self._metadataWidgets = {}
        self._plan = []
        self._rendering = False

    def _startNewRun(self):
        self._resetRunState()
        self._messageLabel.setText("")
        plugin = self._resolvePlugin()
        if plugin is None:
            self._messageLabel.setText("No plugin configured.")
            self._stepBar.setSteps([])
            self._tabWidget.clear()
            return False
        self._plugin = plugin
        self._engine = SpectralWorkflowEngine(plugin)
        self._runHookOnce(SpectralWorkflowPhaseType.ACQUISITION)
        self._runHookOnce(SpectralWorkflowPhaseType.PUBLISHING)   # static -> detect if declared
        self._rebuildPlan()
        self._renderCursor()
        return True

    def _startViewRun(self, loadedWorkflow):
        # VIEW mode: render a persisted run read-only (the subclass loaded it). No engine, no hooks.
        self._resetRunState()
        self._messageLabel.setText("")
        self._loadedWorkflow = loadedWorkflow
        self._rebuildPlan()
        self._renderCursor()

    def _isView(self):
        return self._loadedWorkflow is not None

    def _workflow(self):
        return self._loadedWorkflow if self._loadedWorkflow is not None else self._engine.getWorkflow()

    def _policy(self):
        # VIEW browses with default STEP nav regardless of the run's plugin.
        plugin = self._plugin
        return plugin.policy() if (plugin is not None and not self._isView()) else WorkflowPolicy.default()

    def _mode(self):
        return self._policy().getNavigation().getMode()

    def _runHookOnce(self, phaseType):
        if phaseType not in self._hooksRun:
            self._engine.runPhaseHook(phaseType)
            self._hooksRun.add(phaseType)
        return self._engine.getWorkflow().getPhase(phaseType)

    # --- the plan (chevron) ---

    def _hasMetadataFields(self):
        if self._isView():
            return len(self._loadedWorkflow.getMetadataFields()) > 0
        return self._plugin is not None and len(self._plugin.metadata(self._engine.getWorkflow())) > 0

    def _plannedPhases(self):
        workflow = self._workflow()
        if self._isView():
            # actual persisted phases + metadata if there are rows
            planned = [pt for pt in NavigationModel.PHASE_ORDER
                       if workflow.getPhase(pt) is not None and len(workflow.getPhase(pt).getSteps()) > 0]
            if self._hasMetadataFields():
                planned.append(SpectralWorkflowPhaseType.METADATA)
            return planned
        # NEW: predictive plan — ACQUISITION (declared), the computed spine, METADATA (if fields), PUBLISHING (if declared)
        planned = []
        acquisition = workflow.getPhase(SpectralWorkflowPhaseType.ACQUISITION)
        if acquisition is not None and len(acquisition.getSteps()) > 0:
            planned.append(SpectralWorkflowPhaseType.ACQUISITION)
        planned.append(SpectralWorkflowPhaseType.PROCESSING)
        planned.append(SpectralWorkflowPhaseType.EVALUATION)
        if self._hasMetadataFields():
            planned.append(SpectralWorkflowPhaseType.METADATA)
        publishing = workflow.getPhase(SpectralWorkflowPhaseType.PUBLISHING)
        if publishing is not None and len(publishing.getSteps()) > 0:
            planned.append(SpectralWorkflowPhaseType.PUBLISHING)
        return planned

    def _rebuildPlan(self):
        policy = self._policy().getNavigation()
        workflow = self._workflow()
        plan = []
        for phaseType in self._plannedPhases():
            phase = workflow.getPhase(phaseType)
            steps = list(phase.getSteps().values()) if phase is not None else []
            if steps and policy.expandsSteps(phaseType):
                for step in steps:
                    plan.append(NavStop(NavStopKind.STEP, phaseType, self._stepLabel(step, phaseType), step=step))
            else:
                plan.append(NavStop(NavStopKind.PHASE, phaseType, self._phaseLabel(phaseType)))
        self._plan = plan
        self._stepBar.setSteps([stop.label for stop in plan])

    def _phaseLabel(self, phaseType):
        return NavigationModel.PHASE_LABELS.get(phaseType, str(phaseType))

    def _stepLabel(self, step, phaseType):
        return step.getLabel() or self._phaseLabel(phaseType)

    # --- rendering ---

    def _renderCursor(self):
        if not self._plan:
            return
        self._rendering = True
        self._beforeRender()
        stop = self._plan[self._cursor]
        self._ensurePopulated(stop.phaseType)
        self._tabWidget.clear()
        self._tabWidget.tabBar().setVisible(True)
        if stop.phaseType == SpectralWorkflowPhaseType.METADATA:
            self._tabWidget.addTab(self._buildMetadataForm(), "Metadata")
        else:
            self._renderStop(stop, self._tabWidget)
        # Change F: a single-step phase shows its content directly, no redundant one-tab bar.
        if self._tabWidget.count() == 1:
            self._tabWidget.tabBar().setVisible(False)
        self._stepBar.setCurrentIndex(self._cursor)
        self._refreshNav()
        self._rendering = False

    def _ensurePopulated(self, phaseType):
        if phaseType in _COMPUTED and not self._isView():
            self._runHookOnce(phaseType)

    # --- navigation ---

    def onClickedBack(self):
        if self._cursor > 0:
            self._cursor -= 1
            # Returning to ACQUISITION means the user may re-capture -> drop the computed-phase cache so a
            # subsequent forward pass re-runs PROCESSING/EVALUATION against the fresh captures.
            if (not self._isView()
                    and self._plan[self._cursor].phaseType == SpectralWorkflowPhaseType.ACQUISITION):
                self._hooksRun.difference_update(_COMPUTED)
                for phaseType in _COMPUTED:
                    phase = self._engine.getWorkflow().getPhase(phaseType)
                    if phase is not None:
                        phase.getSteps().clear()
            self._renderCursor()

    def onClickedNext(self):
        stop = self._plan[self._cursor] if self._plan else None
        if stop is not None and not self._canAdvanceFrom(stop):
            return
        target = NavigationFlow.forwardTarget(self._plan, self._cursor, self._mode())
        if target is None:
            self._onFinish()
            return
        for index in range(self._cursor + 1, target + 1):   # populate everything jumped over (Back-reachable)
            self._ensurePopulated(self._plan[index].phaseType)
        self._cursor = target
        self._renderCursor()

    def _isTerminal(self):
        return NavigationFlow.isTerminal(self._plan, self._cursor)

    def _refreshNav(self):
        self._backButton.setEnabled(self._cursor > 0)
        terminal = self._isTerminal()
        stop = self._plan[self._cursor] if self._plan else None
        self._nextButton.setText(self._terminalLabel() if terminal else "Next")
        self._nextButton.setIcon(QIcon())
        self._nextButton.setEnabled(True if terminal else (stop is None or self._canAdvanceFrom(stop)))
        self._decorateNav(terminal)
        self._afterNav()   # refresh guidance here so it also updates after a capture (onCaptured -> _refreshNav)

    def _terminalLabel(self):
        return "Save changes" if self._isView() else "Save"

    # --- metadata form (shared; both hosts) ---

    def _metadataSpecs(self):
        # (name, label, type, value) — from the loaded rows (VIEW) or the plugin's MetadataFields (NEW).
        if self._isView():
            rows = sorted(self._loadedWorkflow.getMetadataFields(), key=lambda field: field.order or 0)
            return [(row.name, row.label, row.type, row.value) for row in rows]
        specs = sorted(self._plugin.metadata(self._engine.getWorkflow()), key=lambda spec: spec.order)
        return [(spec.name, spec.label, spec.type, "") for spec in specs]

    def _buildMetadataForm(self):
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(Metrics.M, Metrics.M, Metrics.M, Metrics.M)
        panel.setLayout(layout)
        self._metadataWidgets = {}
        for name, label, fieldType, value in self._metadataSpecs():
            if fieldType == "DATE":
                widget = QDateEdit()
                widget.setDisplayFormat("yyyy-MM-dd")
                widget.setCalendarPopup(True)
                widget.setDate(QDate.fromString(value, "yyyy-MM-dd") if value else QDate.currentDate())
            else:
                widget = QLineEdit()
                widget.setText("" if value is None else str(value))
            self._metadataWidgets[name] = (widget, fieldType)
            layout.addWidget(self.createLabeledComponent(label, widget))
        layout.addStretch(1)
        return panel

    def _readMetadata(self):
        result = {}
        for name, (widget, fieldType) in self._metadataWidgets.items():
            result[name] = widget.date().toString("yyyy-MM-dd") if fieldType == "DATE" else widget.text()
        return result

    # --- finish / persistence (D-save: both hosts save) ---

    def _onFinish(self):
        if self._isView():
            self._persistMetadataEdits()
        else:
            self._persistNewRun()
        self._leave()

    def _pluginProvenance(self):
        # (codeRef, version) credited on a saved run. Default = the logged-in user's assigned plugin; the bench
        # overrides it with the actually-selected plugin.
        session = CurrentUserSession()
        return session.getPluginCodeRef(), session.getPluginVersion()

    def _persistNewRun(self):
        workflow = self._engine.getWorkflow()
        session = CurrentUserSession()
        codeRef, version = self._pluginProvenance()
        workflow.username = session.username
        workflow.userId = session.userId
        workflow.pluginCodeRef = codeRef
        workflow.pluginVersion = version
        workflow.timestampIso = datetime.datetime.now().isoformat()
        specsByName = {spec.name: spec for spec in self._plugin.metadata(workflow)}
        for name, value in self._readMetadata().items():
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

    def _persistMetadataEdits(self):
        PersistSpectralWorkflowLogicModule().updateMetadata(
            self._loadedWorkflow.id, self._readMetadata(), userId=CurrentUserSession().userId)
