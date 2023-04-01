from PySide6.QtWidgets import QGridLayout
from PySide6.QtWidgets import QGroupBox
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import QWidget

from chromos.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from chromos.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from view.spectral.spectralJob.overview.SpectralJobsOverviewViewModule import SpectralJobsOverviewViewModule


# from PySide6.QtCore import pyqtSignal

class HomeViewModule(QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QGridLayout()
        self.setLayout(layout)

        spectralJobsOverviewViewModule = SpectralJobsOverviewViewModule()
        spectralJobsOverviewViewModule.resize(600,600)
        layout.addWidget(spectralJobsOverviewViewModule, 0, 0, 1, 1)
        layout.setRowStretch(0,100)

        navigationGroupBox = self.createNavigationGroupBox()
        layout.addWidget(navigationGroupBox, 1, 0, 1, 1)

    def onClickedSettingsButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SettingsViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def onClickedCreateSpectralJobButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SpectralJob")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def createNavigationGroupBox(self):
        result = QGroupBox("")

        layout = QGridLayout()
        result.setLayout(layout);

        createSpectralJobButton = QPushButton()
        createSpectralJobButton.setText("New measurement")
        layout.addWidget(createSpectralJobButton, 0, 0, 1, 1)
        createSpectralJobButton.clicked.connect(self.onClickedCreateSpectralJobButton)

        settingsButton = QPushButton()
        settingsButton.setText("Settings")
        layout.addWidget(settingsButton, 0, 1, 1, 1)
        settingsButton.clicked.connect(self.onClickedSettingsButton)

        return result



