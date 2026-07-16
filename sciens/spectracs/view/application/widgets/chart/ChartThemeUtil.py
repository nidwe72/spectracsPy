import pyqtgraph as pg

from sciens.spectracs.logic.application.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule


class ChartThemeUtil:
    """
    Single source of truth for styling pyqtgraph plots in the app's dark theme,
    built on top of ApplicationStyleLogicModule (see docs/SPEC_pyside6_and_android.md, D8).

    Replaces the per-chart QtCharts styling (transparent background, white title,
    dark grid) that was scattered across the three former QtCharts view modules.
    """

    @staticmethod
    def stylePlotWidget(plotWidget: pg.PlotWidget):
        style = ApplicationStyleLogicModule()

        # Transparent background so the app's dark page background shows through
        # (the QtCharts charts used a transparent QBrush for the same effect).
        plotWidget.setBackground(None)

        plotItem = plotWidget.getPlotItem()

        # Axis lines + tick labels in the light body-text color so they stay
        # readable over the dark background.
        textColor = style.getTextColor()
        for axisName in ('left', 'bottom', 'right', 'top'):
            axis = plotItem.getAxis(axisName)
            axis.setPen(textColor)
            axis.setTextPen(textColor)

        # Subtle grid (the QtCharts version used getSecondaryChartGridColor).
        plotItem.showGrid(x=True, y=True, alpha=0.2)

        # Static, non-interactive feel matching the old QChartView (no zoom/pan,
        # no context menu, no auto-range button) so frozen axes stay frozen.
        plotItem.hideButtons()
        plotWidget.setMenuEnabled(False)
        plotWidget.setMouseEnabled(x=False, y=False)

    @staticmethod
    def titleColorName() -> str:
        # White title brush, as the QtCharts charts used (setTitleBrush).
        return ApplicationStyleLogicModule().getPrimaryTextColor().name()

    @staticmethod
    def primaryPen(width: int = 2):
        return pg.mkPen(color=ApplicationStyleLogicModule().getPrimaryColor(), width=width)

    @staticmethod
    def grayPen(grayValue: int, width: int = 1):
        return pg.mkPen(color=(grayValue, grayValue, grayValue), width=width)
