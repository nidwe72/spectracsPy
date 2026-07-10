from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QLineEdit, QSizePolicy, QVBoxLayout

from sciens.spectracs.logic.appliction.style.Metrics import Metrics
from sciens.spectracs.model.spectral.evaluation.ColorSwatchView import ColorSwatchView
from sciens.spectracs.model.spectral.evaluation.LabelView import LabelView
from sciens.spectracs.model.spectral.evaluation.MetricFieldView import MetricFieldView
from sciens.spectracs.model.spectral.evaluation.SpectrumPlotView import SpectrumPlotView
from sciens.spectracs.model.spectral.evaluation.VerdictView import VerdictView
from sciens.spectracs.view.application.widgets.page.TooltipPageLabel import TooltipPageLabel


class EvaluationResultRenderer:
    # Host-side renderer (SPEC_pumpkin_integration.md C.3): turns the plugin's Qt-free EvaluationResult
    # view-models into real widgets. The plugin produces plain data (rgb tuples, strings); the Qt lives here.

    def render(self, evaluationResult) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(Metrics.S)
        container.setLayout(layout)

        swatchRow = None
        metricGrid = None  # accumulates consecutive MetricFieldViews into one grid (aligned label column)
        for item in evaluationResult.getItems():
            if not isinstance(item, MetricFieldView):
                metricGrid = self.__flushMetricGrid(layout, metricGrid)
            if isinstance(item, ColorSwatchView):
                if swatchRow is None:
                    swatchRow = self.__swatchRow()
                    layout.addWidget(swatchRow)
                self.__addSwatch(swatchRow, item)
            elif isinstance(item, VerdictView):
                layout.addWidget(self.__verdictLabel(item.roastState))
            elif isinstance(item, MetricFieldView):
                metricGrid = self.__addMetricRow(metricGrid, item)
            elif isinstance(item, LabelView):
                label = QLabel(item.text)
                label.setWordWrap(True)  # long text (e.g. the header) must wrap, else it forces the whole
                layout.addWidget(label)  # panel wide → horizontal scrollbar at narrow width (§18.1)
            elif isinstance(item, SpectrumPlotView):
                title = item.title or "Spectrum"
                points = len(item.spectrum.valuesByNanometers) if item.spectrum is not None else 0
                layout.addWidget(QLabel("%s (%d points)" % (title, points)))

        self.__flushMetricGrid(layout, metricGrid)
        layout.addStretch(1)
        return container

    def __addMetricRow(self, metricGrid, metricFieldView):
        # A Spectrometer-setup-style row: gray PageLabel chip (col 0, 30%) + read-only value field (col 1,
        # 70%). Clicking the label pops the tooltip (TooltipPageLabel). Consecutive metrics share one grid.
        if metricGrid is None:
            widget = QWidget()
            grid = QGridLayout()
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setSpacing(Metrics.S)
            grid.setColumnStretch(0, 30)
            grid.setColumnStretch(1, 70)
            widget.setLayout(grid)
            metricGrid = [widget, grid, 0]
        _, grid, row = metricGrid
        label = TooltipPageLabel(metricFieldView.label)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        if metricFieldView.tooltip:
            label.setToolTip(metricFieldView.tooltip)
        # S5: presentation the plugin attached (MetricFieldViewStyle). Apply via QFont so the gray-chip QSS on
        # TooltipPageLabel is preserved (a setStyleSheet would clobber it).
        style = getattr(metricFieldView, "style", None)
        if style is not None and getattr(style, "labelBold", False):
            font = label.font()
            font.setBold(True)
            label.setFont(font)
        field = QLineEdit(str(metricFieldView.value))
        field.setReadOnly(True)
        grid.addWidget(label, row, 0, 1, 1)
        grid.addWidget(field, row, 1, 1, 1)
        metricGrid[2] = row + 1
        return metricGrid

    def __flushMetricGrid(self, layout, metricGrid):
        if metricGrid is not None:
            layout.addWidget(metricGrid[0])
        return None

    def __swatchRow(self):
        row = QWidget()
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Metrics.M)
        row.setLayout(layout)
        row.setProperty("swatchColumn", 0)
        return row

    def __addSwatch(self, row, colorSwatchView):
        column = row.property("swatchColumn") or 0
        cell = QWidget()
        cellLayout = QVBoxLayout()
        cellLayout.setContentsMargins(0, 0, 0, 0)
        cell.setLayout(cellLayout)

        block = QLabel()
        block.setFixedSize(96, 96)
        red, green, blue = colorSwatchView.rgb
        block.setStyleSheet("background-color: rgb(%d,%d,%d); border: 1px solid #444;" % (red, green, blue))
        cellLayout.addWidget(block)
        if colorSwatchView.label:
            caption = QLabel(colorSwatchView.label)
            caption.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            cellLayout.addWidget(caption)

        row.layout().addWidget(cell, 0, column, 1, 1)
        row.setProperty("swatchColumn", column + 1)

    def __verdictLabel(self, roastState):
        label = QLabel(str(roastState))
        label.setStyleSheet("font-weight: bold; font-size: 16px;")
        return label
