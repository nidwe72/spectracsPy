from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel, QLineEdit, QPushButton

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.appliction.style.Metrics import Metrics
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget


class LoginViewModule(PageWidget):
    """In-window login page — the Android-safe counterpart of ServiceLoginDialog.

    Qt-for-Android allows only ONE top-level window / EGL surface, so showing ServiceLoginDialog (a
    QDialog) aborts the app ("Failed to acquire deadlock protector for
    QAndroidPlatformOpenGLWindow::eglSurface()"). This renders the same form as a page in the main
    QStackedWidget instead (see docs/SPEC_android_port.md P4c). Login logic is identical — it goes
    through SpectracsPyServerClient().login() against the local server; errors render INLINE (a
    QMessageBox would be a second window and crash too).
    """

    # Form page: pack fields at natural height near the top, not spread over the panel.
    compactMainContainer = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__usernameComponent = None
        self.__passwordComponent = None
        self.__errorLabel = None

    def _getPageTitle(self):
        return 'Login'

    def getUsernameComponent(self):
        if self.__usernameComponent is None:
            self.__usernameComponent = QLineEdit()
        return self.__usernameComponent

    def getPasswordComponent(self):
        if self.__passwordComponent is None:
            self.__passwordComponent = QLineEdit()
            self.__passwordComponent.setEchoMode(QLineEdit.EchoMode.Password)
            self.__passwordComponent.returnPressed.connect(self.onClickedLoginButton)
        return self.__passwordComponent

    def getErrorLabel(self):
        if self.__errorLabel is None:
            self.__errorLabel = QLabel("")
            self.__errorLabel.setProperty("error", True)  # QSS hook; inline colour is the fallback
            self.__errorLabel.setStyleSheet("color: #d9534f;")
            self.__errorLabel.setVisible(False)
        return self.__errorLabel

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()
        result['username'] = self.createLabeledComponent('Username', self.getUsernameComponent())
        result['password'] = self.createLabeledComponent('Password', self.getPasswordComponent())
        result['error'] = self.getErrorLabel()
        return result

    def createNavigationGroupBox(self):
        result = QGroupBox("")
        result.setProperty("plain", True)  # borderless holder (spec C2)

        layout = QGridLayout()
        layout.setSpacing(Metrics.S)
        layout.setContentsMargins(0, 0, 0, 0)
        result.setLayout(layout)

        loginButton = QPushButton("Login")
        loginButton.clicked.connect(self.onClickedLoginButton)
        layout.addWidget(loginButton, 0, 0, 1, 1)

        backButton = QPushButton("Back")
        backButton.setProperty("buttonType", "secondary")  # Bootstrap 'secondary' (gray)
        backButton.clicked.connect(self.onClickedBackButton)
        layout.addWidget(backButton, 0, 1, 1, 1)

        return result

    def onClickedLoginButton(self):
        username = self.getUsernameComponent().text()
        password = self.getPasswordComponent().text()

        result = SpectracsPyServerClient().login(username, password)
        if result.get("ok"):
            CurrentUserSession().login(result)
            ApplicationContextLogicModule().getApplicationSignalsProvider().emitUserSessionSignal()
            self.getErrorLabel().setVisible(False)
            self.getPasswordComponent().clear()
            # Launch seam: a user bound to a plugin lands in its wizard; otherwise Home.
            target = "WizardViewModule" if CurrentUserSession().getPluginCodeRef() else "Home"
            self.__navigateTo(target)
        else:
            message = result.get("message") or "invalid credentials"
            self.getErrorLabel().setText(message)
            self.getErrorLabel().setVisible(True)

    def onClickedBackButton(self):
        self.__navigateTo("Home")

    def __navigateTo(self, target):
        navigationHandler = ApplicationContextLogicModule().getNavigationHandler()
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            navigationHandler.handleNavigationSignal)
        signal = NavigationSignal(None)
        signal.setTarget(target)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(signal)
