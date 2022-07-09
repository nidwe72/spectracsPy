import usb
import typing

from model.databaseEntity.spectral.device.SpectrometerSensor import SpectrometerSensor
from model.databaseEntity.spectral.device.SpectrometerSensorCodeName import SpectrometerSensorCodeName


class SpectrometerSensorUtil:

    @staticmethod
    def getHardwareId(spectrometerSensor:SpectrometerSensor):
        result=spectrometerSensor.vendorId+'_'+spectrometerSensor.modelId
        return result

    @staticmethod
    def isSensorConnected(spectrometerSensor:SpectrometerSensor):
        result = True
        dev = usb.core.find(idVendor=int('0x' + spectrometerSensor.vendorId, base=16),
                            idProduct=int('0x' + spectrometerSensor.modelId, base=16))

        if dev is None:
            result=False

        return result

    @staticmethod
    def getSupportedSpectrometerSensors()->typing.Dict[str, SpectrometerSensor]:

        # persistSpectrometerSensorLogicModule=PersistSpectrometerSensorLogicModule()
        # persistenceParametersGetSpectrometerSensors=PersistenceParametersGetSpectrometerSensors()
        # persistedSpectrometerSensors=persistSpectrometerSensorLogicModule.getSpectrometerSensors(persistenceParametersGetSpectrometerSensors)

        result={}

        microdiaDevice=SpectrometerSensor()
        microdiaDevice.codeName = SpectrometerSensorCodeName.AUTOMAT
        microdiaDevice.name = "Microdia 0c45:6366"
        microdiaDevice.description = "Thunder optics"
        microdiaDevice.vendorId="0c45"
        microdiaDevice.sellerName = "ThunderOptics"
        microdiaDevice.vendorName = "Microdia"
        microdiaDevice.modelId = "6366"
        microdiaDevice.sensorProductName = "IMXXXX"
        microdiaDevice.sensorVendorName = "Sony"
        result[microdiaDevice.codeName]=microdiaDevice

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


    @staticmethod
    def getSensorByCodeName(spectrometerSensorCodenName)->SpectrometerSensor:
        spectrometerSensors=SpectrometerSensorUtil.getSupportedSpectrometerSensors()
        result=spectrometerSensors.get(spectrometerSensorCodenName)
        return result

    @staticmethod
    def getSensorMarkup(spectrometerSensor: SpectrometerSensor):

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
                <td colspan="5" style="font-weight:bold;text-align: center;background-color:#404040;">%codeName%</td>
            </tr>
            <tr>
                <td width=20%>Code name</td>
                <td width=20%>Vendor</td>
                <td width=20%>Vendor id</td>
                <td width=20%>Model id</td>
                <td width=20%>Sensor</td>                
            </tr>                        
            <tr>
                <td width=20%>%codeName%</td>
                <td width=20%>%vendorName%</td>
                <td width=20%>%vendorId%</td>
                <td width=20%>%modelId%</td>
                <td width=20%>%sensorVendorName% %sensorProductName%</td>                
            </tr>
            </table>
            </body>
            '''


        html = html.replace('%vendorId%', spectrometerSensor.vendorId)
        html = html.replace('%vendorName%', spectrometerSensor.vendorName)
        html = html.replace('%modelId%', spectrometerSensor.modelId)
        html = html.replace('%codeName%', spectrometerSensor.codeName)
        html = html.replace('%sensorVendorName%', spectrometerSensor.sensorVendorName)
        html = html.replace('%sensorProductName%', spectrometerSensor.sensorProductName)

        return html
