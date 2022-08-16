import threading

from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QPushButton, QGroupBox, QGridLayout, QWidget

from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from logic.appliction.image.houghLine.HoughLineLogicModule import HoughLineLogicModule
from logic.spectral.video.SpectrumVideoThread import SpectrumVideoThread
from model.application.navigation.NavigationSignal import NavigationSignal
from model.application.video.VideoSignal import VideoSignal
from model.databaseEntity.spectral.device import SpectrometerCalibrationProfile
from model.spectral.SpectralVideoThreadSignal import SpectralVideoThreadSignal
from model.spectral.SpectrumSampleType import SpectrumSampleType
from view.application.widgets.page.PageWidget import PageWidget
from view.application.widgets.video.VideoViewModule import VideoViewModule


class SpectrometerCalibrationProfileViewModule(PageWidget):

    model: SpectrometerCalibrationProfile = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def initialize(self):
        super().initialize()

    def _getPageTitle(self):
        if not self._isTopMostPageWidget():
            return "Calibration Profile"
        else:
            return "Settings > Spectrometer profiles > Spectrometer profile > Calibration Profile"

    def getMainContainerWidgets(self):
        result= super().getMainContainerWidgets()

        if not self._isTopMostPageWidget():

            editCalibrationProfileButton=QPushButton('Edit')
            editCalibrationProfileButton.setObjectName('SpectrometerCalibrationProfileViewModule.editCalibrationProfileButton')
            result[editCalibrationProfileButton.objectName()]=editCalibrationProfileButton
            editCalibrationProfileButton.clicked.connect(self.onClickedEditButton)

        else:

            self.videoViewModule = VideoViewModule()
            self.videoViewModule.setObjectName(
                'SpectrometerCalibrationProfileViewModule.videoViewModule')
            result[self.videoViewModule.objectName()] = self.videoViewModule

            buttonsPanel=QWidget()
            buttonsPanel.setObjectName(
                'SpectrometerCalibrationProfileViewModule.buttonsPanel')
            result[buttonsPanel.objectName()] = buttonsPanel


            layout=QGridLayout()
            buttonsPanel.setLayout(layout)

            self.captureVideoButton=QPushButton('Detect vertical bounds')
            self.captureVideoButton.clicked.connect(self.onClickedCaptureVideoButton)

            layout.addWidget(self.captureVideoButton,0,0,1,1)


        return result

    def onClickedCaptureVideoButton(self):

        self.videoThread = SpectrumVideoThread()
        self.videoThread.spectralVideoThreadSignal.connect(self.handleSpectralVideoThreadSignal)
        self.videoThread.setFrameCount(50)

        self.videoThread.setSpectrumSampleType(SpectrumSampleType.UNSPECIFIED)

        self.videoThread.start()

    def handleSpectralVideoThreadSignal(self, event:threading.Event,spectralVideoThreadSignal: SpectralVideoThreadSignal):
        if isinstance(spectralVideoThreadSignal, SpectralVideoThreadSignal):

            # self.spectralJobGraphViewModule.updateGraph(spectralVideoThreadSignal.spectralJob)
            # self.plotSpectraMeanViewModule.updateGraph(spectralVideoThreadSignal.spectralJob)

            videoSignal = VideoSignal()
            if spectralVideoThreadSignal.currentFrameIndex==spectralVideoThreadSignal.framesCount:
                pass
                # colorizedImage=spectralImageLogicModule.colorizeQImage(spectralVideoThreadSignal.image,132)
                # videoSignal.image = colorizedImage

            print('handleSpectralVideoThreadSignal')

            # colorizedImage=spectralVideoThreadSignal.image.convertToFormat(QImage.Format.Format_Grayscale8)
            # videoSignal.image = colorizedImage

            #colorizedImage=spectralVideoThreadSignal.image.convertToFormat(QImage.Format.Format_Grayscale8)
            videoSignal.image = spectralVideoThreadSignal.image

            houghLineLogicModule = HoughLineLogicModule()
            lines = houghLineLogicModule.getHoughLines(videoSignal.image)

            # spectralImageLogicModule=SpectralImageLogicModule()
            # someImage=QImage()
            # #someImage.load("/home/nidwe/testPhilipsBlured3.png")
            # someImage.load("/home/nidwe/testPhilipsSharpened2.png")
            # #someImage.load("/home/nidwe/testPhilips.png")
            # foo=spectralImageLogicModule.convertQImageToNumpyArray(someImage)
            # bar=spectralImageLogicModule.calculateFocalMeasureOfNumpyImage(foo)
            # print("bar")
            # print(bar)
            # videoSignal.image=someImage

            self.videoViewModule.handleVideoSignal(videoSignal)


            event.set()


    def onClickedEditButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SpectrometerCalibrationProfileViewModule")

        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def createNavigationGroupBox(self):
        result = QGroupBox("")

        layout = QGridLayout()
        result.setLayout(layout);

        backButton = QPushButton()
        backButton.setText("Back")
        layout.addWidget(backButton, 0, 0, 1, 1)
        backButton.clicked.connect(self.onClickedBackButton)

        saveButton = QPushButton()
        saveButton.setText("Save")
        layout.addWidget(saveButton, 0, 1, 1, 1)
        saveButton.clicked.connect(self.onClickedSaveButton)

        return result

    def onClickedSaveButton(self):
        pass

    def onClickedBackButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SpectrometerProfileViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)





