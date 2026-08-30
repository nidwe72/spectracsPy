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
        # ⭐⭐ STAMP THE SECTION STRUCTURE ONTO THE RECORD, HERE (D4 / §27.16-N6). The plugin declares which
        # phases are sectioned by step; from this line on the WORKFLOW carries it, and the chevron, the PDF
        # and a LIMS addon all read it from there instead of from a live plugin.
        # ⛔ NOT AT SAVE, where the other provenance fields are stamped: the bench renders its PDF preview in
        # EVALUATION before anything is saved, so a save-time stamp would print the same run two ways.
        self._engine.getWorkflow().setSectionedPhases(plugin.policy().getNavigation().stepChevronPhases)
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
        # ⭐⭐ ONE DERIVATION OF "steps -> chevron" (SPEC_settled_measurement.md §27.16/N1). This method used
        # to re-implement NavigationModel.stops() inline, which meant the tested model was NOT the live one —
        # §27.11's lesson in another costume, and it would have made D4's persisted structure change nothing
        # on screen. The only real difference was the PREDICTIVE phase list, so that is passed IN.
        # ⭐⭐ THE STRUCTURE COMES FROM THE WORKFLOW, NOT FROM A LIVE PLUGIN (D4, §27.14a) — which is what
        # makes a re-opened run navigate the way it was measured. `_policy()` still answers the INTERACTION
        # question (auto-advance), and that one is correctly reset to the default when browsing a saved run.
        workflow = self._workflow()
        self._plan = NavigationModel.stops(workflow, plannedPhases=self._plannedPhases(),
                                           sectionedPhases=workflow.getSectionedPhases())
        self._stepBar.setSteps([stop.label for stop in self._plan])

    # ⛔ `_phaseLabel` / `_stepLabel` are GONE with the inline plan builder (§27.16/N1): they were this
    # class's private copies of NavigationModel.__phaseLabel / __stepLabel, and a second copy of a label rule
    # is how the chevron and the model drift apart. NavigationModel owns the labels now, alone.

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
            self._tabWidget.addTab(self._buildMetadataForm(), "Details")
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
            self._renderCursor()

    def onClickedNext(self):
        stop = self._plan[self._cursor] if self._plan else None
        if stop is not None and not self._canAdvanceFrom(stop):
            return
        target = NavigationFlow.forwardTarget(self._plan, self._cursor, self._mode(), canJump=self._canJump())
        if target is None:
            self._onFinish()
            return
        for index in range(self._cursor + 1, target + 1):   # populate everything jumped over (Back-reachable)
            self._ensurePopulated(self._plan[index].phaseType)
        self._cursor = target
        self._renderCursor()

    def _canJump(self):
        # Option C (SPEC_simplified_plugin_navigation.md §4.4a): the AUTO_ADVANCE jump past the computed phases
        # fires only on a FRESH capture pass — i.e. PROCESSING has not been computed yet (or was invalidated by a
        # re-capture, see _onCapture). A revisit to acquisition WITHOUT re-capturing leaves PROCESSING computed,
        # so paging forward steps through the phases one at a time instead of skipping to the metadata halt.
        return SpectralWorkflowPhaseType.PROCESSING not in getattr(self, "_hooksRun", set())

    def _onCapture(self):
        # A capture (re)invalidates the computed phases (SPEC §4.4a, Option C): drop the PROCESSING/EVALUATION
        # cache so the next forward pass recomputes them against the fresh frames — and, being fresh again,
        # re-arms the AUTO_ADVANCE jump. The hosts call this from their capture callbacks (replacing the former
        # invalidate-on-Back-into-acquisition hack); it then refreshes the nav so the Next gate reflects the
        # new capture state. No-op in VIEW mode (nothing runs).
        if not self._isView():
            self._hooksRun.difference_update(_COMPUTED)
            for phaseType in _COMPUTED:
                phase = self._engine.getWorkflow().getPhase(phaseType)
                if phase is not None:
                    phase.getSteps().clear()
        self._refreshNav()

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
            # Director anchor (SPEC_director_cut.md E1): a stable objectName per metadata field so the doc-mode
            # harness can focus + type into it (e.g. title / temperature). Field names are safe identifiers.
            widget.setObjectName("PluginExecutionView.metadata.%s" % name)
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
        # ⚠ KEEP the measurement time if the engine already stamped it (it does, at __buildWorkflow).
        # Overwriting here would replace "when it was measured" with "when it was filed", and those differ
        # by however long the operator spent looking at the result.
        if not workflow.timestampIso:
            workflow.timestampIso = datetime.datetime.now().isoformat(timespec="seconds")
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
