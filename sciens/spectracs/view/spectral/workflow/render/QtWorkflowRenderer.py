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
            # D2: an out-of-gamut chromaticity is DRAWN as a per-channel clamp of itself, so the swatch is not
            # the colour the numbers describe. Mark it with a dashed amber border rather than silently painting
            # a confident wrong colour (DOC_colour_geometry.md §12.1).
            isOutOfGamut = style is not None and getattr(style, "isOutOfGamut", False)
            border = "2px dashed #c8862a" if isOutOfGamut else "1px solid #444"
            swatch.setStyleSheet("background-color: rgb(%d,%d,%d); border: %s;"
                                 % (red, green, blue, border))
            if isOutOfGamut:
                swatch.setToolTip("This chromaticity is outside sRGB — the swatch is a clamped "
                                  "approximation, not the colour the numbers describe.")
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

    # Below this camera DN a bin is quantization-limited (SPEC_capture_quality.md §17.6/11); drawn as a line on
    # DN-axis plots so "too dilute / too dark" is visible instead of inferred.
    # ⚠ LEGACY FALLBACK ONLY (SPEC_soret_448_trim.md §13). The guard is a MEASUREMENT constant and now belongs
    # to the plugin, which declares it via SpectrumPlotView.addLevel(). This copy survives for one reason: a
    # DbMeasurement blob written before 2026-08-10 carries no levels, and its saved plot must still show the
    # guard it was read against. A view that declares ANY level owns its guards outright.
    __LOW_DN_GUARD = 16.0
    __GUARD_COLOR = (200, 120, 60)
    __BAND_BRUSH = (120, 120, 120, 40)
    __LEVEL_COLOR = "#d0d0d0"
    # SPEC_soret_448_trim.md §25.2/§25.3 — annotation styling is RENDERER-owned, never plugin-declared: this
    # renderer draws on a DARK plot and the report renderer on WHITE paper, from the same view-model.
    __CAPTION_COLOR = "#ffffff"          # band + marker captions (they used to inherit the band's SHADING
    #                                      colour, so semi-transparent anchors rendered as ghosts)
    __BADGE_TEXT = "#ffffff"
    __LEGEND_BORDER = "#9a9a9a"
    __LEGEND_FILL = (18, 18, 18, 190)    # semitransparent, square-cornered (Edwin: no rounded corners)
    __LEGEND_PADDING = 34.0              # default magnitude if a view declares a position but no padding

    def visitSpectrumPlot(self, view):
        # P2: draw a real curve (pyqtgraph) from the view's traces + shaded band annotations. Supports the
        # single-spectrum case and multi-trace overlays (Reference + Sample).
        import pyqtgraph as pg
        from sciens.spectracs.view.spectral.workflow.SpectrumPlotWidget import SpectrumPlotWidget
        from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil
        plot = SpectrumPlotWidget()
        palette = ["y", "c", "m", "g", "r"]
        traces = view.allTraces() if hasattr(view, "allTraces") else [(view.spectrum, None, None, None)]
        # axis="dn": raw capture spectra are drawn on a camera-DN axis (§16.7.2e) — display-only, the values
        # themselves stay linear everywhere else.
        asDn = getattr(view, "axis", None) == "dn"
        levels = getattr(view, "levels", None) or []
        util = SpectralColorUtil()
        first = True
        for index, (spectrum, _label, color, style) in enumerate(traces):
            plot.plotSpectrum(util.toDisplayDnSpectrum(spectrum) if asDn else spectrum,
                              title=(view.title if first else None),
                              color=(color or palette[index % len(palette)]), clear=first, style=style)
            first = False
        if asDn:
            plot.getPlotItem().setLabel("left", "camera DN")
            if not levels:   # legacy blob (no declared guards) -> draw the one the run was read against
                guard = pg.InfiniteLine(pos=self.__LOW_DN_GUARD, angle=0,
                                        pen=pg.mkPen(self.__GUARD_COLOR, style=Qt.PenStyle.DashLine))
                guard.setZValue(-5)
                plot.addItem(guard)
        for band in (getattr(view, "bands", None) or []):
            color = band[3] if len(band) > 3 else None
            brush = pg.mkBrush(color) if color else pg.mkBrush(*self.__BAND_BRUSH)
            region = pg.LinearRegionItem(values=(band[0], band[1]), movable=False, brush=brush)
            # ⚠ A LinearRegionItem draws its two DRAG HANDLES as bright vertical lines. On a non-movable
            # annotation those read as data — a band edge is not a measurement. Hide them; the fill IS the band.
            for handle in region.lines:
                handle.setPen(pg.mkPen(None))
            region.setZValue(-10)
            plot.addItem(region, ignoreBounds=True)   # shading is an annotation; the CURVE sets the range
            label = band[2] if len(band) > 2 else None
            if label:
                # The caption rides INSIDE the span, pinned to the top edge — a band's name has to travel with
                # the band, and it is the same string the report renderer draws (M2: the preview IS the PDF).
                # ⚠ It does NOT inherit `color`: that is the band's SHADING colour, and for a recessive anchor
                # shade (#5a6a7a55) the caption rendered as a ghost — §25.3, Edwin read it off the rig.
                self.__topAnchoredText(plot, (band[0] + band[1]) / 2.0, str(label), self.__CAPTION_COLOR)
        for level in levels:
            self.__drawLevel(plot, level)
        for marker in (getattr(view, "markers", None) or []):
            line = pg.InfiniteLine(pos=marker[0], angle=90,
                                   pen=pg.mkPen('w', style=Qt.PenStyle.DashLine))
            plot.addItem(line)
            if len(marker) > 1 and marker[1]:
                # B6 (SPEC_soret_448_trim.md §8.3): matplotlib annotated the marker and the screen did not, so
                # the "Q" label appeared on paper only — the exact drift M2 forbids.
                # ⚠ At the BOTTOM, not the top: a marker usually sits INSIDE a band (λmax lives in the Q
                # window), so two captions on the same row overprint each other. Bands own the top row,
                # markers the bottom one — and the report renderer follows the same split.
                self.__topAnchoredText(plot, marker[0], str(marker[1]), self.__CAPTION_COLOR, atTop=False)
        self.__drawLegend(plot, view)
        plot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.__layout.addWidget(plot)
        self.__expandingContent = True

    __BADGE_SIZE = 19

    class __BadgeSample:
        """The legend's sample column paints the badge itself (D-sample, Edwin) — so a row reads `③ red-anchor
        mean` and the number means the same thing in both places. Built lazily as a pyqtgraph ItemSample
        subclass because pyqtgraph must not be imported at module scope in this renderer."""

        def __new__(cls, number, barColor):
            import pyqtgraph as pg
            from PySide6.QtCore import QRectF
            from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil
            fill = SpectralColorUtil().darkenHex(barColor)
            textColor = QtWorkflowRenderer._QtWorkflowRenderer__BADGE_TEXT

            class BadgeSample(pg.ItemSample):
                def boundingRect(self):
                    return QRectF(0, 0, 22, 20)

                def paint(self, painter, *args):
                    painter.setRenderHint(painter.RenderHint.Antialiasing, True)
                    painter.setBrush(pg.mkBrush(fill))
                    painter.setPen(pg.mkPen(barColor, width=1))
                    painter.drawEllipse(QRectF(2, 1, 18, 18))
                    painter.setPen(pg.mkPen(textColor))
                    font = painter.font()
                    font.setPointSize(8)
                    font.setBold(True)
                    painter.setFont(font)
                    painter.drawText(QRectF(2, 1, 18, 18), Qt.AlignmentFlag.AlignCenter, str(number))

            return BadgeSample(pg.PlotDataItem())

    def __topAnchoredText(self, plot, nanometers, label, color, atTop=True):
        # A caption that sits at the TOP of whatever the plot currently shows and stays there while the view
        # rescales. pyqtgraph has no "axes-fraction" anchor, so place it once at today's range and follow the
        # signal — the alternative (a fixed y) leaves the label off-screen as soon as the data changes.
        #
        # ⛔⛔ `ignoreBounds=True` IS LOAD-BEARING — without it the plot ANIMATES ITSELF TO DEATH. A TextItem has
        # a fixed PIXEL size, so parked at the top edge it always protrudes ABOVE the range; auto-range then
        # expands to enclose it, which fires sigYRangeChanged, which moves the caption to the NEW top, which
        # protrudes again. Measured on a real run: the y-span grew ~4.7 % per event-loop tick, without bound —
        # the curve appears to shrink because the axis keeps growing underneath it (Edwin saw it as "like an
        # animation"). An annotation must never drive auto-range.
        # ⚠ The InfiniteLine guides DO stay inside the bounds, deliberately — that is what makes a 60 DN guard
        # visible when a fill peaks below it, and lines cannot feed back because they do not move.
        # ⚠ EDGE CLAMP (§25.3): a caption centred on a band near the window edge overflows the plot and gets
        # cut — "red anchor" at 625 nm on a window ending at 636 rendered as "ed anchor". Pin the caption's
        # RIGHT edge (or left) instead of its centre when it would otherwise leave the view.
        import pyqtgraph as pg
        viewBox = plot.getPlotItem().vb
        low, high = viewBox.viewRange()[0]
        margin = 0.06 * (high - low)
        anchorX = 1.0 if nanometers > high - margin else (0.0 if nanometers < low + margin else 0.5)
        text = pg.TextItem(label, color=color, anchor=(anchorX, 0.0 if atTop else 1.0))
        text.setZValue(-4)
        plot.addItem(text, ignoreBounds=True)
        edge = 1 if atTop else 0
        text.setPos(nanometers, viewBox.viewRange()[1][edge])
        viewBox.sigYRangeChanged.connect(
            lambda _viewBox, valueRange, item=text, x=nanometers, e=edge: item.setPos(x, valueRange[e]))

    def __drawLevel(self, plot, level):
        # SPEC_soret_448_trim.md §12.2 — one primitive, two shapes: unranged = a full-width guide line (the DN
        # guards), ranged = a BAR over the band at that height (a band mean, drawn where it is measured).
        # ⚠ NOT gamma-encoded on a dn-axis plot: only the CURVE is decoded for display; a declared level is
        # already in that space (encoding 16 DN would land it at 0.58 — the bug the DN axis exists to prevent).
        import pyqtgraph as pg
        from sciens.spectracs.view.spectral.workflow.SpectrumPlotWidget import SpectrumPlotWidget
        value, lowNm, highNm, label, color, style, number = tuple(level) + (None,) * (7 - len(level))
        pen = SpectrumPlotWidget.pen(color or self.__LEVEL_COLOR, width=2, style=style)
        if lowNm is None or highNm is None:
            # pyqtgraph draws the caption on the line itself (InfLineLabel) — no manual follow needed.
            line = pg.InfiniteLine(pos=value, angle=0, pen=pen, label=(str(label) if label else None),
                                   labelOpts={"position": 0.04, "color": (color or self.__LEVEL_COLOR),
                                              "movable": False})
            line.setZValue(-5)
            plot.addItem(line)
            return
        plot.plot([lowNm, highNm], [value, value], pen=pen)
        if number is not None:
            # §25.2 — a numbered bar wears a BADGE instead of a caption; the caption text moves to the legend.
            self.__drawBadge(plot, (lowNm + highNm) / 2.0, value, number, color or self.__LEVEL_COLOR)
        elif label:
            text = pg.TextItem(str(label), color=(color or self.__LEVEL_COLOR), anchor=(0.5, 1.0))
            text.setPos((lowNm + highNm) / 2.0, value)
            plot.addItem(text, ignoreBounds=True)   # a caption is not data — see __topAnchoredText

    def __drawBadge(self, plot, nanometers, value, number, barColor):
        # A numbered disc sitting ON the annotation it names (SPEC_soret_448_trim.md §25.2). Fill = a DARKENED
        # shade of the bar's colour so a white numeral is legible (1.84:1 -> 5.24:1 on the cyan bar); ring =
        # the bar's own colour, so the badge still reads as belonging to that bar.
        import pyqtgraph as pg
        from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil
        fill = SpectralColorUtil().darkenHex(barColor)
        disc = pg.ScatterPlotItem([nanometers], [value], symbol="o", size=self.__BADGE_SIZE,
                                  brush=pg.mkBrush(fill), pen=pg.mkPen(barColor, width=1))
        plot.addItem(disc, ignoreBounds=True)
        text = pg.TextItem(str(number), color=self.__BADGE_TEXT, anchor=(0.5, 0.5))
        text.setPos(nanometers, value)
        plot.addItem(text, ignoreBounds=True)

    def __drawLegend(self, plot, view):
        # §25.2 — the declared legend. Rows are DERIVED from the view (numbered levels, then labelled traces),
        # so a badge and its row are the same fact. Parented to the ViewBox rather than added to the scene, so
        # it is corner-anchored, immune to rescaling, and structurally unable to feed the auto-range (§20.2).
        import pyqtgraph as pg
        from sciens.spectracs.model.spectral.plugin.view.LegendPosition import LegendPosition
        position = LegendPosition.parse(getattr(view, "legendPosition", None))
        rows = view.legendRows() if position is not None and hasattr(view, "legendRows") else []
        if not rows:
            return
        legend = pg.LegendItem(pen=pg.mkPen(self.__LEGEND_BORDER), brush=pg.mkBrush(*self.__LEGEND_FILL),
                               labelTextColor=self.__CAPTION_COLOR, labelTextSize="9pt", frame=True,
                               verSpacing=1)
        legend.setParentItem(plot.getPlotItem().vb)
        padding = getattr(view, "legendPadding", None) or self.__LEGEND_PADDING
        signX, signY = position.paddingSigns()
        corner = position.corner()
        legend.anchor(itemPos=corner, parentPos=corner, offset=(signX * padding, signY * padding))
        for number, label, color in rows:
            if number is None:
                # A CURVE: no badge — named by text in its own colour (Edwin). pyqtgraph's LegendItem paints
                # one colour for every label, so the per-row colour has to ride in as HTML.
                sample = pg.ItemSample(pg.PlotDataItem(pen=pg.mkPen(color or self.__CAPTION_COLOR, width=3)))
                legend.addItem(sample, '<span style="color:%s">%s</span>'
                               % (color or self.__CAPTION_COLOR, label))
            else:
                legend.addItem(self.__BadgeSample(number, color or self.__LEVEL_COLOR), str(label or ""))

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
            # ⭐ a tab may carry ONE view-model or a LIST of them (a summary column of metric rows).
            items = child if isinstance(child, list) else [child]
            tabs.addTab(QtWorkflowRenderer().render(items), label or "")
        tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.__layout.addWidget(tabs, 1)
        self.__expandingContent = True

    def visitSeriesPlot(self, view):
        """The stacked time-series plot (SPEC_settled_measurement.md §18.3/§18.7) — header, panels, footer.

        ⭐ Two rendering rules, both found by mocking it before building it (§18.7):
          ⛔ each panel AUTOSCALES to its own data. Drawing the 12-22 `Q%` domain as axis levels would force
             a 10-unit axis around a 0.5-unit trajectory and flatten the trace into a line — which is why
             the domain arrives as a HEADER field instead.
          ⭐ per-panel `scale`: `A_valley` falls by a factor of 40, so on a linear axis the settling tail —
             the very thing the gate judges — sits in the bottom 3 % of the panel. It renders as log.
        ⭐ The renderer draws numbers under labels it was handed; it never learns that "A_valley" is a
        wavelength window (§18.3).
        """
        import pyqtgraph
        from PySide6.QtWidgets import QSizePolicy

        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Metrics.S)
        panel.setLayout(layout)

        if view.title:
            title = QLabel(view.title)
            title.setStyleSheet("font-weight: bold;")
            layout.addWidget(title)
        if view.header:
            layout.addWidget(self.__fieldStrip(view.header, bold=True))

        for panelSpec in view.panels:
            plot = pyqtgraph.PlotWidget()
            plot.setBackground(None)
            plot.showGrid(x=True, y=True, alpha=0.2)
            plot.setLabel("bottom", view.xLabel or "")
            plot.setLabel("left", panelSpec.get("label") or panelSpec.get("key") or "")
            if panelSpec.get("scale") == "log":
                plot.setLogMode(False, True)
            for series in panelSpec.get("series", []):
                pen = pyqtgraph.mkPen(series.get("color") or "#e08000", width=2)
                plot.plot(series["xs"], series["ys"], pen=pen, symbol="o", symbolSize=5,
                          symbolBrush=series.get("color") or "#e08000")
            for level in panelSpec.get("levels", []):
                line = pyqtgraph.InfiniteLine(pos=level["value"], angle=0, label=level.get("label") or "",
                                              pen=pyqtgraph.mkPen("#888888", style=Qt.PenStyle.DashLine))
                plot.addItem(line)
            for marker in panelSpec.get("markers", []):
                line = pyqtgraph.InfiniteLine(pos=marker["x"], angle=90, label=marker.get("label") or "",
                                              pen=pyqtgraph.mkPen(marker.get("color") or "#4aa3df",
                                                                  style=Qt.PenStyle.DotLine))
                plot.addItem(line)
            for point in panelSpec.get("points", []):
                # ⭐ THE LATCHED ANSWER. Without it a reader cannot see WHICH row became the number.
                plot.plot([point["x"]], [point["y"]], pen=None, symbol="star", symbolSize=18,
                          symbolBrush=point.get("color") or "#2ECC71")
            plot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            layout.addWidget(plot, 1)

        if view.footer:
            # ⭐ §18.7: without the audit line a saved graph is a picture, not a record.
            layout.addWidget(self.__fieldStrip(view.footer, muted=True))

        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.__layout.addWidget(panel, 1)
        self.__expandingContent = True

    def __fieldStrip(self, fields, bold=False, muted=False):
        # A one-line key/value strip — the §13.2 "legend box" content, reused for the header and footer.
        # ⚠ §17/U6: it WRAPS, so at 412 dp it reflows to further lines instead of forcing a wide panel.
        strip = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Metrics.M)
        strip.setLayout(layout)
        for label, value in fields:
            item = QLabel("%s  %s" % (label, value))
            item.setWordWrap(True)
            style = []
            if bold:
                style.append("font-weight: bold;")
            if muted:
                style.append("color: #888888; font-size: 11px;")
            if style:
                item.setStyleSheet(" ".join(style))
            layout.addWidget(item)
        layout.addStretch(1)
        return strip

    def visitTable(self, view):
        # §18.8 — the generic table. ⭐ It renders any plugin's MonitorRecord (columns + rows) with no
        # plugin-specific knowledge; formatting is per column, declared by the plugin, because the host
        # cannot know that a rate wants four decimals and a frame count wants none.
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QAbstractItemView, QSizePolicy
        if view.title:
            title = QLabel(view.title)
            title.setStyleSheet("font-weight: bold;")
            self.__layout.addWidget(title)
        labels = view.headerLabels()
        rows = view.textRows()
        table = QTableWidget(len(rows), len(labels))
        table.setHorizontalHeaderLabels(labels)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        for rowIndex, cells in enumerate(rows):
            for columnIndex, text in enumerate(cells):
                item = QTableWidgetItem(text)
                alignment = view.columns[columnIndex].get("align", "right")
                item.setTextAlignment((Qt.AlignmentFlag.AlignRight if alignment == "right"
                                       else Qt.AlignmentFlag.AlignLeft) | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(rowIndex, columnIndex, item)
        table.resizeColumnsToContents()
        table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.__layout.addWidget(table, 1)
        self.__expandingContent = True
        if view.caption:
            caption = QLabel(view.caption)
            caption.setWordWrap(True)
            caption.setStyleSheet("color: #888888; font-size: 11px;")
            self.__layout.addWidget(caption)

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
