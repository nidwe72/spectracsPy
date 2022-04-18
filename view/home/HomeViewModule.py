from PyQt6.QtWidgets import QWidget
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QPushButton

from PyQt6.QtCore import pyqtSignal

from view.spectral.spectralJob.overview.SpectralJobsOverviewViewModule import SpectralJobsOverviewViewModule
from model.application.navigation.NavigationSignal import NavigationSignal

from controller.application.ApplicationSignalsProviderLogicModule import ApplicationSignalsProviderLogicModule

from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule

from controller.application.navigationHandler.NavigationHandlerLogicModule import NavigationHandlerLogicModule

class HomeViewModule(QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QGridLayout()
        self.setLayout(layout)

        spectralJobsOverviewViewModule = SpectralJobsOverviewViewModule()
        layout.addWidget(spectralJobsOverviewViewModule, 0, 0, 1, 1)

        createSpectralJobButton = QPushButton()
        createSpectralJobButton.setText("New measurement")
        layout.addWidget(createSpectralJobButton, 1, 0, 1, 1)
        createSpectralJobButton.clicked.connect(self.onClickedCreateSpectralJobButton)

        settingsButton = QPushButton()
        settingsButton.setText("Settings")
        layout.addWidget(settingsButton, 1, 1, 1, 1)

        settingsButton.clicked.connect(self.onClickedSettingsButton)

    def onClickedSettingsButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("Settings")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def onClickedCreateSpectralJobButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SpectralJob")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)


