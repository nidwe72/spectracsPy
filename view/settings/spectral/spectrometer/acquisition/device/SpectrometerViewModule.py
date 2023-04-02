from sciens.spectracs.model.databaseEntity.spectral.device.Spectrometer import Spectrometer
from view.application.widgets.page.PageLineEdit import PageLineEdit
from view.application.widgets.page.PageWidget import PageWidget
from view.settings.spectral.spectrometer.acquisition.device.SpectrometerSensorViewModule import \
    SpectrometerSensorViewModule
from view.settings.spectral.spectrometer.acquisition.device.SpectrometerStyleViewModule import \
    SpectrometerStyleViewModule
from view.settings.spectral.spectrometer.acquisition.device.SpectrometerVendorViewModule import \
    SpectrometerVendorViewModule


class SpectrometerViewModule(PageWidget):

    model:Spectrometer=None
    spectrometerModelNameComponent:PageLineEdit = None
    spectrometerSensorViewModule:SpectrometerSensorViewModule = None
    spectrometerVendorViewModule:SpectrometerVendorViewModule = None
    spectrometerStyleViewModule:SpectrometerStyleViewModule = None

    def getMainContainerWidgets(self):
        result= super().getMainContainerWidgets()

        self.spectrometerModelNameComponent=PageLineEdit()
        self.spectrometerModelNameComponent.setReadOnly(True)
        result['spectrometerModelNameComponent'] =self.createLabeledComponent("Product name", self.spectrometerModelNameComponent)

        self.spectrometerSensorViewModule=SpectrometerSensorViewModule(self)
        self.spectrometerSensorViewModule.setMaximumHeight(120)
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
