from PySide6.QtCharts import QLineSeries, QChart, QChartView, QScatterSeries, QSplineSeries
from PySide6.QtCore import Qt, QMargins
from PySide6.QtGui import QBrush, QColor, QPen
from numpy import poly1d

from logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from logic.spectral.util.SpectrallineUtil import SpectralLineUtil
from model.databaseEntity.spectral.device import SpectrometerCalibrationProfile
from view.application.widgets.page.PageWidget import PageWidget


class SpectrometerCalibrationProfileSpectralLinesInterpolationViewModule(PageWidget):

    __model: SpectrometerCalibrationProfile = None
    __scatterSeries:QScatterSeries=None
    __splineSeries: QSplineSeries = None

    def getMainContainerWidgets(self):
        result= super().getMainContainerWidgets()

        chart = QChart()
        chart.addSeries(self.__getScatterSeries())
        chart.addSeries(self.__getSplineSeries())
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

        hasPoints=self.__doesModelHasCalibratedSpectralLines()

        for spectralLine in self.getModel().getSpectralLines():
            if spectralLine.pixelIndex is not None:
                scatterSeries.append(int(spectralLine.pixelIndex),int(spectralLine.spectralLineMasterData.nanometer))

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

            series = chart.series()

            return

    def __doesModelHasCalibratedSpectralLines(self):

        spectralLines = self.getModel().getSpectralLines()

        result=False
        for spectralLine in spectralLines:
            if spectralLine.pixelIndex is not None:
                result = True
            else:
                result = False
                break

        return result

    def __updateSplineSeries(self):
        splineSeries=self.__getSplineSeries()
        splineSeries.clear()

        model = self.getModel()

        hasCalibratedSpectralLines = self.__doesModelHasCalibratedSpectralLines()

        if hasCalibratedSpectralLines:
            spectralLines = model.getSpectralLines()
            pixelIndices = SpectralLineUtil().getPixelIndices(spectralLines)
            minPixelIndex=min(pixelIndices)-50
            maxPixelIndex = max(pixelIndices)+50

            polynomial=poly1d([model.interpolationCoefficientA,model.interpolationCoefficientB,model.interpolationCoefficientC,model.interpolationCoefficientD])

            for pixelIndex in range(minPixelIndex,maxPixelIndex,20):
                nanometer=polynomial(pixelIndex)
                splineSeries.append(int(pixelIndex), int(nanometer))

            chart = splineSeries.chart()

            if chart is not None:
                chart.removeSeries(splineSeries)
                chart.addSeries(splineSeries)
                chart.createDefaultAxes()

    def __getScatterSeries(self)->QScatterSeries:
        if self.__scatterSeries is None:
            self.__scatterSeries=QScatterSeries()
        self.__scatterSeries.setMarkerShape(QScatterSeries.MarkerShape.MarkerShapeCircle)
        self.__scatterSeries.setMarkerSize(8.0);
        self.__scatterSeries.setColor(ApplicationStyleLogicModule().getPrimaryColor())
        self.__scatterSeries.setBorderColor(ApplicationStyleLogicModule().getPrimaryTextColor())

        return self.__scatterSeries

    def __getSplineSeries(self)->QScatterSeries:
        if self.__splineSeries is None:
            self.__splineSeries=QSplineSeries()
        self.__splineSeries.setColor(ApplicationStyleLogicModule().getPrimaryTextColor())
        return self.__splineSeries


    def setModel(self,model:SpectrometerCalibrationProfile):
        self.__model=model
        self.__updateSplineSeries()
        self.__updateScatterSeries()

    def getModel(self)->SpectrometerCalibrationProfile:
        return self.__model