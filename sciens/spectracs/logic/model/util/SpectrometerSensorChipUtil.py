from typing import Dict
from sciens.base.Singleton import Singleton
from sciens.spectracs.logic.persistence.database.spectrometerSensorChip.PersistSpectrometerSensorChipLogicModule import \
    PersistSpectrometerSensorChipLogicModule
from sciens.spectracs.logic.persistence.database.spectrometerSensorChip.PersistenceParametersGetSpectrometerSensorChips import \
    PersistenceParametersGetSpectrometerSensorChips
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerSensorChip import SpectrometerSensorChip


class SpectrometerSensorChipUtil(Singleton):


    def getSpectrometerSensorChips(self) -> Dict[str, SpectrometerSensorChip]:
        transientEntities = {}

        sensorSpectracspectracs9999=SpectrometerSensorChip()
        sensorSpectracspectracs9999.vendorName="Spectracs"
        sensorSpectracspectracs9999.productName = "9999"
        transientEntities[sensorSpectracspectracs9999.vendorName+'_'+sensorSpectracspectracs9999.productName]=sensorSpectracspectracs9999

        sensorSonySonix6366=SpectrometerSensorChip()
        sensorSonySonix6366.vendorName="Sonix"
        sensorSonySonix6366.productName = "6366"
        transientEntities[sensorSonySonix6366.vendorName+'_'+sensorSonySonix6366.productName]=sensorSonySonix6366

        sensorSonyImx1234=SpectrometerSensorChip()
        sensorSonyImx1234.vendorName="Sony"
        sensorSonyImx1234.productName = "IMX1234"
        transientEntities[sensorSonyImx1234.vendorName+'_'+sensorSonyImx1234.productName]=sensorSonyImx1234

        persistLogicModule = PersistSpectrometerSensorChipLogicModule()

        # todo:performance
        # do not load always load all entities
        persistenceParameters = PersistenceParametersGetSpectrometerSensorChips()

        entitiesByIds = persistLogicModule.getSpectrometerSensorChips(
            persistenceParameters)

        entitiesByCompoundKeys = self.getEntitiesByCompoundIds(entitiesByIds)

        result = {}

        for entityCompoundId, entity in transientEntities.items():
            persistedEntity = entitiesByCompoundKeys.get(entityCompoundId)
            if persistedEntity is None:
                persistLogicModule.saveSpectrometerSensorChip(entity)
                result[entity.vendorName+'_'+entity.productName ] = entity
                continue
            else:
                result[entity.vendorName+'_'+entity.productName] = persistedEntity

        return result

    def getEntitiesByCompoundIds(self, entitiesByIds:Dict[int, SpectrometerSensorChip]):
        result={}
        for entityId, entity in entitiesByIds.items():
            result[entity.vendorName+'_'+entity.productName]=entity
        return result

