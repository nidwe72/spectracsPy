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


class SpectrometerProfilesTableModel(QAbstractTableModel):
    HEADERS = ['Serial', 'Device']

    def __init__(self, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.__profiles = []

    def setProfiles(self, profiles):
        self.beginResetModel()
        self.__profiles = profiles or []
        self.endResetModel()

    def getProfileAt(self, row: int):
        if 0 <= row < len(self.__profiles):
            return self.__profiles[row]
        return None

    def rowCount(self, parent=QModelIndex()):
        return len(self.__profiles)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        profile = self.__profiles[index.row()]
        if index.column() == 0:
            return profile.get('serial')
        if index.column() == 1:
            return profile.get('deviceCodeName')
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[section]
        return None


class SpectrometerProfileAuthoringListViewModule(PageWidget):
    """Master profile list (SPEC_connection_and_calibration_ux.md §4.1.b)."""

    tableView: QTableView = None
    profilesTableModel: SpectrometerProfilesTableModel = None
    bannerLabel: QLabel = None

    def _getPageTitle(self):
        return "Settings > Spectrometer profiles (authoring)"

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
        self.profilesTableModel = SpectrometerProfilesTableModel()
        self.tableView.setModel(self.profilesTableModel)
        applyTableLayout(self.tableView)
        self.tableView.verticalHeader().setVisible(False)
        self.tableView.doubleClicked.connect(self.onDoubleClickedRow)
        result['table'] = self.tableView

        self.refresh()
        return result

    def showEvent(self, event):
        super().showEvent(event)
        if self.profilesTableModel is not None:
            self.refresh()

    def refresh(self):
        if not CurrentUserSession().hasRole(UserRoleType.MASTER_USER.value):
            self.__showBanner("Not authorized.")
            self.profilesTableModel.setProfiles([])
            return
        profiles = SpectracsPyServerClient().listSpectrometerProfiles()
        if profiles is None:
            self.__showBanner("Server unavailable — cannot load profiles.")
            self.profilesTableModel.setProfiles([])
        else:
            self.bannerLabel.setVisible(False)
            self.profilesTableModel.setProfiles(profiles)

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

    def __getSelectedProfile(self):
        index = self.tableView.currentIndex()
        if index is not None and index.isValid():
            return self.profilesTableModel.getProfileAt(index.row())
        return None

    def onClickedAddButton(self):
        self.__openEditor(None)

    def onClickedEditButton(self):
        profile = self.__getSelectedProfile()
        if profile is not None:
            self.__openEditor(profile)

    def onDoubleClickedRow(self, index):
        self.onClickedEditButton()

    def __openEditor(self, dto):
        from sciens.spectracs.view.settings.spectrometerProfileAuthoring.SpectrometerProfileAuthoringViewModule import \
            SpectrometerProfileAuthoringViewModule
        navigationSignal = NavigationSignal(None)
        navigationSignal.setTarget("SpectrometerProfileAuthoringViewModule")
        targetViewModule = ApplicationContextLogicModule().getNavigationHandler().getViewModule(navigationSignal)
        if isinstance(targetViewModule, SpectrometerProfileAuthoringViewModule):
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
