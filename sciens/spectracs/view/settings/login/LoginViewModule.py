from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel, QLineEdit, QPushButton, QWidget

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.appliction.style.Metrics import Metrics
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
from sciens.spectracs.logic.session.ActiveSpectrometerProfileLogicModule import ActiveSpectrometerProfileLogicModule
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget


class LoginViewModule(PageWidget):
    """In-window login page — the single login surface on BOTH desktop and Android (§G3a; the desktop
    ServiceLoginDialog QDialog was retired).

    Qt-for-Android allows only ONE top-level window / EGL surface, so a QDialog login aborts the app
    ("Failed to acquire deadlock protector for QAndroidPlatformOpenGLWindow::eglSurface()"). This renders
    the form as a page in the main QStackedWidget instead (see docs/SPEC_android_port.md P4c). Login goes
    through SpectracsPyServerClient().login() against the server; errors render INLINE (a QMessageBox
    would be a second window and crash too). Register lives in the body; Login/Back in the footer (§G4b).
    """

    # Short form: compact fields, centred vertically (not top-packed) so the login sits mid-height, and
    # capped/centred horizontally at Metrics.CONTENT_MAX_WIDTH so it doesn't stretch across a wide desktop.
    compactMainContainer = True
    verticalCenterMainContainer = True
    maxContentWidth = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__usernameComponent = None
        self.__passwordComponent = None
        self.__errorLabel = None
        self.__registerButton = None

    def _getPageTitle(self):
        return 'Login'

    def showEvent(self, event):
        # Every time the login view opens (incl. after logout): start empty, no stale error, username active.
        super().showEvent(event)
        self.getUsernameComponent().clear()
        self.getPasswordComponent().clear()
        self.getErrorLabel().setVisible(False)
        # Defer focus until after the widget is actually shown (setFocus in showEvent is unreliable).
        QTimer.singleShot(0, lambda: self.getUsernameComponent().setFocus())

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

    def getRegisterButton(self):
        # §G4b: Register is a mode-switch, so it lives in the form BODY, not the footer (the footer holds
        # the primary Login + Back).
        if self.__registerButton is None:
            self.__registerButton = QPushButton("New here? Register")
            self.__registerButton.setProperty("buttonType", "secondary")
            self.__registerButton.clicked.connect(self.onClickedRegisterButton)
        return self.__registerButton

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()
        # One shared grid so Username/Password share a single label-column width (aligned edges), and the
        # full-width Register button below lines up with that column's left edge.
        result['form'] = self.createForm([
            ('Username', self.getUsernameComponent()),
            ('Password', self.getPasswordComponent()),
        ])
        result['error'] = self.getErrorLabel()
        # Register spans the full (capped) form width.
        result['register'] = self.getRegisterButton()
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
            # Install the user's calibrated profile (by serial) into ApplicationSettings so views that read
            # the active profile — e.g. the dev measurement bench — see it (SPEC_dev_measure_bench §11).
            ActiveSpectrometerProfileLogicModule().installFromSession()
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

    def onClickedRegisterButton(self):
        self.__navigateTo("RegistrationViewModule")

    def onClickedBackButton(self):
        self.__navigateTo("Home")

    def __navigateTo(self, target):
        navigationHandler = ApplicationContextLogicModule().getNavigationHandler()
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            navigationHandler.handleNavigationSignal)
        signal = NavigationSignal(None)
        signal.setTarget(target)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(signal)
