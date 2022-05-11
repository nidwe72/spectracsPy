import sys
from PyQt6.QtWidgets import QWidget
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtWidgets import QGraphicsScene
from PyQt6.QtWidgets import QGraphicsView
from PyQt6.QtWidgets import QGraphicsPixmapItem
from PyQt6.QtGui import QImage
from PyQt6.QtGui import QPixmap

from PyQt6.QtCharts import QChart
from PyQt6.QtCharts import QLineSeries
from PyQt6.QtCore import QPointF
from PyQt6.QtCharts import QChartView

from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from model.application.navigation.NavigationSignal import NavigationSignal

from logic.spectral.importSpectrum.ImportSpectrumLogicModuleParameters import ImportSpectrumLogicModuleParameters
from logic.spectral.importSpectrum.ImportSpectrumLogicModule import ImportSpectrumLogicModule

from view.widgets.video.VideoThread import VideoThread
from view.widgets.video.VideoSignal import VideoSignal

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

        self.videoWidget=QGraphicsView()
        layout.addWidget(self.videoWidget, 0, 0, 1, 2)

        someImage=QImage("/home/nidwe/testPhilips.png");
        scene = QGraphicsScene();

        # imageItem=QGraphicsPixmapItem(QPixmap.fromImage(someImage))
        imageItem = QGraphicsPixmapItem()
        scene.addItem(imageItem)

        self.videoWidget.setScene(scene)

        self.videoThread=VideoThread()
        self.videoThread.start()
        self.videoThread.videoSignal.connect(self.handleVideoSignal)

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

    def handleVideoSignal(self,videoSignal:VideoSignal):
        image = videoSignal.image
        print("gotta image with")
        # pixmap = QPixmap()
        # self.videoWidget.setPixmap(QPixmap.fromImage(image))
        scene=self.videoWidget.scene()

        someImage = QImage("/home/nidwe/testPhilips.png");
        somePixmap = QPixmap.fromImage(someImage)

        somePixmap2 = QPixmap.fromImage(image)

        item=scene.items()[0]
        item.setPixmap(somePixmap2)

        #scene.addItem(QGraphicsPixmapItem(somePixmap))
        #scene.addText("hmmm")







