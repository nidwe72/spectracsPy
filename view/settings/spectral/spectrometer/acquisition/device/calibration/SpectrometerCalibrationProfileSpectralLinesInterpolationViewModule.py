from PyQt6.QtCharts import QLineSeries, QChart, QChartView, QScatterSeries
from PyQt6.QtCore import Qt, QMargins
from PyQt6.QtGui import QBrush, QColor, QPen

from logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from logic.spectral.util.SpectrallineUtil import SpectralLineUtil
from model.databaseEntity.spectral.device import SpectrometerCalibrationProfile
from view.application.widgets.page.PageWidget import PageWidget


class SpectrometerCalibrationProfileSpectralLinesInterpolationViewModule(PageWidget):

    __model: SpectrometerCalibrationProfile = None
    __scatterSeries:QScatterSeries=None

    def getMainContainerWidgets(self):
        result= super().getMainContainerWidgets()

        chart = QChart()
        chart.addSeries(self.__getScatterSeries())
        chart.legend().hide()

        # chart.setMargins(QMargins(10,10,10,10))
        chartView = QChartView(chart)
        chartView.setContentsMargins(-20, -10, -10, -10)
        chart.setContentsMargins(-20, -10, -10, -10)

        chart.setBackgroundBrush(QBrush(QColor("transparent")))
        chart.setTitleBrush(QBrush(QColor("white")));

        result['chartView'] = chartView

        return result

    def __updateScatterSeries(self):
        scatterSeries=self.__getScatterSeries()
        scatterSeries.clear()

        hasPoints=False
        for spectralLine in self.getModel().getSpectralLines():
            if spectralLine.pixelIndex is not None:
                scatterSeries.append(int(spectralLine.pixelIndex),int(spectralLine.nanometer))
                hasPoints=True

        if scatterSeries.chart() is not None and hasPoints:


            scatterSeries.chart().createDefaultAxes()

            ax = scatterSeries.chart().axes(Qt.Orientation.Horizontal, scatterSeries)[0]
            ax.setMin(min(SpectralLineUtil().getPixelIndices(self.getModel().getSpectralLines()))-50)
            ax.setMax(max(SpectralLineUtil().getPixelIndices(self.getModel().getSpectralLines()))+50)

            ay = scatterSeries.chart().axes(Qt.Orientation.Vertical, scatterSeries)[0]
            ay.setMin(min(SpectralLineUtil().getNanometers(self.getModel().getSpectralLines()))-50)
            ay.setMax(max(SpectralLineUtil().getNanometers(self.getModel().getSpectralLines()))+50)

            chart=scatterSeries.chart()
            chart.removeSeries(scatterSeries)
            chart.addSeries(scatterSeries)
            chart.createDefaultAxes()

            ax = scatterSeries.chart().axes(Qt.Orientation.Horizontal, scatterSeries)[0]
            ax.setMin(min(SpectralLineUtil().getPixelIndices(self.getModel().getSpectralLines()))-50)
            ax.setMax(max(SpectralLineUtil().getPixelIndices(self.getModel().getSpectralLines()))+50)

            ay = scatterSeries.chart().axes(Qt.Orientation.Vertical, scatterSeries)[0]
            ay.setMin(min(SpectralLineUtil().getNanometers(self.getModel().getSpectralLines()))-50)
            ay.setMax(max(SpectralLineUtil().getNanometers(self.getModel().getSpectralLines()))+50)


            q_pen = QPen(QBrush(QColor(50, 50, 50, 50)), 1)
            chart.axes(Qt.Orientation.Horizontal)[0].setGridLinePen(q_pen);
            chart.axes(Qt.Orientation.Vertical)[0].setGridLinePen(q_pen);



    def __getScatterSeries(self)->QScatterSeries:
        if self.__scatterSeries is None:
            self.__scatterSeries=QScatterSeries()
        self.__scatterSeries.setMarkerShape(QScatterSeries.MarkerShape.MarkerShapeCircle)
        self.__scatterSeries.setMarkerSize(8.0);
        self.__scatterSeries.setColor(ApplicationStyleLogicModule().getPrimaryColor())
        self.__scatterSeries.setBorderColor(ApplicationStyleLogicModule().getPrimaryTextColor())

        return self.__scatterSeries

    def setModel(self,model:SpectrometerCalibrationProfile):
        self.__model=model
        self.__updateScatterSeries()

    def getModel(self)->SpectrometerCalibrationProfile:
        return self.__model