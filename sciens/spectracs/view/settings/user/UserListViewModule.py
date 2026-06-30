from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import QGroupBox, QGridLayout, QPushButton, QTableView, QLabel, QAbstractItemView, QMessageBox

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.appliction.style.Metrics import Metrics
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.model.databaseEntity.application.user.UserRoleType import UserRoleType
from sciens.spectracs.model.signal.UserSignal import UserSignal
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget
from sciens.spectracs.view.settings.user.UserViewModule import UserViewModule


class UserListViewModule(PageWidget):
    """A selectable table of AppUsers with Add / Edit / Delete. Server-owned store, so it loads
    via Pyro and refreshes by re-fetching (not by local mutation)."""

    tableView: QTableView = None
    usersTableModel = None
    bannerLabel: QLabel = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ApplicationContextLogicModule().getApplicationSignalsProvider().userSignal.connect(self.handleUserSignal)

    def handleUserSignal(self, userSignal: UserSignal):
        # Any create/update/delete -> re-fetch from the server.
        if self.usersTableModel is not None:
            self.refresh()

    def createMainContainer(self):
        result = super().createMainContainer()
        result.setTitle("Settings > Users")
        return result

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

        self.usersTableModel = UsersTableModel()
        self.tableView.setModel(self.usersTableModel)
        self.tableView.horizontalHeader().setStretchLastSection(True)
        self.tableView.verticalHeader().setVisible(False)  # no empty row-number gutter
        self.tableView.doubleClicked.connect(self.onDoubleClickedRow)

        result['table'] = self.tableView

        self.refresh()
        return result

    def showEvent(self, event):
        # The store is server-owned and the role gate depends on the live session, so re-fetch
        # every time the page is navigated to — the one-time build-time refresh runs at app
        # startup (logged out) and would otherwise leave the screen stuck on that stale state.
        super().showEvent(event)
        if self.usersTableModel is not None:
            self.refresh()

    def refresh(self):
        # Defense in depth: even though the launch button is role-gated, refuse to populate
        # the table for a non-master that reaches this screen.
        if not CurrentUserSession().hasRole(UserRoleType.MASTER_USER.value):
            self.__showBanner("Not authorized.")
            self.usersTableModel.setUsers([])
            return

        users = SpectracsPyServerClient().listUsers()
        if users is None:
            # None sentinel = server unreachable (distinct from [] = no users).
            self.__showBanner("Server unavailable — cannot load users.")
            self.usersTableModel.setUsers([])
        else:
            self.bannerLabel.setVisible(False)
            self.usersTableModel.setUsers(users)

    def __showBanner(self, text: str):
        self.bannerLabel.setText(text)
        self.bannerLabel.setVisible(True)

    def createNavigationGroupBox(self):
        result = QGroupBox("")
        result.setProperty("plain", True)  # borderless holder (spec C2)

        layout = QGridLayout()
        layout.setSpacing(Metrics.S)
        layout.setContentsMargins(0, 0, 0, 0)  # align nav buttons to content edge (spec C7)
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

        deleteButton = QPushButton()
        deleteButton.setText("Delete")
        deleteButton.setProperty("buttonType", "secondary")  # gray, not red (deletion is guarded by a confirm dialog)
        layout.addWidget(deleteButton, 0, 3, 1, 1)
        deleteButton.clicked.connect(self.onClickedDeleteButton)

        return result

    def __getSelectedUser(self) -> dict:
        index = self.tableView.currentIndex()
        if index is not None and index.isValid():
            return self.usersTableModel.getUserAt(index.row())
        return None

    def __getUserEditor(self, navigationSignal) -> UserViewModule:
        return ApplicationContextLogicModule().getNavigationHandler().getViewModule(navigationSignal)

    def onClickedAddButton(self):
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("UserViewModule")
        targetViewModule = self.__getUserEditor(someNavigationSignal)
        if isinstance(targetViewModule, UserViewModule):
            targetViewModule.loadView(None)
            self.__emitNavigation(someNavigationSignal)

    def onClickedEditButton(self):
        user = self.__getSelectedUser()
        if user is None:
            return
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("UserViewModule")
        targetViewModule = self.__getUserEditor(someNavigationSignal)
        if isinstance(targetViewModule, UserViewModule):
            targetViewModule.loadView(user)
            self.__emitNavigation(someNavigationSignal)

    def onDoubleClickedRow(self, index: QModelIndex):
        self.onClickedEditButton()

    def onClickedDeleteButton(self):
        user = self.__getSelectedUser()
        if user is None:
            return
        confirm = QMessageBox.question(
            self, "Delete user",
            'Delete user "%s"? This cannot be undone.' % (user.get('username') or ''),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm != QMessageBox.StandardButton.Yes:
            return
        result = SpectracsPyServerClient().deleteUser(user.get('userId'))
        if not result.get('ok'):
            QMessageBox.warning(self, "Delete failed", result.get('message') or "delete failed")
            return
        self.refresh()

    def onClickedBackButton(self):
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SettingsViewModule")
        self.__emitNavigation(someNavigationSignal)

    def __emitNavigation(self, navigationSignal: NavigationSignal):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(navigationSignal)


class UsersTableModel(QAbstractTableModel):
    HEADERS = ['Username', 'Display name', 'Role', 'Enabled']

    def __init__(self, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.__users = []

    def setUsers(self, users):
        self.beginResetModel()
        self.__users = users or []
        self.endResetModel()

    def getUserAt(self, row: int):
        if 0 <= row < len(self.__users):
            return self.__users[row]
        return None

    def rowCount(self, parent=QModelIndex()):
        return len(self.__users)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        user = self.__users[index.row()]
        column = index.column()
        if column == 0:
            return user.get('username')
        if column == 1:
            return user.get('displayName') or ''
        if column == 2:
            return ', '.join(user.get('roles') or [])
        if column == 3:
            return 'yes' if user.get('enabled') else 'no'
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[section]
        return None
