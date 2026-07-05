from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel, QLineEdit, QPushButton

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.appliction.style.Metrics import Metrics
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget


class RegistrationViewModule(PageWidget):
    """End-user self-registration (SPEC_connection_and_calibration_ux.md §4.2).

    Reached from the login page. The serial must already resolve to a master-authored instrument (else the
    factory-calibration message). On success the user is auto-logged-in (same seam as LoginViewModule)."""

    compactMainContainer = True

    username: QLineEdit = None
    password: QLineEdit = None
    email: QLineEdit = None
    firstName: QLineEdit = None
    lastName: QLineEdit = None
    serial: QLineEdit = None
    errorLabel: QLabel = None

    def _getPageTitle(self):
        return 'Register'

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()
        self.firstName = QLineEdit()
        result['firstName'] = self.createLabeledComponent('First name', self.firstName)
        self.lastName = QLineEdit()
        result['lastName'] = self.createLabeledComponent('Last name', self.lastName)
        self.email = QLineEdit()
        result['email'] = self.createLabeledComponent('Email', self.email)
        self.username = QLineEdit()
        result['username'] = self.createLabeledComponent('Username', self.username)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        result['password'] = self.createLabeledComponent('Password', self.password)
        self.serial = QLineEdit()
        self.serial.setPlaceholderText('XXXX-XXXX (from the label on your spectrometer)')
        result['serial'] = self.createLabeledComponent('Serial', self.serial)

        self.errorLabel = QLabel("")
        self.errorLabel.setStyleSheet("color: #d9534f;")
        self.errorLabel.setWordWrap(True)
        self.errorLabel.setVisible(False)
        result['error'] = self.errorLabel
        return result

    def createNavigationGroupBox(self):
        result = QGroupBox("")
        result.setProperty("plain", True)
        layout = QGridLayout()
        layout.setSpacing(Metrics.S)
        layout.setContentsMargins(0, 0, 0, 0)
        result.setLayout(layout)

        registerButton = QPushButton("Register")
        registerButton.clicked.connect(self.onClickedRegisterButton)
        layout.addWidget(registerButton, 0, 0, 1, 1)

        backButton = QPushButton("Back")
        backButton.setProperty("buttonType", "secondary")
        backButton.clicked.connect(self.onClickedBackButton)
        layout.addWidget(backButton, 0, 1, 1, 1)

        return result

    def __showError(self, message):
        self.errorLabel.setText(message)
        self.errorLabel.setVisible(True)

    def onClickedRegisterButton(self):
        username = self.username.text().strip()
        password = self.password.text()
        email = self.email.text().strip()
        firstName = self.firstName.text().strip()
        lastName = self.lastName.text().strip()
        serial = self.serial.text().strip()

        client = SpectracsPyServerClient()
        result = client.registerEndUser(username, password, email, firstName, lastName, serial)
        if not result.get("ok"):
            self.__showError(result.get("message") or "registration failed")
            return

        # Auto-login through the standard path so the instrument bundle lands in the session.
        loginResult = client.login(username, password)
        if loginResult.get("ok"):
            CurrentUserSession().login(loginResult)
            ApplicationContextLogicModule().getApplicationSignalsProvider().emitUserSessionSignal()
            self.errorLabel.setVisible(False)
            self.password.clear()
            target = "WizardViewModule" if CurrentUserSession().getPluginCodeRef() else "Home"
            self.__navigateTo(target)
        else:
            # Registered but auto-login failed (unexpected) — send them to the login page.
            self.__navigateTo("LoginViewModule")

    def onClickedBackButton(self):
        self.__navigateTo("LoginViewModule")

    def __navigateTo(self, target):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        signal = NavigationSignal(None)
        signal.setTarget(target)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(signal)
