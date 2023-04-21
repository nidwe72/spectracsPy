from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerVendor import SpectrometerVendor
from sciens.spectracs.view.application.widgets.page.PageLineEdit import PageLineEdit
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget


class SpectrometerVendorViewModule(PageWidget):
    model: SpectrometerVendor = None
    spectrometerVendorNameComponent:PageLineEdit=None

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        self.spectrometerVendorNameComponent=PageLineEdit(self)

        self.spectrometerVendorNameComponent.setReadOnly(True)
        result['spectrometerStyleNameComponent']=self.createLabeledComponent("Vendor name", self.spectrometerVendorNameComponent)

        return result

    def setModel(self, model: SpectrometerVendor):
        self.model = model
        self.spectrometerVendorNameComponent.setText(model.vendorName)

    def getModel(self, model: SpectrometerVendor):
        return self.model

    def _getPageTitle(self):
        return "Spectrometer vendor"
