from PySide6.QtWidgets import QGridLayout
from PySide6.QtWidgets import QGroupBox
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import QWidget

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.connection.ConnectionStatusLogicModule import ConnectionStatusLogicModule
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.view.spectral.spectralJob.overview.SpectralJobsOverviewViewModule import SpectralJobsOverviewViewModule
from sciens.spectracs.logic.appliction.style.Metrics import Metrics


# from PySide6.QtCore import pyqtSignal

class HomeViewModule(QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QGridLayout()
        self.setLayout(layout)

        # Connection status of the current user's instrument (SPEC_connection_and_calibration_ux.md §4.4).
        self.connectionStatusLabel = QLabel("")
        self.connectionStatusLabel.setStyleSheet("font-weight: bold; padding: 4px;")
        layout.addWidget(self.connectionStatusLabel, 0, 0, 1, 1)

        self.spectralJobsOverviewViewModule = SpectralJobsOverviewViewModule()
        self.spectralJobsOverviewViewModule.resize(600,600)
        layout.addWidget(self.spectralJobsOverviewViewModule, 1, 0, 1, 1)
        layout.setRowStretch(1,100)

        navigationGroupBox = self.createNavigationGroupBox()
        layout.addWidget(navigationGroupBox, 2, 0, 1, 1)

        # Refresh the indicator whenever the session changes (login / logout / registration auto-login).
        ApplicationContextLogicModule().getApplicationSignalsProvider().userSessionSignal.connect(
            self.updateConnectionStatus)
        self.updateConnectionStatus()

    def updateConnectionStatus(self):
        if CurrentUserSession().isLoggedIn():
            self.connectionStatusLabel.setText(ConnectionStatusLogicModule().getLabel())
            self.connectionStatusLabel.setVisible(True)
        else:
            self.connectionStatusLabel.setVisible(False)

    def showEvent(self, event):
        super().showEvent(event)
        self.updateConnectionStatus()

    def onClickedSettingsButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SettingsViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def onClickedCreateSpectralJobButton(self):
        # Route a plugin-configured user to their measurement wizard; otherwise keep the legacy flow.
        target = "WizardViewModule" if CurrentUserSession().getPluginCodeRef() else "SpectralJob"
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget(target)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def createNavigationGroupBox(self):
        result = QGroupBox("")
        result.setProperty("plain", True)  # borderless holder (spec C2)

        layout = QGridLayout()
        layout.setSpacing(Metrics.S)
        layout.setContentsMargins(0, 0, 0, 0)  # align nav buttons to content edge (spec C7)
        result.setLayout(layout);

        createSpectralJobButton = QPushButton()
        createSpectralJobButton.setText("New measurement")
        layout.addWidget(createSpectralJobButton, 0, 0, 1, 1)
        createSpectralJobButton.clicked.connect(self.onClickedCreateSpectralJobButton)

        # Edit / Delete act on the selected row of the workflows table (right of New measurement).
        editButton = QPushButton("Edit")
        layout.addWidget(editButton, 0, 1, 1, 1)
        editButton.clicked.connect(self.spectralJobsOverviewViewModule.onClickedEdit)

        deleteButton = QPushButton("Delete")
        deleteButton.setProperty("buttonType", "secondary")
        layout.addWidget(deleteButton, 0, 2, 1, 1)
        deleteButton.clicked.connect(self.spectralJobsOverviewViewModule.onClickedDelete)

        settingsButton = QPushButton()
        settingsButton.setText("Settings")
        layout.addWidget(settingsButton, 0, 3, 1, 1)
        settingsButton.clicked.connect(self.onClickedSettingsButton)

        return result



