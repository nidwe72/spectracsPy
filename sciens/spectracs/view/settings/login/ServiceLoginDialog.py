from PySide6.QtWidgets import QDialog, QGridLayout, QLabel, QLineEdit, QPushButton
from sciens.spectracs.view.application.widgets.InWindowDialog import InWindowDialog

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal


class ServiceLoginDialog(QDialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Service Login")

        layout = QGridLayout()
        self.setLayout(layout)

        layout.addWidget(QLabel("Username"), 0, 0, 1, 1)
        self.usernameComponent = QLineEdit()
        layout.addWidget(self.usernameComponent, 0, 1, 1, 1)

        layout.addWidget(QLabel("Password"), 1, 0, 1, 1)
        self.passwordComponent = QLineEdit()
        self.passwordComponent.setEchoMode(QLineEdit.Password)
        self.passwordComponent.returnPressed.connect(self.onClickedLoginButton)
        layout.addWidget(self.passwordComponent, 1, 1, 1, 1)

        loginButton = QPushButton("Login")
        loginButton.clicked.connect(self.onClickedLoginButton)
        layout.addWidget(loginButton, 2, 0, 1, 1)

        registerButton = QPushButton("Register")
        registerButton.setProperty("buttonType", "secondary")
        registerButton.clicked.connect(self.onClickedRegisterButton)
        layout.addWidget(registerButton, 2, 1, 1, 1)

        cancelButton = QPushButton("Cancel")
        cancelButton.setProperty("buttonType", "secondary")  # Bootstrap 'secondary' (gray), not primary
        cancelButton.clicked.connect(self.reject)
        layout.addWidget(cancelButton, 2, 2, 1, 1)

    def onClickedLoginButton(self):
        username = self.usernameComponent.text()
        password = self.passwordComponent.text()

        result = SpectracsPyServerClient().login(username, password)
        if result.get("ok"):
            CurrentUserSession().login(result)
            self.accept()
            # C.0 launch seam: a user configured to run a plugin lands straight in its measurement wizard.
            if CurrentUserSession().getPluginCodeRef():
                self.__navigateTo("WizardViewModule")
        else:
            message = result.get("message") or "invalid credentials"
            InWindowDialog.notify(self, "Login failed", message)

    def onClickedRegisterButton(self):
        # Close the desktop login dialog and open the in-window registration page (§4.2).
        self.reject()
        self.__navigateTo("RegistrationViewModule")

    def __navigateTo(self, target):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        signal = NavigationSignal(None)
        signal.setTarget(target)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(signal)
