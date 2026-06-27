import pyqtgraph as pg
from numpy import poly1d

from sciens.spectracs.logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from sciens.spectracs.logic.spectral.util.SpectrallineUtil import SpectralLineUtil
from sciens.spectracs.model.databaseEntity.spectral.device.calibration.SpectrometerCalibrationProfile import \
    SpectrometerCalibrationProfile
from sciens.spectracs.view.application.widgets.chart.ChartThemeUtil import ChartThemeUtil
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget


class SpectrometerCalibrationProfileSpectralLinesInterpolationViewModule(PageWidget):

    __model: SpectrometerCalibrationProfile = None
    __plotWidget: pg.PlotWidget = None
    __scatterItem: pg.ScatterPlotItem = None
    __curveItem: pg.PlotDataItem = None

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        style = ApplicationStyleLogicModule()

        self.__plotWidget = pg.PlotWidget()
        ChartThemeUtil.stylePlotWidget(self.__plotWidget)

        # The calibrated spectral lines as points (pixel index -> nanometer).
        self.__scatterItem = pg.ScatterPlotItem(
            size=8.0,
            brush=pg.mkBrush(style.getPrimaryColor()),
            pen=pg.mkPen(style.getPrimaryTextColor()),
        )
        # The fitted calibration curve (the cubic polynomial sampled densely).
        # This was a QtCharts QSplineSeries, but the data is already the smooth
        # calibration polynomial - no spline interpolation is involved.
        self.__curveItem = pg.PlotDataItem(pen=pg.mkPen(style.getPrimaryTextColor(), width=2))

        self.__plotWidget.addItem(self.__curveItem)
        self.__plotWidget.addItem(self.__scatterItem)

        result['chartView'] = self.__plotWidget

        self.__refresh()

        return result

    def __refresh(self):
        if self.__plotWidget is None or self.getModel() is None:
            return

        self.__updateCurve()
        self.__updateScatter()

    def __updateScatter(self):
        self.__scatterItem.clear()

        if not self.__doesModelHasCalibratedSpectralLines():
            return

        xs = []
        ys = []
        for spectralLine in self.getModel().getSpectralLines():
            if spectralLine.pixelIndex is not None:
                xs.append(int(spectralLine.pixelIndex))
                ys.append(int(spectralLine.spectralLineMasterData.nanometer))

        self.__scatterItem.setData(xs, ys)

        spectralLines = self.getModel().getSpectralLines()
        pixelIndices = SpectralLineUtil().getPixelIndices(spectralLines)
        nanometers = SpectralLineUtil().getNanometers(spectralLines)

        # Same +/-50 padding the QtCharts version applied to the auto axes.
        self.__plotWidget.setXRange(min(pixelIndices) - 50, max(pixelIndices) + 50, padding=0)
        self.__plotWidget.setYRange(min(nanometers) - 50, max(nanometers) + 50, padding=0)

    def __doesModelHasCalibratedSpectralLines(self):

        spectralLines = self.getModel().getSpectralLines()

        result = False
        for spectralLine in spectralLines:
            if spectralLine.pixelIndex is not None:
                result = True
            else:
                result = False
                break

        return result

    def __updateCurve(self):
        self.__curveItem.clear()

        model = self.getModel()

        if not self.__doesModelHasCalibratedSpectralLines():
            return

        spectralLines = model.getSpectralLines()
        pixelIndices = SpectralLineUtil().getPixelIndices(spectralLines)
        minPixelIndex = min(pixelIndices) - 50
        maxPixelIndex = max(pixelIndices) + 50

        polynomial = poly1d([model.interpolationCoefficientA, model.interpolationCoefficientB,
                             model.interpolationCoefficientC, model.interpolationCoefficientD])

        xs = []
        ys = []
        for pixelIndex in range(minPixelIndex, maxPixelIndex, 20):
            xs.append(int(pixelIndex))
            ys.append(int(polynomial(pixelIndex)))

        self.__curveItem.setData(xs, ys)

    def setModel(self, model: SpectrometerCalibrationProfile):
        self.__model = model
        self.__refresh()

    def getModel(self) -> SpectrometerCalibrationProfile:
        return self.__model
