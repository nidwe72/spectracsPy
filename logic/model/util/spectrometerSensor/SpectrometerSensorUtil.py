from typing import Dict

import usb
from sqlalchemy import inspect

from base.Singleton import Singleton
from logic.model.util.SpectrometerSensorChipUtil import SpectrometerSensorChipUtil
from logic.persistence.database.spectrometerSensor.PersistSpectrometerSensorLogicModule import \
    PersistSpectrometerSensorLogicModule
from logic.persistence.database.spectrometerSensor.PersistenceParametersGetSpectrometerSensors import \
    PersistenceParametersGetSpectrometerSensors
from model.databaseEntity.spectral.device.SpectrometerSensor import SpectrometerSensor
from model.databaseEntity.spectral.device.SpectrometerSensorCodeName import SpectrometerSensorCodeName


class SpectrometerSensorUtil(Singleton):

    def getSpectrometerSensors(self) -> Dict[str, SpectrometerSensor]:
        transientEntities = {}

        sensorChips = SpectrometerSensorChipUtil().getSpectrometerSensorChips()

        microdiaDevice = SpectrometerSensor()
        microdiaDevice.codeName = SpectrometerSensorCodeName.AUTOMAT
        microdiaDevice.description = "Thunder optics"
        microdiaDevice.vendorId = "0c45"
        microdiaDevice.vendorName = "Microdia"
        microdiaDevice.sellerName = "ThunderOptics"

        microdiaDevice.modelId = "6366"
        microdiaDevice.spectrometerSensorChip=sensorChips['Sonix_6366']
        microdiaDevice.spectrometerSensorChipId = sensorChips['Sonix_6366'].id

        transientEntities[microdiaDevice.codeName] = microdiaDevice

        elp4KDevice = SpectrometerSensor()
        elp4KDevice.codeName = SpectrometerSensorCodeName.EXAKTA
        elp4KDevice.description = "ELP "

        elp4KDevice.vendorId = "0aaa"
        elp4KDevice.vendorName = "ELP"

        elp4KDevice.modelId = "1234"

        elp4KDevice.sellerName = "ELP"

        elp4KDevice.spectrometerSensorChip=sensorChips['Sony_IMX1234']
        elp4KDevice.spectrometerSensorChipId = sensorChips['Sony_IMX1234'].id

        transientEntities[elp4KDevice.codeName]=elp4KDevice

        persistLogicModule = PersistSpectrometerSensorLogicModule()

        # todo:performance
        # do not load always load all entities
        persistenceParameters = PersistenceParametersGetSpectrometerSensors()

        entitiesByIds = persistLogicModule.getSpectrometerSensors(
            persistenceParameters)

        entitiesByCodeNames = self.getEntitiesByCodeNames(entitiesByIds);

        result = {}

        for entityCodeName, entity in transientEntities.items():
            persistedEntity = entitiesByCodeNames.get(entityCodeName)

            if persistedEntity is None:
                persistLogicModule.saveSpectrometerSensor(entity)
                result[entity.codeName ] = entity
                continue
            else:
                result[entity.codeName] = persistedEntity

        return result

    def getEntitiesByCodeNames(self, entitiesByIds:Dict[str, SpectrometerSensor]):
        result={}
        for entityId, entity in entitiesByIds.items():
            result[entity.codeName]=entity
        return result


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


    def getSensorByCodeName(self, spectrometerSensorCodenName) -> SpectrometerSensor:
        spectrometerSensors = self.getSpectrometerSensors()
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
