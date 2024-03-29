from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerStyle import SpectrometerStyle
from sciens.spectracs.view.application.widgets.page.PageLineEdit import PageLineEdit
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget


class SpectrometerStyleViewModule(PageWidget):
    model: SpectrometerStyle = None
    spectrometerStyleNameComponent: PageLineEdit = None

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        self.spectrometerStyleNameComponent=PageLineEdit()
        self.spectrometerStyleNameComponent.setReadOnly(True)
        result['spectrometerStyleNameComponent']=self.createLabeledComponent("Style name", self.spectrometerStyleNameComponent)

        return result

    def setModel(self, model: SpectrometerStyle):
        self.model = model
        self.spectrometerStyleNameComponent.setText(model.styleName)

    def getModel(self, model: SpectrometerStyle):
        return self.model

    def _getPageTitle(self):
        return "Spectrometer style"
