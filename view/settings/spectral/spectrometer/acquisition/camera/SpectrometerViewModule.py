from PyQt6.QtWidgets import QLineEdit

from model.databaseEntity.spectral.device import Spectrometer
from view.application.widgets.page.PageWidget import PageWidget
from view.settings.spectral.spectrometer.acquisition.camera.SpectrometerSensorViewModule import \
    SpectrometerSensorViewModule
from view.settings.spectral.spectrometer.acquisition.camera.SpectrometerStyleViewModule import \
    SpectrometerStyleViewModule
from view.settings.spectral.spectrometer.acquisition.camera.SpectrometerVendorViewModule import \
    SpectrometerVendorViewModule


class SpectrometerViewModule(PageWidget):

    model:Spectrometer=None
    spectrometerModelNameComponent:QLineEdit = None
    spectrometerSensorViewModule:SpectrometerSensorViewModule = None
    spectrometerVendorViewModule:SpectrometerVendorViewModule = None
    spectrometerStyleViewModule:SpectrometerStyleViewModule = None

    def getMainContainerWidgets(self):
        result= super().getMainContainerWidgets()

        self.spectrometerModelNameComponent=QLineEdit()
        result['spectrometerModelNameComponent'] =self.createLabeledComponent("Product name", self.spectrometerModelNameComponent)

        self.spectrometerSensorViewModule=SpectrometerSensorViewModule(self)
        self.spectrometerSensorViewModule.initialize()
        result['spectrometerSensorViewModule']=self.spectrometerSensorViewModule

        self.spectrometerVendorViewModule=SpectrometerVendorViewModule(self)
        self.spectrometerVendorViewModule.initialize()
        result['spectrometerVendorViewModule']=self.spectrometerVendorViewModule

        self.spectrometerStyleViewModule=SpectrometerStyleViewModule(self)
        self.spectrometerStyleViewModule.initialize()
        result['spectrometerStyleViewModule']=self.spectrometerStyleViewModule

        return result

    def setModel(self,model:Spectrometer):
        self.model=model

        self.spectrometerModelNameComponent.setText(model.modelName)
        self.spectrometerSensorViewModule.setModel(model.spectrometerSensor)
        self.spectrometerVendorViewModule.setModel(model.spectrometerVendor)
        self.spectrometerStyleViewModule.setModel(model.spectrometerStyle)

    def getModel(self,model:Spectrometer):
        return self.model

    def _getPageTitle(self):
        return "Spectrometer"
