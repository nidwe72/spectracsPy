from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QGroupBox
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QWidget

from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from logic.spectral.video.SpectrumVideoThread import SpectrumVideoThread
from model.application.navigation.NavigationSignal import NavigationSignal
from view.application.widgets.video.VideoViewModule import VideoViewModule
from model.application.video.VideoSignal import VideoSignal

from model.spectral.SpectralVideoThreadSignal import SpectralVideoThreadSignal

class SpectralJobViewModule(QWidget):

    videoThread:SpectrumVideoThread

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout=QGridLayout()
        self.setLayout(layout)

        self.videoViewModule = VideoViewModule()
        layout.addWidget(self.videoViewModule, 0, 0, 1, 1)

        self.videoThread = SpectrumVideoThread()
        self.videoThread.setFrameCount(30)
        self.videoThread.start()

        sampleButtonsGroupBox=self.createSampleButtonsGroupBox()
        layout.addWidget(sampleButtonsGroupBox, 1, 0, 1, 1)

        lightGroupBox=self.createLightButtonsGroupBox()
        layout.addWidget(lightGroupBox, 2, 0, 1, 1)

        navigationGroupBox=self.createNavigationGroupBox()
        layout.addWidget(navigationGroupBox, 3, 0, 1, 1)

        self.videoThread.spectralVideoThreadSignal.connect(self.handleSpectralVideoThreadSignal)

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

        return lightGroupBox

    def onClickedImportButtonButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SpectralJobImport")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def onClickedBackButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("Home")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def handleSpectralVideoThreadSignal(self, spectralVideoThreadSignal:SpectralVideoThreadSignal):
        if isinstance(spectralVideoThreadSignal, SpectralVideoThreadSignal):
            videoSignal=VideoSignal()
            videoSignal.image=spectralVideoThreadSignal.image
            self.videoViewModule.handleVideoSignal(videoSignal)





