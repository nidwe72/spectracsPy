import threading

from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QPushButton, QGroupBox, QGridLayout, QWidget

from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from logic.appliction.image.houghLine.HoughLineLogicModule import HoughLineLogicModule
from logic.spectral.video.SpectrometerCalibrationProfileHoughLinesVideoThread import \
    SpectrometerCalibrationProfileHoughLinesVideoThread
from logic.spectral.video.SpectrumVideoThread import SpectrumVideoThread
from model.application.applicationStatus.ApplicationStatusSignal import ApplicationStatusSignal
from model.application.navigation.NavigationSignal import NavigationSignal
from model.application.video.VideoSignal import VideoSignal
from model.databaseEntity.spectral.device import SpectrometerCalibrationProfile
from model.signal.SpectrometerCalibrationProfileHoughLinesVideoSignal import \
    SpectrometerCalibrationProfileHoughLinesVideoSignal
from model.spectral.SpectralVideoThreadSignal import SpectralVideoThreadSignal
from model.spectral.SpectrumSampleType import SpectrumSampleType
from view.application.widgets.page.PageWidget import PageWidget
from view.application.widgets.video.VideoViewModule import VideoViewModule
from view.settings.spectral.spectrometer.acquisition.device.calibration.SpectrometerCalibrationProfileHoughLinesVideoViewModule import \
    SpectrometerCalibrationProfileHoughLinesVideoViewModule


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

            #self.videoViewModule = VideoViewModule()
            self.videoViewModule = SpectrometerCalibrationProfileHoughLinesVideoViewModule()
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

        self.allHoughLines=[]

        self.videoThread = SpectrometerCalibrationProfileHoughLinesVideoThread()
        self.videoThread.videoThreadSignal.connect(self.handleSpectralVideoThreadSignal)
        self.videoThread.setFrameCount(50)

        self.videoThread.start()

    def handleSpectralVideoThreadSignal(self, event:threading.Event, videoThreadSignal: SpectrometerCalibrationProfileHoughLinesVideoSignal):
        if isinstance(videoThreadSignal, SpectrometerCalibrationProfileHoughLinesVideoSignal):

            if videoThreadSignal.currentFrameIndex==videoThreadSignal.framesCount:
                pass


            houghLineLogicModule = HoughLineLogicModule()
            houghLines = houghLineLogicModule.getHoughLines(videoThreadSignal.image)

            videoThreadSignal.upperHoughLine=houghLines[0]
            videoThreadSignal.lowerHoughLine = houghLines[1]

            self.allHoughLines.append(houghLines)

            someNavigationSignal = NavigationSignal(None)
            someNavigationSignal.setTarget("SpectrometerCalibrationProfileViewModule")

            applicationStatusSignal = ApplicationStatusSignal()
            applicationStatusSignal.text='retrieving hough lines'
            applicationStatusSignal.isStatusReset = False
            applicationStatusSignal.stepsCount=videoThreadSignal.framesCount
            applicationStatusSignal.currentStepIndex=videoThreadSignal.currentFrameIndex

            if applicationStatusSignal.stepsCount==applicationStatusSignal.currentStepIndex:
                applicationStatusSignal.isStatusReset=True

            ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(applicationStatusSignal)

            self.videoViewModule.handleVideoSignal(videoThreadSignal)

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





