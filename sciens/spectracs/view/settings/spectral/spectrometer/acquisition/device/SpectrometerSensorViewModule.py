from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QTextEdit

from sciens.spectracs.logic.model.util.spectrometerSensor.SpectrometerSensorUtil import SpectrometerSensorUtil
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerSensor import SpectrometerSensor
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget


class SpectrometerSensorViewModule(PageWidget):
    model: SpectrometerSensor = None
    spectrometerSensorTextEdit:QTextEdit = None

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        self.spectrometerSensorTextEdit=QTextEdit()
        result['spectrometerSensorTextEdit']=self.spectrometerSensorTextEdit

        return result

    def setModel(self, model: SpectrometerSensor):
        self.model = model

        if model is not None:
            markup = SpectrometerSensorUtil().getSensorMarkup(model)

            markupDocument = QTextDocument()
            markupDocument.setHtml(markup)

            self.spectrometerSensorTextEdit.setDocument(markupDocument)

    def getModel(self, model: SpectrometerSensor):
        return self.model

    def _getPageTitle(self):
        return "Spectrometer sensor"
