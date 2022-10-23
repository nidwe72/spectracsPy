from PyQt6.QtWidgets import QLineEdit

from logic.appliction.style.Polisher import Polisher
from model.databaseEntity.spectral.device import SpectrometerVendor
from view.application.widgets.page.PageLineEdit import PageLineEdit
from view.application.widgets.page.PageWidget import PageWidget


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
