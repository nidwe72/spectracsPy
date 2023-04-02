from PySide6.QtWidgets import QWidget
from PySide6.QtWidgets import QGridLayout
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import QFileDialog

from PySide6.QtCharts import QChart
from PySide6.QtCharts import QLineSeries
from PySide6.QtCore import QPointF
from PySide6.QtCharts import QChartView

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal

from sciens.spectracs.logic.spectral.importSpectrum.ImportSpectrumLogicModuleParameters import ImportSpectrumLogicModuleParameters
from sciens.spectracs.logic.spectral.importSpectrum.ImportSpectrumLogicModule import ImportSpectrumLogicModule


class SpectralJobImportViewModule(QWidget):

    videoThread=None
    videoWidget=None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QGridLayout()
        self.setLayout(layout)

        series = QLineSeries()

        series.append(0, 6)
        series.append(3, 5)
        series.append(3, 8)
        series.append(7, 3)
        series.append(12, 7)

        series << QPointF(11, 1) << QPointF(13, 3) \
        << QPointF(17, 6) << QPointF(18, 3) << QPointF(20, 20)

        chart = QChart()
        chart.addSeries(series)
        # chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.setTitle("Spectrum")
        #chart.setTheme(QChart.ChartThemeBlueCerulean)

        chartView = QChartView(chart)
        #layout.addWidget(chartView, 0, 0, 1, 2)

        importButton = QPushButton()
        importButton.setText("Open file")
        layout.addWidget(importButton, 1, 0, 1, 1)
        importButton.clicked.connect(self.onClickedImportButton)

        backButton = QPushButton()
        backButton.setText("back")
        layout.addWidget(backButton, 1, 1, 1, 1)

        backButton.clicked.connect(self.onClickedBackButton)

    def onClickedBackButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SpectralJob")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def onClickedImportButton(self):
        filepath = self.getFilepathByDialog()
        importSpectrumLogicModuleParameters = ImportSpectrumLogicModuleParameters()
        importSpectrumLogicModuleParameters.setFilepath(filepath)

        importSpectrumLogicModule = ImportSpectrumLogicModule()
        importSpectrumLogicModule.importSpectrum(importSpectrumLogicModuleParameters)

        print(filepath)

    def getFilepathByDialog(self):
        result = None
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.FileMode.AnyFile)
        # dlg.setFilter("Text files (*.txt)")

        if dlg.exec():
            filenames = dlg.selectedFiles()
            result = filenames[0]
        return result







