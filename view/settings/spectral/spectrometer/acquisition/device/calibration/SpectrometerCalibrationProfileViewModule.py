from PyQt6.QtCharts import QLineSeries, QChart, QChartView
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QPen
from PyQt6.QtWidgets import QPushButton, QGroupBox, QGridLayout, QTabWidget, QTextEdit

from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from logic.model.util.SpectrometerCalibrationProfileUtil import SpectrometerCalibrationProfileUtil
from logic.persistence.database.spectrometerCalibrationProfile.PersistSpectrometerCalibrationProfileLogicModule import \
    PersistSpectrometerCalibrationProfileLogicModule
from model.application.navigation.NavigationSignal import NavigationSignal
from model.databaseEntity.spectral.device import SpectrometerCalibrationProfile
from view.application.widgets.page.PageWidget import PageWidget
from view.settings.spectral.spectrometer.acquisition.device.calibration.SpectrometerCalibrationProfileHoughLinesViewModule import \
    SpectrometerCalibrationProfileHoughLinesViewModule
from view.settings.spectral.spectrometer.acquisition.device.calibration.SpectrometerCalibrationProfileWavelengthCalibrationViewModule import \
    SpectrometerCalibrationProfileWavelengthCalibrationViewModule


class SpectrometerCalibrationProfileViewModule(PageWidget):

    __model: SpectrometerCalibrationProfile = None

    tabWidget:QTabWidget=None
    houghLinesViewModule:SpectrometerCalibrationProfileHoughLinesViewModule=None
    wavelengthCalibrationViewModule:SpectrometerCalibrationProfileWavelengthCalibrationViewModule=None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verticalLayout=False

    def _getPageTitle(self):
        if not self._isTopMostPageWidget():
            return "Calibration Profile (pixel/nanometer)"
        else:
            return "Settings > Spectrometer profiles > Spectrometer profile > Calibration Profile"

    def getMainContainerWidgets(self):
        result= super().getMainContainerWidgets()

        if not self._isTopMostPageWidget():

            edit = QTextEdit()
            edit.setText('foo')
            # item = graphicsScene.addWidget(edit)
            # graphicsLayout.addItem(item,0,0,1,1, Qt.AlignmentFlag.AlignVCenter)

            series = QLineSeries()

            series.append(0, 6)
            series.append(3, 5)
            series.append(3, 8)
            series.append(7, 3)
            series.append(12, 7)



            chart = QChart()
            chart.addSeries(series)
            # chart.setTitle("Spectrum")
            chart.legend().hide()


            pen = series.pen();
            pen.setWidth(2);
            pen.setBrush(QBrush(QColor("#33663d")))
            series.setPen(pen)



            chart.createDefaultAxes();

            q_pen = QPen(QBrush(QColor(50, 50, 50, 50)), 1)
            chart.axes(Qt.Orientation.Horizontal)[0].setGridLinePen(q_pen);
            chart.axes(Qt.Orientation.Vertical)[0].setGridLinePen(q_pen);

            chartView = QChartView(chart)
            chartView.setContentsMargins(-20,0,0,0)
            chart.setContentsMargins(-20,-10,-10,-10)


            chart.setBackgroundBrush(QBrush(QColor("transparent")))
            chart.setTitleBrush(QBrush(QColor("white")));

            result['chartView'] = chartView

            editCalibrationProfileButton=QPushButton('Edit')
            editCalibrationProfileButton.setMinimumWidth(100)
            editCalibrationProfileButton.setObjectName('SpectrometerCalibrationProfileViewModule.editCalibrationProfileButton')
            result[editCalibrationProfileButton.objectName()]=editCalibrationProfileButton
            editCalibrationProfileButton.clicked.connect(self.onClickedEditButton)


        else:

            self.tabWidget = QTabWidget()

            if self.houghLinesViewModule is None:
                self.houghLinesViewModule=SpectrometerCalibrationProfileHoughLinesViewModule(self)
            # self.houghLinesViewModule.setStylesheetOnlySelf("border:1px solid #00000000;")
            self.houghLinesViewModule.initialize()
            self.tabWidget.addTab(self.houghLinesViewModule,'Region of interest')

            if self.wavelengthCalibrationViewModule is None:
                self.wavelengthCalibrationViewModule=SpectrometerCalibrationProfileWavelengthCalibrationViewModule(self)
            self.wavelengthCalibrationViewModule.setModel(self.__getModel())
            # self.wavelengthCalibrationViewModule.setStylesheetOnlySelf("border:1px solid #00000000;")
            self.wavelengthCalibrationViewModule.initialize()
            self.tabWidget.addTab(self.wavelengthCalibrationViewModule, 'Wavelength calibration')

            result['tabWidget']=self.tabWidget

        return result

    def onClickedEditButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SpectrometerCalibrationProfileViewModule")

        spectrometerCalibrationProfileViewModule = ApplicationContextLogicModule().getNavigationHandler().getViewModule(someNavigationSignal)
        spectrometerCalibrationProfileViewModule.setModel(self.__getModel())
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
        model = self.__getModel()
        PersistSpectrometerCalibrationProfileLogicModule().saveSpectrometerCalibrationProfile(model)

    def onClickedBackButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SpectrometerProfileViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def setModel(self,model: SpectrometerCalibrationProfile):
        self.__model=model

        SpectrometerCalibrationProfileUtil().initializeSpectrometerCalibrationProfile(model)

        if self.wavelengthCalibrationViewModule is None:
            self.wavelengthCalibrationViewModule = SpectrometerCalibrationProfileWavelengthCalibrationViewModule(self)
        self.wavelengthCalibrationViewModule.setModel(model)

        if self.houghLinesViewModule is None:
            self.houghLinesViewModule = SpectrometerCalibrationProfileHoughLinesViewModule(self)
        self.houghLinesViewModule.setModel(model)

    def __getModel(self)->SpectrometerCalibrationProfile:
        return self.__model

