import usb
import typing

from base.Singleton import Singleton
from logic.model.util.SpectrometerSensorChipUtil import SpectrometerSensorChipUtil
from logic.persistence.database.spectrometerSensor.PersistSpectrometerSensorLogicModule import \
    PersistSpectrometerSensorLogicModule
from logic.persistence.database.spectrometerSensor.PersistenceParametersGetSpectrometerSensors import \
    PersistenceParametersGetSpectrometerSensors
from model.databaseEntity.spectral.device.SpectrometerSensor import SpectrometerSensor
from model.databaseEntity.spectral.device.SpectrometerSensorCodeName import SpectrometerSensorCodeName


class SpectrometerSensorUtil(Singleton):

    def getHardwareId(self, spectrometerSensor: SpectrometerSensor):
        result = spectrometerSensor.vendorId + '_' + spectrometerSensor.modelId
        return result

    def isSensorConnected(self, spectrometerSensor: SpectrometerSensor):
        result = True
        dev = usb.core.find(idVendor=int('0x' + spectrometerSensor.vendorId, base=16),
                            idProduct=int('0x' + spectrometerSensor.modelId, base=16))

        if dev is None:
            result = False

        return result

    def getSupportedSpectrometerSensors(self) -> typing.Dict[str, SpectrometerSensor]:
        persistSpectrometerSensorLogicModule = PersistSpectrometerSensorLogicModule()
        persistenceParametersGetSpectrometerSensors = PersistenceParametersGetSpectrometerSensors()
        persistedSpectrometerSensors = persistSpectrometerSensorLogicModule.getSpectrometerSensors(
            persistenceParametersGetSpectrometerSensors)

        sensorChips = SpectrometerSensorChipUtil().getSupportedSpectrometerSensorChips()

        result = {}

        microdiaDevice = SpectrometerSensor()
        microdiaDevice.codeName = SpectrometerSensorCodeName.AUTOMAT
        microdiaDevice.name = "Microdia 0c45:6366"
        microdiaDevice.description = "Thunder optics"
        microdiaDevice.vendorId = "0c45"
        microdiaDevice.sellerName = "ThunderOptics"
        microdiaDevice.vendorName = "Microdia"
        microdiaDevice.modelId = "6366"
        # microdiaDevice.sensorProductName = "IMXXXX"
        # microdiaDevice.sensorVendorName = "Sony"
        microdiaDevice.spectrometerSensorChip=sensorChips['Sonix_6366']

        result[microdiaDevice.codeName] = microdiaDevice

        # elp8KDevice=SpectrometerSensor()
        # elp8KDevice.name = "Sonix 0c45:6366"
        # elp8KDevice.codeName = SpectrometerSensorCodeName.EXAKTA
        # elp8KDevice.description = "Waveshare"
        # elp8KDevice.vendorId="0c45"
        # elp8KDevice.vendorName = "Sonix"
        # elp8KDevice.modelId = "7777"
        # result[elp8KDevice.name]=elp8KDevice

        # hardwareId=SpectrometerSensorUtil.getHardwareId(microdiaDevice)
        # print(hardwareId)

        return result

    def getSensorByCodeName(self, spectrometerSensorCodenName) -> SpectrometerSensor:
        spectrometerSensors = self.getSupportedSpectrometerSensors()
        result = spectrometerSensors.get(spectrometerSensorCodenName)
        return result

    def getSensorMarkup(self, spectrometerSensor: SpectrometerSensor):
        html = \
            '''            
            <style type="text/css">                
                table {
                    color: white;
                    border-width: 0px;
                    border-collapse: collapse;                    
                }               
            </style>            
            <body width=100% border=1>
            <table width=100% border=1>
            <tr>
                <td colspan="4" style="font-weight:bold;text-align: center;background-color:#404040;padding:5px;">%codeName%</td>
            </tr>
            <tr>
                <td width=25%>Code name</td>
                <td width=25%>Vendor</td>
                <td width=25%>Vendor id</td>
                <td width=25%>Model id</td>
                               
            </tr>                        
            <tr>
                <td width=25%>%codeName%</td>
                <td width=25%>%vendorName%</td>
                <td width=25%>%vendorId%</td>
                <td width=25%>%modelId%</td>                                
            </tr>
            </table>
            
            
            <table width=100% border=1>
            <tr>
                <td width=25% style="font-weight:bold;text-align: center;background-color:#404040;padding:5px;">Sensor</td>
                <td width=19%>Vendor</td>
                <td width=19%>%sensorVendorName%</td>
                <td width=19%>Model id</td>
                <td width=19%>%sensorProductName%</td>                                
            </tr>                        
            </table>
            
            
            </body>
            '''

        html = html.replace('%vendorId%', spectrometerSensor.vendorId)
        html = html.replace('%vendorName%', spectrometerSensor.vendorName)
        html = html.replace('%modelId%', spectrometerSensor.modelId)
        html = html.replace('%codeName%', spectrometerSensor.codeName)
        html = html.replace('%sensorVendorName%', spectrometerSensor.spectrometerSensorChip.vendorName)
        html = html.replace('%sensorProductName%', spectrometerSensor.spectrometerSensorChip.productName)

        return html
