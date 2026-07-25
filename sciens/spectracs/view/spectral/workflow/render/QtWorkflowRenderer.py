import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QSizePolicy, QVBoxLayout

from sciens.spectracs.logic.application.style.Metrics import Metrics
from sciens.spectracs.model.spectral.plugin.view.MetricFieldView import MetricFieldView
from sciens.spectracs.view.application.widgets.page.TooltipPageLabel import TooltipPageLabel
from sciens.spectracs.logic.spectral.report.WorkflowItemVisitor import WorkflowItemVisitor, dispatchItem


def workflowItemObjectName(label):
    # SPEC_director_cut.md E2 — a stable objectName for a rendered view-model so the doc-mode Director can point the
    # cursor at an individual field (the Verdict gauge, a specific chip/row). Slug rule (SHARED with the scenario,
    # §4): lowercase, every run of non-alphanumeric chars -> one "_", strip leading/trailing "_". e.g.
    # "Soret · 440–460 nm" -> "workflowItem.soret_440_460_nm".
    slug = re.sub(r"[^a-z0-9]+", "_", (label or "").lower()).strip("_")
    return ("workflowItem.%s" % slug) if slug else "workflowItem"


class QtWorkflowRenderer(WorkflowItemVisitor):
    # Qt implementation of the render seam (SPEC_plugin_driven_convergence.md §2A / P1). Renders a list of the
    # plugin's Qt-free view-models into a QWidget — this is the behaviour that used to live inline in
    # EvaluationResultRenderer, now behind the shared visitor so the matplotlib target (M2) reuses the dispatch.

    def render(self, items) -> QWidget:
        self.__container = QWidget()
        self.__layout = QVBoxLayout()
        self.__layout.setSpacing(Metrics.S)
        self.__container.setLayout(self.__layout)
        self.__swatchRow = None
        self.__metricGrid = None  # accumulates consecutive MetricFieldViews into one grid (aligned label column)
        self.__expandingContent = False  # set when a plot is added, so it FILLS the height instead of top-packing
        for item in items:
            if not isinstance(item, MetricFieldView):
                self.__flushMetricGrid()
            dispatchItem(item, self)
        self.__flushMetricGrid()
        # A step whose only content is a spectrum plot should fill the vertical space (Edwin, rig cosmetic) —
        # so skip the top-packing stretch when there is an expanding widget; keep it for metric/label lists.
        if not self.__expandingContent:
            self.__layout.addStretch(1)
        return self.__container

    # --- visitor methods ---

    def visitLabel(self, view):
        label = QLabel(view.text)
        label.setWordWrap(True)  # long text (e.g. the header) must wrap, else it forces the whole panel wide →
        self.__layout.addWidget(label)  # horizontal scrollbar at narrow width (§18.1)

    def visitVerdict(self, view):
        label = QLabel(str(view.roastState))
        label.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.__layout.addWidget(label)

    def visitGauge(self, view):
        # SPEC_roast_ampel.md §8.4 — a labeled metric-grid ROW (Edwin 2026-07-24): the caption is the gray label
        # chip in col 0 ("verdict (S/Q ratio)" in Evaluation, "Verdict" in LIMS), the gauge sits in col 1. The
        # col-1 content differs by render flags — band+swatch+pill (Option A) vs big pill + zone bar (Option B).
        from sciens.spectracs.view.spectral.workflow.GaugeWidget import GaugeWidget, HEADLINE_HEIGHT
        from sciens.spectracs.model.spectral.plugin.view.GaugeRender import GaugeRender
        if self.__metricGrid is None:
            widget = QWidget()
            grid = QGridLayout()
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setSpacing(Metrics.S)
            grid.setColumnStretch(0, 30)
            grid.setColumnStretch(1, 70)
            widget.setLayout(grid)
            self.__metricGrid = [widget, grid, 0]
        _, grid, row = self.__metricGrid
        label = TooltipPageLabel(view.caption or "")
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        if GaugeRender.BAND in view.render:                       # Option A: align the chip with the band top
            grid.addWidget(label, row, 0, 1, 1, Qt.AlignmentFlag.AlignTop)
        else:                                                     # Option B (LIMS): same height as the badge,
            label.setFixedHeight(HEADLINE_HEIGHT)                 # text vertically centred (Edwin 2026-07-24)
            label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            grid.addWidget(label, row, 0, 1, 1)
        gauge = GaugeWidget(view)
        gauge.setObjectName(workflowItemObjectName(view.caption or "verdict"))  # E2: Director point target
        grid.addWidget(gauge, row, 1, 1, 1)
        self.__metricGrid[2] = row + 1

    def visitColorSwatch(self, view):
        if self.__swatchRow is None:
            self.__swatchRow = self.__newSwatchRow()
            self.__layout.addWidget(self.__swatchRow)
        self.__addSwatch(self.__swatchRow, view)

    def visitMetricField(self, view):
        # A Spectrometer-setup-style row: gray PageLabel chip (col 0, 30%) + read-only value field (col 1,
        # 70%). Clicking the label pops the tooltip (TooltipPageLabel). Consecutive metrics share one grid.
        if self.__metricGrid is None:
            widget = QWidget()
            grid = QGridLayout()
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setSpacing(Metrics.S)
            grid.setColumnStretch(0, 30)
            grid.setColumnStretch(1, 70)
            widget.setLayout(grid)
            self.__metricGrid = [widget, grid, 0]
        _, grid, row = self.__metricGrid
        label = TooltipPageLabel(view.label)
        label.setObjectName(workflowItemObjectName(view.label))  # E2: Director point target (the field's label chip)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        if view.tooltip:
            label.setToolTip(view.tooltip)
        # S5: presentation the plugin attached (MetricFieldViewStyle). Apply via QFont so the gray-chip QSS on
        # TooltipPageLabel is preserved (a setStyleSheet would clobber it).
        style = getattr(view, "style", None)
        if style is not None and getattr(style, "isLabelBold", False):
            font = label.font()
            font.setBold(True)
            label.setFont(font)
        grid.addWidget(label, row, 0, 1, 1)
        # Three cases (SPEC_color_retrieval.md §F12): color+value → swatch + read-only field side-by-side (a colour
        # chip with its HSL text); color only → a full-width swatch; value only → a read-only field.
        color = getattr(view, "color", None)
        fieldHeight = QLineEdit().sizeHint().height()
        if color is not None:
            red, green, blue = color
            swatch = QLabel()
            swatch.setStyleSheet("background-color: rgb(%d,%d,%d); border: 1px solid #444;" % (red, green, blue))
            if view.value is not None:
                swatch.setFixedSize(fieldHeight, fieldHeight)     # square chip beside the HSL field
                cell = QWidget()
                cellLayout = QHBoxLayout()
                cellLayout.setContentsMargins(0, 0, 0, 0)
                cellLayout.setSpacing(Metrics.S)
                cell.setLayout(cellLayout)
                cellLayout.addWidget(swatch)
                field = QLineEdit(str(view.value))
                field.setReadOnly(True)
                cellLayout.addWidget(field)
                grid.addWidget(cell, row, 1, 1, 1)
            else:
                swatch.setFixedHeight(fieldHeight)                # full-width swatch (aligns to the grid rows)
                grid.addWidget(swatch, row, 1, 1, 1)
        else:
            field = QLineEdit(str(view.value))
            field.setReadOnly(True)
            grid.addWidget(field, row, 1, 1, 1)
        self.__metricGrid[2] = row + 1

    def visitSpectrumPlot(self, view):
        # P2: draw a real curve (pyqtgraph) from the view's traces + shaded band annotations. Supports the
        # single-spectrum case and multi-trace overlays (Reference + Sample).
        import pyqtgraph as pg
        from sciens.spectracs.view.spectral.workflow.SpectrumPlotWidget import SpectrumPlotWidget
        plot = SpectrumPlotWidget()
        palette = ["y", "c", "m", "g", "r"]
        traces = view.allTraces() if hasattr(view, "allTraces") else [(view.spectrum, None, None)]
        first = True
        for index, (spectrum, _label, color) in enumerate(traces):
            plot.plotSpectrum(spectrum, title=(view.title if first else None),
                              color=(color or palette[index % len(palette)]), clear=first)
            first = False
        for band in (getattr(view, "bands", None) or []):
            region = pg.LinearRegionItem(values=(band[0], band[1]), movable=False,
                                         brush=pg.mkBrush(120, 120, 120, 40))
            region.setZValue(-10)
            plot.addItem(region)
        for marker in (getattr(view, "markers", None) or []):
            line = pg.InfiniteLine(pos=marker[0], angle=90,
                                   pen=pg.mkPen('w', style=Qt.PenStyle.DashLine))
            plot.addItem(line)
        plot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.__layout.addWidget(plot)
        self.__expandingContent = True

    def visitSpectrumCapture(self, view):
        # P2: the captured raster (host-filled `.image`). Passive — a scaled image + optional caption.
        from PySide6.QtGui import QPixmap, QImage
        from sciens.spectracs.view.application.widgets.ScaledImageLabel import ScaledImageLabel
        image = getattr(view, "image", None)
        if image is None:
            self.__layout.addWidget(QLabel(view.caption or "(no image)"))
            return
        pixmap = image if isinstance(image, QPixmap) else QPixmap.fromImage(image) if isinstance(image, QImage) else None
        if pixmap is None:
            self.__layout.addWidget(QLabel(view.caption or "(image)"))
            return
        label = ScaledImageLabel()
        label.setImagePixmap(pixmap)
        label.setFill(True)   # use the full width available — a raster's exact aspect isn't meaningful (Edwin)
        self.__layout.addWidget(label, 1)   # fill: ScaledImageLabel is Ignored-sized, needs the stretch
        if view.caption:
            caption = QLabel(view.caption)
            caption.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.__layout.addWidget(caption)
        self.__expandingContent = True

    def visitTabGroup(self, view):
        # T2 (SPEC_simplified_plugin_navigation.md §7b): an explicit sub-tab group — one QTabWidget, each child
        # rendered in its own panel by a FRESH renderer (so a child plot/capture keeps its own expanding-fill),
        # added under its declared title. The group fills the height like a plot/capture does.
        from PySide6.QtWidgets import QTabWidget, QSizePolicy
        tabs = QTabWidget()
        for label, child in view.tabs:
            tabs.addTab(QtWorkflowRenderer().render([child]), label or "")
        tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.__layout.addWidget(tabs, 1)
        self.__expandingContent = True

    # --- accumulation helpers ---

    def __flushMetricGrid(self):
        if self.__metricGrid is not None:
            self.__layout.addWidget(self.__metricGrid[0])
        self.__metricGrid = None

    def __newSwatchRow(self):
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
