from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import QWidget, QGridLayout, QTableView, QAbstractItemView, QPushButton, QHeaderView

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.view.application.widgets.InWindowDialog import InWindowDialog
from sciens.spectracs.logic.persistence.database.spectral.PersistSpectralWorkflowLogicModule import PersistSpectralWorkflowLogicModule
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.model.spectral.plugin.view.VerdictView import VerdictView


def _verdictView(workflow):
    phase = workflow.getPhase(SpectralWorkflowPhaseType.EVALUATION)
    if phase is None:
        return None
    for step in phase.getSteps().values():
        evaluationResult = step.getEvaluationResult()
        if evaluationResult is not None:
            for item in evaluationResult.getItems():
                if isinstance(item, VerdictView):
                    return item
    return None


class WorkflowsTableModel(QAbstractTableModel):
    # Data-driven columns: Date · Verdict · Hue + one column per `showInWorkflowsTable` metadata field
    # (union across the listed workflows; blank where a row lacks the field). SPEC_workflow_persistence §6.

    def __init__(self):
        super().__init__()
        self.__workflows = []
        self.__columns = ["Date", "Verdict", "Hue"]
        self.__metadataNames = []

    def setWorkflows(self, workflows):
        self.beginResetModel()
        self.__workflows = workflows
        labelByName = {}
        for workflow in workflows:
            for field in workflow.getMetadataFields():
                if field.showInWorkflowsTable and field.name not in labelByName:
                    labelByName[field.name] = field.label or field.name
        self.__metadataNames = list(labelByName.keys())
        self.__columns = ["Date", "Verdict", "Hue"] + [labelByName[name] for name in self.__metadataNames]
        self.endResetModel()

    def getWorkflowAt(self, row):
        return self.__workflows[row]

    def rowCount(self, parent=QModelIndex()):
        return len(self.__workflows)

    def columnCount(self, parent=QModelIndex()):
        return len(self.__columns)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.__columns[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        workflow = self.__workflows[index.row()]
        column = index.column()
        if column == 0:
            return (workflow.timestampIso or "").replace("T", " ")[:19]
        if column == 1:
            verdict = _verdictView(workflow)
            return verdict.roastState if verdict is not None else ""
        if column == 2:
            verdict = _verdictView(workflow)
            if verdict is not None and verdict.hueDegrees is not None:
                return "%.0f°" % verdict.hueDegrees
            return ""
        name = self.__metadataNames[column - 3]
        for field in workflow.getMetadataFields():
            if field.name == name:
                return field.value or ""
        return ""


class SpectralJobsOverviewViewModule(QWidget):
    # The per-user saved-runs table on the Home screen. Double-click a row -> open the wizard in VIEW mode.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        layout = QGridLayout()
        self.setLayout(layout)
        self.__model = WorkflowsTableModel()
        self.tableView = QTableView()
        self.tableView.setModel(self.__model)
        self.tableView.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tableView.verticalHeader().setVisible(False)  # no empty row-number gutter (first "empty column")
        # Share the full width across all columns instead of ballooning the last one into a wide empty band.
        self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tableView.doubleClicked.connect(self.onDoubleClicked)
        layout.addWidget(self.tableView, 0, 0, 1, 1)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        userId = CurrentUserSession().userId
        workflows = PersistSpectralWorkflowLogicModule().listForUser(userId) if userId else []
        self.__model.setWorkflows(workflows)

    def __selectedWorkflow(self):
        index = self.tableView.currentIndex()
        if index is not None and index.isValid():
            return self.__model.getWorkflowAt(index.row())
        return None

    def onDoubleClicked(self, index: QModelIndex):
        if index.isValid():
            self.__openInViewMode(self.__model.getWorkflowAt(index.row()))

    def onClickedEdit(self):
        workflow = self.__selectedWorkflow()
        if workflow is not None:
            self.__openInViewMode(workflow)

    def onClickedDelete(self):
        workflow = self.__selectedWorkflow()
        if workflow is None:
            return
        if not InWindowDialog.confirm(self, "Delete measurement",
                                      "This measurement will be permanently deleted. Continue?",
                                      destructive=True):
            return
        PersistSpectralWorkflowLogicModule().delete(workflow.id, userId=CurrentUserSession().userId)
        self.refresh()

    def __openInViewMode(self, workflow):
        signal = NavigationSignal(None)
        signal.setTarget("WizardViewModule")
        wizard = ApplicationContextLogicModule().getNavigationHandler().getViewModule(signal)
        if wizard is not None and hasattr(wizard, "setViewWorkflow"):
            wizard.setViewWorkflow(workflow.id)
            ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
                ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
            ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(signal)
