import threading
from typing import List

from PyQt6.QtCore import QLine
from PyQt6.QtWidgets import QPushButton, QGroupBox, QGridLayout, QWidget, QLineEdit, QStackedWidget

from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from logic.appliction.image.houghLine.HoughLineLogicModule import HoughLineLogicModule
from logic.spectral.video.SpectrometerCalibrationProfileHoughLinesVideoThread import \
    SpectrometerCalibrationProfileHoughLinesVideoThread
from logic.spectral.video.SpectrometerCalibrationProfileWavelengthCalibrationVideoThread import \
    SpectrometerCalibrationProfileWavelengthCalibrationVideoThread
from model.application.applicationStatus.ApplicationStatusSignal import ApplicationStatusSignal
from model.application.navigation.NavigationSignal import NavigationSignal
from model.databaseEntity.spectral.device import SpectrometerCalibrationProfile
from model.signal.SpectrometerCalibrationProfileHoughLinesVideoSignal import \
    SpectrometerCalibrationProfileHoughLinesVideoSignal
from model.signal.SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal import \
    SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal
from view.application.widgets.page.PageWidget import PageWidget
from view.settings.spectral.spectrometer.acquisition.device.calibration.SpectrometerCalibrationProfileHoughLinesVideoViewModule import \
    SpectrometerCalibrationProfileHoughLinesVideoViewModule
from view.settings.spectral.spectrometer.acquisition.device.calibration.SpectrometerCalibrationProfileWavelengthCalibrationVideoViewModule import \
    SpectrometerCalibrationProfileWavelengthCalibrationVideoViewModule


class SpectrometerCalibrationProfileViewModule(PageWidget):

    model: SpectrometerCalibrationProfile = None
    allHoughLines:List[List[QLine]]=None

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

            self.videoViewModulesStackedWidget=QStackedWidget()
            result['videoViewModulesStackedWidget'] = self.videoViewModulesStackedWidget

            self.videoViewModule = SpectrometerCalibrationProfileHoughLinesVideoViewModule()
            self.videoViewModule.setObjectName(
                'SpectrometerCalibrationProfileViewModule.videoViewModule')
            # result[self.videoViewModule.objectName()] = self.videoViewModule

            self.videoViewModulesStackedWidget.addWidget(self.videoViewModule)

            self.wavelengthCalibrationVideoViewModule = SpectrometerCalibrationProfileWavelengthCalibrationVideoViewModule()
            self.videoViewModulesStackedWidget.addWidget(self.wavelengthCalibrationVideoViewModule)

            result['roi'] = self.createRegionOfInterestNavigationGroupBox()

            buttonsPanel=self.createButtonsPanel()
            result[buttonsPanel.objectName()] = buttonsPanel

        return result

    def createButtonsPanel(self):
        buttonsPanel = QWidget()
        buttonsPanel.setObjectName(
            'SpectrometerCalibrationProfileViewModule.buttonsPanel')

        layout = QGridLayout()
        buttonsPanel.setLayout(layout)

        self.captureVideoButton = QPushButton('Detect horizontal lines')
        self.captureVideoButton.clicked.connect(self.onClickedCaptureVideoButton)
        layout.addWidget(self.captureVideoButton, 0, 0, 1, 1)

        self.detectPeaksButton = QPushButton('Detect peaks')
        self.detectPeaksButton.clicked.connect(self.onClickedDetectPeaksButton)
        layout.addWidget(self.detectPeaksButton, 0, 1, 1, 1)

        return buttonsPanel

    def createRegionOfInterestNavigationGroupBox(self):
        result = QGroupBox("Region of interest")

        layout = QGridLayout()
        result.setLayout(layout);

        self.x1Component = QLineEdit()
        layout.addWidget(self.createLabeledComponent('x1', self.x1Component), 0, 0, 1, 1)

        self.x2Component = QLineEdit()
        layout.addWidget(self.createLabeledComponent('x2', self.x2Component), 0, 1, 1, 1)


        self.y1Component = QLineEdit()
        layout.addWidget(self.createLabeledComponent('y1', self.y1Component), 1, 0, 1, 1)

        self.y2Component = QLineEdit()
        layout.addWidget(self.createLabeledComponent('y2', self.y2Component), 1, 1, 1, 1)

        return result

    def onClickedCaptureVideoButton(self):

        self.videoViewModulesStackedWidget.setCurrentIndex(0)

        self.allHoughLines=[]

        self.videoThread = SpectrometerCalibrationProfileHoughLinesVideoThread()
        self.videoThread.videoThreadSignal.connect(self.handleVideoThreadSignal)
        self.videoThread.setFrameCount(50)

        self.videoThread.start()

    def onClickedDetectPeaksButton(self):

        self.videoViewModulesStackedWidget.setCurrentIndex(1)

        self.wavelengthCalibrationVideoThread = SpectrometerCalibrationProfileWavelengthCalibrationVideoThread()
        self.wavelengthCalibrationVideoThread.videoThreadSignal.connect(self.handleWavelengthCalibrationVideoSignal)
        self.wavelengthCalibrationVideoThread.setFrameCount(50)

        self.wavelengthCalibrationVideoThread.start()

    def handleWavelengthCalibrationVideoSignal(self, event: threading.Event,
                                videoSignal: SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal):

        applicationStatusSignal = ApplicationStatusSignal()
        applicationStatusSignal.text = 'detecting peaks'
        applicationStatusSignal.isStatusReset = False
        applicationStatusSignal.stepsCount = videoSignal.framesCount
        applicationStatusSignal.currentStepIndex = videoSignal.currentFrameIndex

        if applicationStatusSignal.stepsCount == applicationStatusSignal.currentStepIndex:
            applicationStatusSignal.isStatusReset = True

        ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(
            applicationStatusSignal)

        self.wavelengthCalibrationVideoViewModule.handleVideoThreadSignal(videoSignal)

        event.set()

    def handleVideoThreadSignal(self, event:threading.Event, videoSignal: SpectrometerCalibrationProfileHoughLinesVideoSignal):
        if isinstance(videoSignal, SpectrometerCalibrationProfileHoughLinesVideoSignal):

            # if videoSignal.currentFrameIndex==videoSignal.framesCount:
            #     pass

            houghLineLogicModule = HoughLineLogicModule()
            houghLines = houghLineLogicModule.getHoughLines(videoSignal.image)
            self.allHoughLines.append(houghLines)

            videoSignal.calibrationStepUpperHoughLine=houghLines[0]
            videoSignal.calibrationStepLowerHoughLine = houghLines[1]

            centerY = videoSignal.calibrationStepUpperHoughLine.p1().y() + (
                        videoSignal.calibrationStepLowerHoughLine.p1().y() - videoSignal.calibrationStepUpperHoughLine.p1().y()) / 2.0

            videoSignal.calibrationStepCenterHoughLine = QLine(videoSignal.calibrationStepUpperHoughLine.p1().x(), centerY,
                                                videoSignal.calibrationStepUpperHoughLine.p2().x(), centerY)

            boundingHoughLines = self.__getBoundingHoughLines()

            videoSignal.upperHoughLine=boundingHoughLines[0]
            videoSignal.lowerHoughLine = boundingHoughLines[1]

            centerY = videoSignal.upperHoughLine.p1().y() + (
                        videoSignal.lowerHoughLine.p1().y() - videoSignal.upperHoughLine.p1().y()) / 2.0

            videoSignal.centerHoughLine = QLine(videoSignal.upperHoughLine.p1().x(), centerY,
                                                videoSignal.upperHoughLine.p2().x(), centerY)

            someNavigationSignal = NavigationSignal(None)
            someNavigationSignal.setTarget("SpectrometerCalibrationProfileViewModule")

            applicationStatusSignal = ApplicationStatusSignal()
            applicationStatusSignal.text='retrieving Hough lines'
            applicationStatusSignal.isStatusReset = False
            applicationStatusSignal.stepsCount=videoSignal.framesCount
            applicationStatusSignal.currentStepIndex=videoSignal.currentFrameIndex

            if applicationStatusSignal.stepsCount==applicationStatusSignal.currentStepIndex:
                self.y2Component.setText(str(videoSignal.upperHoughLine.p1().y()))
                self.y1Component.setText(str(videoSignal.lowerHoughLine.p1().y()))
                applicationStatusSignal.isStatusReset=True

            ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(applicationStatusSignal)

            self.videoViewModule.handleVideoThreadSignal(videoSignal)

            event.set()

    def __getBoundingHoughLines(self)->List[QLine]:

        result = []

        resultUpperHoughLine:QLine=None
        resultLowerHoughLine:QLine = None

        for someHoughLines in self.allHoughLines:
            upperHoughLine=someHoughLines[0]
            lowerHoughLine = someHoughLines[1]

            if resultUpperHoughLine is None:
                resultUpperHoughLine=upperHoughLine
            elif upperHoughLine.p1().y()>resultUpperHoughLine.p1().y():
                resultUpperHoughLine = upperHoughLine

            if resultLowerHoughLine is None:
                resultLowerHoughLine=lowerHoughLine
            elif lowerHoughLine.p1().y()<resultLowerHoughLine.p1().y():
                resultLowerHoughLine=lowerHoughLine

        result.append(resultUpperHoughLine)
        result.append(resultLowerHoughLine)
        return result

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





