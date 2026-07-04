from PySide6.QtWidgets import QGridLayout, QGroupBox, QPushButton, QLineEdit, QComboBox, QCheckBox, \
    QWidget, QHBoxLayout

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.view.application.widgets.InWindowDialog import InWindowDialog
from sciens.spectracs.logic.appliction.style.Metrics import Metrics
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.model.databaseEntity.DbEntityCrudOperation import DbEntityCrudOperation
from sciens.spectracs.model.databaseEntity.application.user.UserRoleType import UserRoleType
from sciens.spectracs.model.signal.UserSignal import UserSignal
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget


class UserViewModule(PageWidget):
    """Add/edit a single AppUser. Reads/writes over Pyro (the user store is server-owned).
    Holds a plain user DTO (dict) — None means 'create a new user'."""

    dto: dict = None
    username: QLineEdit = None
    displayName: QLineEdit = None
    password: QLineEdit = None
    roleComboBox: QComboBox = None
    enabledCheckBox: QCheckBox = None
    compactMainContainer = True  # form page: pack fields at the top, don't spread

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _getPageTitle(self):
        return "Settings > Users > User"

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        self.username = QLineEdit()
        result['username'] = self.createLabeledComponent('Username', self.username)

        self.displayName = QLineEdit()
        result['displayName'] = self.createLabeledComponent('Display name', self.displayName)

        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        result['password'] = self.createLabeledComponent('Password', self.password)

        self.roleComboBox = QComboBox()
        for roleType in UserRoleType:
            self.roleComboBox.addItem(roleType.value)
        result['role'] = self.createLabeledComponent('Role', self.roleComboBox)

        self.enabledCheckBox = QCheckBox()
        self.enabledCheckBox.setFixedHeight(22)  # compact row (override the 50px button height)
        # Wrap the checkbox so it sits left at its natural size instead of being stretched
        # across the 70% field column (which makes the themed indicator look like a big box).
        enabledContainer = QWidget()
        enabledLayout = QHBoxLayout()
        enabledLayout.setContentsMargins(0, 0, 0, 0)
        enabledLayout.addWidget(self.enabledCheckBox)
        enabledLayout.addStretch(1)
        enabledContainer.setLayout(enabledLayout)
        result['enabled'] = self.createLabeledComponent('Enabled', enabledContainer)

        self.__applyModelToWidgets()
        return result

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

        saveButton = QPushButton()
        saveButton.setText("Save")
        layout.addWidget(saveButton, 0, 1, 1, 1)
        saveButton.clicked.connect(self.onClickedSaveButton)

        return result

    def __isCreate(self) -> bool:
        return self.dto is None or self.dto.get('userId') is None

    def __applyModelToWidgets(self):
        if self.username is None:
            return

        if self.__isCreate():
            self.username.setText('')
            self.username.setReadOnly(False)
            self.displayName.setText('')
            self.password.setText('')
            self.password.setPlaceholderText('required, min 8 characters')
            self.roleComboBox.setCurrentText(UserRoleType.END_USER.value)
            self.enabledCheckBox.setChecked(True)
        else:
            self.username.setText(self.dto.get('username') or '')
            self.username.setReadOnly(True)  # username is immutable after creation
            self.displayName.setText(self.dto.get('displayName') or '')
            self.password.setText('')
            self.password.setPlaceholderText('leave blank to keep current (min 8 if changed)')
            roles = self.dto.get('roles') or []
            self.roleComboBox.setCurrentText(roles[0] if roles else UserRoleType.END_USER.value)
            self.enabledCheckBox.setChecked(bool(self.dto.get('enabled')))

    def getModel(self) -> dict:
        return self.dto

    def setModel(self, dto: dict):
        self.dto = dto
        self.__applyModelToWidgets()

    def loadView(self, dto: dict):
        self.setModel(dto)

    def onClickedSaveButton(self):
        displayName = self.displayName.text()
        password = self.password.text()
        roleName = self.roleComboBox.currentText()
        enabled = self.enabledCheckBox.isChecked()

        if self.__isCreate():
            username = self.username.text().strip()
            result = SpectracsPyServerClient().createUser(username, password, displayName, enabled, roleName)
            operation = DbEntityCrudOperation.CREATE
        else:
            userId = self.dto.get('userId')
            result = SpectracsPyServerClient().updateUser(userId, displayName, enabled, roleName, password)
            operation = DbEntityCrudOperation.UPDATE

        if not result.get('ok'):
            InWindowDialog.notify(self, "Save failed", result.get('message') or "save failed")
            return

        # Self-edit notice: a master changing their own account is allowed, but the live
        # session keeps its current role/state until next login.
        if (not self.__isCreate()) and self.dto.get('userId') == CurrentUserSession().userId:
            InWindowDialog.notify(self, "Saved",
                                  "Changes to your own account take effect on next login.")

        userSignal = UserSignal().setEntity(result).setOperation(operation)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitUserSignal(userSignal)
        self.__navigateToList()

    def onClickedBackButton(self):
        self.__navigateToList()

    def __navigateToList(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("UserListViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)
