from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QVBoxLayout

from sciens.spectracs.logic.appliction.style.Metrics import Metrics
from sciens.spectracs.model.spectral.evaluation.ColorSwatchView import ColorSwatchView
from sciens.spectracs.model.spectral.evaluation.LabelView import LabelView
from sciens.spectracs.model.spectral.evaluation.SpectrumPlotView import SpectrumPlotView
from sciens.spectracs.model.spectral.evaluation.VerdictView import VerdictView


class EvaluationResultRenderer:
    # Host-side renderer (SPEC_pumpkin_integration.md C.3): turns the plugin's Qt-free EvaluationResult
    # view-models into real widgets. The plugin produces plain data (rgb tuples, strings); the Qt lives here.

    def render(self, evaluationResult) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(Metrics.S)
        container.setLayout(layout)

        swatchRow = None
        for item in evaluationResult.getItems():
            if isinstance(item, ColorSwatchView):
                if swatchRow is None:
                    swatchRow = self.__swatchRow()
                    layout.addWidget(swatchRow)
                self.__addSwatch(swatchRow, item)
            elif isinstance(item, VerdictView):
                layout.addWidget(self.__verdictLabel(item.roastState))
            elif isinstance(item, LabelView):
                layout.addWidget(QLabel(item.text))
            elif isinstance(item, SpectrumPlotView):
                title = item.title or "Spectrum"
                points = len(item.spectrum.valuesByNanometers) if item.spectrum is not None else 0
                layout.addWidget(QLabel("%s (%d points)" % (title, points)))

        layout.addStretch(1)
        return container

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
