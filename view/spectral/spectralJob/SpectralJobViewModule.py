from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QGroupBox
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QWidget

from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from logic.spectral.video.SpectrumVideoThread import SpectrumVideoThread
from model.application.navigation.NavigationSignal import NavigationSignal
from model.spectral.SpectrumSampleType import SpectrumSampleType
from view.spectral.spectralJob.widget.SpectralJobWidgetViewModule import SpectralJobWidgetViewModule
from view.spectral.spectralJob.widget.SpectralJobWidgetViewModuleParameters import SpectralJobWidgetViewModuleParameters
from view.spectral.spectralJob.widget.SpectralJobsWidgetViewModule import SpectralJobsWidgetViewModule


class SpectralJobViewModule(QWidget):
    videoThread: SpectrumVideoThread

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QGridLayout()
        self.setLayout(layout)

        self.spectralJobsWidgetViewModule = SpectralJobsWidgetViewModule(self)
        layout.addWidget(self.spectralJobsWidgetViewModule, 0, 0, 1, 1)

        sampleButtonsGroupBox = self.createSampleButtonsGroupBox()
        layout.addWidget(sampleButtonsGroupBox, 1, 0, 1, 1)

        lightGroupBox = self.createLightButtonsGroupBox()
        layout.addWidget(lightGroupBox, 2, 0, 1, 1)

        navigationGroupBox = self.createNavigationGroupBox()
        layout.addWidget(navigationGroupBox, 3, 0, 1, 1)



    def createSampleButtonsGroupBox(self):
        lightGroupBox = QGroupBox("Oil")

        lightGroupBoxLayout = QGridLayout()
        lightGroupBox.setLayout(lightGroupBoxLayout);

        measureLightButton = QPushButton()
        measureLightButton.setText("Measure")
        lightGroupBoxLayout.addWidget(measureLightButton, 0, 0, 1, 1)

        importLightButton = QPushButton()
        importLightButton.setText("Import")
        lightGroupBoxLayout.addWidget(importLightButton, 0, 1, 1, 1)

        return lightGroupBox

    def createNavigationGroupBox(self):
        result = QGroupBox("")

        layout = QGridLayout()
        result.setLayout(layout);

        measureLightButton = QPushButton()
        measureLightButton.setText("Save")
        layout.addWidget(measureLightButton, 0, 0, 1, 1)

        importLightButton = QPushButton()
        importLightButton.setText("Back")
        layout.addWidget(importLightButton, 0, 1, 1, 1)
        importLightButton.clicked.connect(self.onClickedBackButton)

        return result

    def createLightButtonsGroupBox(self):
        lightGroupBox = QGroupBox("Light")

        lightGroupBoxLayout = QGridLayout()
        lightGroupBox.setLayout(lightGroupBoxLayout);

        measureLightButton = QPushButton()
        measureLightButton.setText("Measure")
        lightGroupBoxLayout.addWidget(measureLightButton, 0, 0, 1, 1)

        usePreviousLightMeasurementButton = QPushButton()
        usePreviousLightMeasurementButton.setText("Previous measurement")
        lightGroupBoxLayout.addWidget(usePreviousLightMeasurementButton, 0, 1, 1, 1)

        importLightButton = QPushButton()
        importLightButton.setText("Import")
        lightGroupBoxLayout.addWidget(importLightButton, 0, 2, 1, 1)

        measureLightButton.clicked.connect(self.onClickedMeasureLightButton)

        return lightGroupBox

    def onClickedMeasureLightButton(self):
        self.spectralJobsWidgetViewModule.referenceWidget.startVideoThread()

    def onClickedImportButtonButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SpectralJobImport")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def onClickedBackButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("Home")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

