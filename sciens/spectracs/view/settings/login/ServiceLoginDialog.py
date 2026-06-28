from PySide6.QtWidgets import QDialog, QGridLayout, QLabel, QLineEdit, QPushButton, QMessageBox

from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession


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

        cancelButton = QPushButton("Cancel")
        cancelButton.clicked.connect(self.reject)
        layout.addWidget(cancelButton, 2, 1, 1, 1)

    def onClickedLoginButton(self):
        username = self.usernameComponent.text()
        password = self.passwordComponent.text()

        result = SpectracsPyServerClient().login(username, password)
        if result.get("ok"):
            CurrentUserSession().login(result)
            self.accept()
        else:
            message = result.get("message") or "invalid credentials"
            QMessageBox.warning(self, "Login failed", message)
