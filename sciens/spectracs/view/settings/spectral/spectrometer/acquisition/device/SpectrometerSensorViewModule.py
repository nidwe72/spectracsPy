from PySide6 import QtCore
from PySide6.QtGui import QBrush
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView

from sciens.spectracs.logic.application.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerSensor import SpectrometerSensor
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget


class SpectrometerSensorViewModule(PageWidget):
    """The sensor is shown as two real, read-only tables (the sensor + its chip), replacing the old
    editable QTextEdit-HTML. This resolves two audit burdens at once (R4/R5): the tables are no longer
    tap-to-edit (NoEditTriggers/NoSelection/NoFocus), they fit 412 dp (columns Stretch, shared QSS),
    and the HTML's literal `border: 1px solid red` (the Android red gridlines) is gone. Layout mirrors
    the original: table 1 = codeName caption + Code name/Vendor/Vendor id/Model id; table 2 = the chip.
    See docs/SPEC_phone_width_responsiveness.md."""

    ROW_HEIGHT = 30
    compactMainContainer = True  # B2: top-pack the two fixed-height tables

    model: SpectrometerSensor = None
    sensorTable: QTableWidget = None
    chipTable: QTableWidget = None

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        self.sensorTable = QTableWidget(3, 4)
        self._configureReadOnlyTable(self.sensorTable, rowCount=3)
        result['sensorTable'] = self.sensorTable

        self.chipTable = QTableWidget(1, 5)
        self._configureReadOnlyTable(self.chipTable, rowCount=1)
        result['chipTable'] = self.chipTable

        self._populate()
        return result

    def setModel(self, model: SpectrometerSensor):
        self.model = model
        self._populate()

    def getModel(self, model: SpectrometerSensor):
        return self.model

    def _getPageTitle(self):
        return "Spectrometer sensor"

    # --- table construction -------------------------------------------------

    def _configureReadOnlyTable(self, table, rowCount):
        table.horizontalHeader().setVisible(False)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setDefaultSectionSize(self.ROW_HEIGHT)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)      # not tap-to-edit
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)      # not selectable
        table.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)                      # no caret/focus ring
        table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.setFixedHeight(rowCount * self.ROW_HEIGHT + 2)  # exact content height, no empty rows

    def _makeItem(self, text, caption=False):
        item = QTableWidgetItem(text if text is not None else "")
        if caption:
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            item.setBackground(QBrush(ApplicationStyleLogicModule().getSurfaceAltColor()))
        return item

    def _populate(self):
        if self.sensorTable is None:
            return

        sensor = self.model
        codeName = sensor.codeName if sensor is not None else ""
        vendorName = sensor.vendorName if sensor is not None else ""
        vendorId = sensor.vendorId if sensor is not None else ""
        modelId = sensor.modelId if sensor is not None else ""

        chip = sensor.spectrometerSensorChip if sensor is not None else None
        chipVendor = chip.vendorName if chip is not None else ""
        chipModel = chip.productName if chip is not None else ""

        # Table 1 — sensor: caption row (codeName, spanning 4), header labels, value row.
        self.sensorTable.setSpan(0, 0, 1, 4)
        self.sensorTable.setItem(0, 0, self._makeItem(codeName, caption=True))
        for col, text in enumerate(["Code name", "Vendor", "Vendor id", "Model id"]):
            self.sensorTable.setItem(1, col, self._makeItem(text))
        for col, text in enumerate([codeName, vendorName, vendorId, modelId]):
            self.sensorTable.setItem(2, col, self._makeItem(text))

        # Table 2 — chip: "Sensor" caption cell + two label/value pairs (Vendor / Model id).
        for col, (text, caption) in enumerate([
            ("Sensor", True), ("Vendor", False), (chipVendor, False),
            ("Model id", False), (chipModel, False),
        ]):
            self.chipTable.setItem(0, col, self._makeItem(text, caption=caption))
