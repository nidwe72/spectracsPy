import threading
from typing import List

from PySide6.QtCore import QLine
from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QGroupBox, QLineEdit

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.spectral.acquisition.device.calibration.SpectrometerRegionOfInterestLogicModule import \
    SpectrometerRegionOfInterestLogicModule
from sciens.spectracs.logic.spectral.video.SpectrometerCalibrationProfileHoughLinesVideoThread import \
    SpectrometerCalibrationProfileHoughLinesVideoThread
from sciens.spectracs.model.application.applicationStatus.ApplicationStatusSignal import ApplicationStatusSignal
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.model.databaseEntity.spectral.device.calibration.SpectrometerCalibrationProfile import \
    SpectrometerCalibrationProfile

from sciens.spectracs.model.signal.SpectrometerCalibrationProfileHoughLinesVideoSignal import \
    SpectrometerCalibrationProfileHoughLinesVideoSignal
from view.application.widgets.page.PageWidget import PageWidget
from view.settings.spectral.spectrometer.acquisition.device.calibration.SpectrometerCalibrationProfileHoughLinesVideoViewModule import \
    SpectrometerCalibrationProfileHoughLinesVideoViewModule

class SpectrometerCalibrationProfileHoughLinesViewModule(PageWidget):

    __model:SpectrometerCalibrationProfile=None

    videoThread: SpectrometerCalibrationProfileHoughLinesVideoThread = None
    videoViewModule: SpectrometerCalibrationProfileHoughLinesVideoViewModule = None
    captureVideoButton: QPushButton = None
    allHoughLines: List[List[QLine]] = None

    x1Component: QLineEdit = None
    y1Component: QLineEdit = None
    x2Component: QLineEdit = None
    y2Component: QLineEdit = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        self.videoViewModule = SpectrometerCalibrationProfileHoughLinesVideoViewModule()
        self.videoViewModule.setObjectName(
            'SpectrometerCalibrationProfileHoughLinesViewModule.videoViewModule')
        result[self.videoViewModule.objectName()] = self.videoViewModule

        mainWidget = self.createMainWidget()
        result['mainWidget'] = mainWidget

        buttonsPanel = self.createButtonsPanel()
        result[buttonsPanel.objectName()] = buttonsPanel

        return result

    def createButtonsPanel(self):
        buttonsPanel = QWidget()
        buttonsPanel.setObjectName(
            'SpectrometerCalibrationProfileViewModule.buttonsPanel')

        layout = QGridLayout()
        buttonsPanel.setLayout(layout)

        self.captureVideoButton = QPushButton('Detect Region of Interest')
        # noinspection PyUnresolvedReferences
        self.captureVideoButton.clicked.connect(self.onClickedCaptureVideoButton)
        layout.addWidget(self.captureVideoButton, 0, 0, 1, 1)

        return buttonsPanel

    def onClickedCaptureVideoButton(self):

        self.allHoughLines = []
        self.videoThread = SpectrometerCalibrationProfileHoughLinesVideoThread()
        spectrometerProfile = ApplicationContextLogicModule().getApplicationSettings().getSpectrometerProfile()
        isVirtual = spectrometerProfile.spectrometer.spectrometerSensor.isVirtual
        self.videoThread.setIsVirtual(isVirtual)
        self.videoThread.videoThreadSignal.connect(self.handleVideoThreadSignal)
        self.videoThread.setFrameCount(50)
        self.videoThread.start()

    def createRegionOfInterestNavigationGroupBox(self):
        result = QGroupBox("Region of interest")

        layout = QGridLayout()
        result.setLayout(layout)

        self.x1Component = QLineEdit()
        layout.addWidget(self.createLabeledComponent('x1', self.x1Component), 0, 0, 1, 1)

        self.x2Component = QLineEdit()
        layout.addWidget(self.createLabeledComponent('x2', self.x2Component), 0, 1, 1, 1)

        self.y1Component = QLineEdit()
        layout.addWidget(self.createLabeledComponent('y1', self.y1Component), 1, 0, 1, 1)

        self.y2Component = QLineEdit()
        layout.addWidget(self.createLabeledComponent('y2', self.y2Component), 1, 1, 1, 1)

        return result

    def handleVideoThreadSignal(self, event: threading.Event,
                                videoSignal: SpectrometerCalibrationProfileHoughLinesVideoSignal):
        if isinstance(videoSignal, SpectrometerCalibrationProfileHoughLinesVideoSignal):

            houghLines=SpectrometerRegionOfInterestLogicModule().getHorizontalBoundingLines(videoSignal)
            self.allHoughLines.append(houghLines)

            videoSignal.calibrationStepUpperHoughLine = houghLines[0]
            videoSignal.calibrationStepLowerHoughLine = houghLines[1]

            centerY = videoSignal.calibrationStepUpperHoughLine.p1().y() + (
                    videoSignal.calibrationStepLowerHoughLine.p1().y() - videoSignal.calibrationStepUpperHoughLine.p1().y()) / 2.0

            videoSignal.calibrationStepCenterHoughLine = QLine(videoSignal.calibrationStepUpperHoughLine.p1().x(),
                                                               centerY,
                                                               videoSignal.calibrationStepUpperHoughLine.p2().x(),
                                                               centerY)

            boundingHoughLines = self.__getBoundingHoughLines()
            videoSignal.upperHoughLine = boundingHoughLines[0]
            videoSignal.lowerHoughLine = boundingHoughLines[1]

            centerY = videoSignal.upperHoughLine.p1().y() + (
                    videoSignal.lowerHoughLine.p1().y() - videoSignal.upperHoughLine.p1().y()) / 2.0

            videoSignal.centerHoughLine = QLine(videoSignal.upperHoughLine.p1().x(), centerY,
                                                videoSignal.upperHoughLine.p2().x(), centerY)

            someNavigationSignal = NavigationSignal(None)
            someNavigationSignal.setTarget("SpectrometerCalibrationProfileViewModule")

            applicationStatusSignal = ApplicationStatusSignal()
            applicationStatusSignal.isStatusReset = False
            applicationStatusSignal.stepsCount = videoSignal.framesCount
            applicationStatusSignal.currentStepIndex = videoSignal.currentFrameIndex
            applicationStatusSignal.text = f"retrieving Hough lines > step [{applicationStatusSignal.currentStepIndex+1}/{applicationStatusSignal.stepsCount}]"

            # print(f"videoSignal.currentFrameIndex:{videoSignal.currentFrameIndex}");
            # print(f"applicationStatusSignal.stepsCount:{applicationStatusSignal.stepsCount}");
            # print(f"applicationStatusSignal.currentStepIndex:{applicationStatusSignal.currentStepIndex}");

            if applicationStatusSignal.stepsCount-1 == applicationStatusSignal.currentStepIndex:
                self.y2Component.setText(str(videoSignal.upperHoughLine.p1().y()))
                self.y1Component.setText(str(videoSignal.lowerHoughLine.p1().y()))

                self.__getModel().regionOfInterestY1=videoSignal.lowerHoughLine.p1().y()
                self.__getModel().regionOfInterestY2 = videoSignal.upperHoughLine.p1().y()

                SpectrometerRegionOfInterestLogicModule().getVerticalBoundingLines(videoSignal)

                self.__getModel().regionOfInterestX1 = videoSignal.leftBoundingLine.p1().x()
                self.__getModel().regionOfInterestX2 = videoSignal.rightBoundingLine.p1().x()

                applicationStatusSignal.isStatusReset = True

            ApplicationContextLogicModule().getApplicationSignalsProvider().emitApplicationStatusSignal(
                applicationStatusSignal)

            self.videoViewModule.handleVideoThreadSignal(videoSignal)


            self.setModel(self.__getModel())

            event.set()

    def __getBoundingHoughLines(self) -> List[QLine]:

        result = []

        # noinspection PyTypeChecker
        resultUpperHoughLine: QLine=None
        # noinspection PyTypeChecker
        resultLowerHoughLine: QLine=None

        for someHoughLines in self.allHoughLines:
            upperHoughLine = someHoughLines[0]
            lowerHoughLine = someHoughLines[1]

            if resultUpperHoughLine is None:
                resultUpperHoughLine = upperHoughLine
            elif upperHoughLine.p1().y() > resultUpperHoughLine.p1().y():
                resultUpperHoughLine = upperHoughLine

            if resultLowerHoughLine is None:
                resultLowerHoughLine = lowerHoughLine
            elif lowerHoughLine.p1().y() < resultLowerHoughLine.p1().y():
                resultLowerHoughLine = lowerHoughLine

        if resultUpperHoughLine is not None:
            result.append(resultUpperHoughLine)
        if resultLowerHoughLine is not None:
            result.append(resultLowerHoughLine)

        return result

    def createMainWidget(self):

        result = QWidget()
        resultLayout = QGridLayout()
        result.setLayout(resultLayout)
        resultLayout.addWidget(self.createRegionOfInterestNavigationGroupBox(), 0, 0, 1, 1)

        return result

    def initialize(self):
        super().initialize()

    def setModel(self,model:SpectrometerCalibrationProfile):
        self.__model=model

        if self.y1Component is None:
            self.y1Component = QLineEdit()
        if model.regionOfInterestY1 is None:
            self.y1Component.setText('')
        else:
            self.y1Component.setText(str(model.regionOfInterestY1))

        if self.y2Component is None:
            self.y2Component = QLineEdit()
        if model.regionOfInterestY2 is None:
            self.y2Component.setText('')
        else:
            self.y2Component.setText(str(model.regionOfInterestY2))

        if self.x1Component is None:
            self.x1Component = QLineEdit()
        if model.regionOfInterestX1 is None:
            self.x1Component.setText('')
        else:
            self.x1Component.setText(str(model.regionOfInterestX1))

        if self.x2Component is None:
            self.x2Component = QLineEdit()
        if model.regionOfInterestX2 is None:
            self.x2Component.setText('')
        else:
            self.x2Component.setText(str(model.regionOfInterestX2))

    def __getModel(self):
        return self.__model



