from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import QAbstractItemView, QGridLayout, QGroupBox, QLabel, QPushButton, QTableView

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.appliction.style.Metrics import Metrics
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.model.databaseEntity.application.user.UserRoleType import UserRoleType
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget
from sciens.spectracs.view.application.widgets.table.TableLayoutUtil import applyTableLayout


class SpectrometerSetupsTableModel(QAbstractTableModel):
    HEADERS = ['Serial', 'Plugin']

    def __init__(self, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.__setups = []

    def setSetups(self, setups):
        self.beginResetModel()
        self.__setups = setups or []
        self.endResetModel()

    def getSetupAt(self, row: int):
        if 0 <= row < len(self.__setups):
            return self.__setups[row]
        return None

    def rowCount(self, parent=QModelIndex()):
        return len(self.__setups)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        setup = self.__setups[index.row()]
        if index.column() == 0:
            return setup.get('serial')
        if index.column() == 1:
            codeRef = setup.get('pluginCodeRef') or ''
            return codeRef.split('.')[-1]
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[section]
        return None


class SpectrometerSetupListViewModule(PageWidget):
    """Master instrument-setup list (SPEC_connection_and_calibration_ux.md §4.1.c)."""

    tableView: QTableView = None
    setupsTableModel: SpectrometerSetupsTableModel = None
    bannerLabel: QLabel = None

    def _getPageTitle(self):
        return "Settings > Spectrometer setups"

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        if self.bannerLabel is None:
            self.bannerLabel = QLabel("")
            self.bannerLabel.setVisible(False)
        result['banner'] = self.bannerLabel

        if self.tableView is None:
            self.tableView = QTableView()
        self.tableView.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableView.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableView.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setupsTableModel = SpectrometerSetupsTableModel()
        self.tableView.setModel(self.setupsTableModel)
        applyTableLayout(self.tableView)
        self.tableView.verticalHeader().setVisible(False)
        self.tableView.doubleClicked.connect(self.onDoubleClickedRow)
        result['table'] = self.tableView

        self.refresh()
        return result

    def showEvent(self, event):
        super().showEvent(event)
        if self.setupsTableModel is not None:
            self.refresh()

    def refresh(self):
        if not CurrentUserSession().hasRole(UserRoleType.MASTER_USER.value):
            self.__showBanner("Not authorized.")
            self.setupsTableModel.setSetups([])
            return
        setups = SpectracsPyServerClient().listSpectrometerSetups()
        if setups is None:
            self.__showBanner("Server unavailable — cannot load setups.")
            self.setupsTableModel.setSetups([])
        else:
            self.bannerLabel.setVisible(False)
            self.setupsTableModel.setSetups(setups)

    def __showBanner(self, text):
        self.bannerLabel.setText(text)
        self.bannerLabel.setVisible(True)

    def createNavigationGroupBox(self):
        result = QGroupBox("")
        result.setProperty("plain", True)
        layout = QGridLayout()
        layout.setSpacing(Metrics.S)
        layout.setContentsMargins(0, 0, 0, 0)
        result.setLayout(layout)

        backButton = QPushButton()
        backButton.setText("Back")
        layout.addWidget(backButton, 0, 0, 1, 1)
        backButton.clicked.connect(self.onClickedBackButton)

        addButton = QPushButton()
        addButton.setText("Add")
        layout.addWidget(addButton, 0, 1, 1, 1)
        addButton.clicked.connect(self.onClickedAddButton)

        editButton = QPushButton()
        editButton.setText("Edit")
        layout.addWidget(editButton, 0, 2, 1, 1)
        editButton.clicked.connect(self.onClickedEditButton)

        return result

    def __getSelectedSetup(self):
        index = self.tableView.currentIndex()
        if index is not None and index.isValid():
            return self.setupsTableModel.getSetupAt(index.row())
        return None

    def onClickedAddButton(self):
        self.__openEditor(None)

    def onClickedEditButton(self):
        setup = self.__getSelectedSetup()
        if setup is not None:
            self.__openEditor(setup)

    def onDoubleClickedRow(self, index):
        self.onClickedEditButton()

    def __openEditor(self, dto):
        from sciens.spectracs.view.settings.spectrometerSetup.SpectrometerSetupViewModule import \
            SpectrometerSetupViewModule
        navigationSignal = NavigationSignal(None)
        navigationSignal.setTarget("SpectrometerSetupViewModule")
        targetViewModule = ApplicationContextLogicModule().getNavigationHandler().getViewModule(navigationSignal)
        if isinstance(targetViewModule, SpectrometerSetupViewModule):
            targetViewModule.loadView(dto)
            self.__emitNavigation(navigationSignal)

    def onClickedBackButton(self):
        navigationSignal = NavigationSignal(None)
        navigationSignal.setTarget("SettingsViewModule")
        self.__emitNavigation(navigationSignal)

    def __emitNavigation(self, navigationSignal: NavigationSignal):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(navigationSignal)
