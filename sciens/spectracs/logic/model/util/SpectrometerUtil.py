from typing import Dict, List

from base.Singleton import Singleton
from sciens.spectracs.logic.model.util.SpectrometerStyleUtil import SpectrometerStyleUtil
from sciens.spectracs.logic.model.util.SpectrometerVendorUtil import SpectrometerVendorUtil
from sciens.spectracs.logic.model.util.spectrometerSensor.SpectrometerSensorUtil import SpectrometerSensorUtil
from sciens.spectracs.logic.persistence.database.spectrometer.PersistSpectrometerLogicModule import PersistSpectrometerLogicModule
from sciens.spectracs.logic.persistence.database.spectrometer.PersistenceParametersGetSpectrometers import \
    PersistenceParametersGetSpectrometers
from sciens.spectracs.model.databaseEntity.spectral.device.Spectrometer import Spectrometer
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerSensorCodeName import SpectrometerSensorCodeName
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerStyleId import SpectrometerStyleId
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerVendorId import SpectrometerVendorId


class SpectrometerUtil(Singleton):

    def getSpectrometers(self) -> Dict[str, Spectrometer]:

        transientEntities = self.getTransientSpectrometers()

        persistLogicModule = PersistSpectrometerLogicModule()

        # todo:performance
        # do not load always load all entities
        persistenceParameters = PersistenceParametersGetSpectrometers()

        entitiesByIds = persistLogicModule.getSpectrometers(persistenceParameters)

        entitiesByNames = self.getEntitiesByNames(entitiesByIds)

        result = {}

        for entityName, entity in transientEntities.items():
            persistedEntity = entitiesByNames.get(entityName)

            if persistedEntity is None:
                persistLogicModule.saveSpectrometer(entity)
                result[self.getName(entity)] = entity
                continue
            else:
                result[self.getName(entity)] = persistedEntity

        return result

    def getTransientSpectrometers(self) -> Dict[str, Spectrometer]:

        result = {}

        spectrometerSpectracsPhantomVirtuaxSlightHaze = Spectrometer()
        spectrometerSpectracsPhantomVirtuaxSlightHaze.spectrometerVendor = \
            SpectrometerVendorUtil().getSpectrometerVendorWithId(SpectrometerVendorId.SPECTRACS)
        spectrometerSpectracsPhantomVirtuaxSlightHaze.spectrometerSensor = \
            SpectrometerSensorUtil().getSensorByCodeName(SpectrometerSensorCodeName.VIRTUAX)
        spectrometerSpectracsPhantomVirtuaxSlightHaze.spectrometerStyle = \
            SpectrometerStyleUtil().getSpectrometerStyleWithId(SpectrometerStyleId.SLIGHT_HAZE)
        spectrometerSpectracsPhantomVirtuaxSlightHaze.spectrometerSensorCodeName = SpectrometerSensorCodeName.VIRTUAX
        spectrometerSpectracsPhantomVirtuaxSlightHaze.modelName = 'Phantom'
        result[self.getName(spectrometerSpectracsPhantomVirtuaxSlightHaze)] = \
            spectrometerSpectracsPhantomVirtuaxSlightHaze

        spectrometerSpectracsInvisionExaktaGreenGold = Spectrometer()
        spectrometerSpectracsInvisionExaktaGreenGold.spectrometerVendor = \
            SpectrometerVendorUtil().getSpectrometerVendorWithId(SpectrometerVendorId.SPECTRACS)
        spectrometerSpectracsInvisionExaktaGreenGold.spectrometerStyle = \
            SpectrometerStyleUtil().getSpectrometerStyleWithId(SpectrometerStyleId.GREEN_GOLD)
        spectrometerSpectracsInvisionExaktaGreenGold.spectrometerSensor = \
            SpectrometerSensorUtil().getSensorByCodeName(SpectrometerSensorCodeName.EXAKTA)
        spectrometerSpectracsInvisionExaktaGreenGold.modelName = 'InVision'
        result[self.getName(spectrometerSpectracsInvisionExaktaGreenGold)] = \
            spectrometerSpectracsInvisionExaktaGreenGold

        spectrometerSpectracsInLightAutomatGreenGold = Spectrometer()
        spectrometerSpectracsInLightAutomatGreenGold.spectrometerVendor = \
            SpectrometerVendorUtil().getSpectrometerVendorWithId(SpectrometerVendorId.SPECTRACS)
        spectrometerSpectracsInLightAutomatGreenGold.spectrometerSensor = \
            SpectrometerSensorUtil().getSensorByCodeName(SpectrometerSensorCodeName.AUTOMAT)
        spectrometerSpectracsInLightAutomatGreenGold.spectrometerStyle = \
            SpectrometerStyleUtil().getSpectrometerStyleWithId(SpectrometerStyleId.GREEN_GOLD)
        spectrometerSpectracsInLightAutomatGreenGold.spectrometerSensorCodeName = SpectrometerSensorCodeName.AUTOMAT
        spectrometerSpectracsInLightAutomatGreenGold.modelName = 'InLight'
        result[self.getName(spectrometerSpectracsInLightAutomatGreenGold)] = \
            spectrometerSpectracsInLightAutomatGreenGold

        return result

    def getName(self,spectrometer:Spectrometer):
        result=""
        result+=spectrometer.spectrometerVendor.vendorId
        result+= " "
        result+= spectrometer.modelName
        result+= " "
        result+= spectrometer.spectrometerSensor.codeName
        result+= " "
        result+= spectrometer.spectrometerStyle.styleId
        return result

    def getEntityViewName(self,spectrometer:Spectrometer):
        result=""
        result+=spectrometer.spectrometerVendor.vendorName
        result+= " "
        result+= spectrometer.modelName
        result+= " "
        result+= spectrometer.spectrometerSensor.codeName
        result+= " "
        result+= spectrometer.spectrometerStyle.styleName
        return result


    def getEntitiesByNames(self, entitiesByIds:Dict[str, Spectrometer]):
        result={}
        for entityId, entity in entitiesByIds.items():
            result[self.getName(entity)]=entity
        return result

    def getSpectrometersHavingSensorConnected(self)->List[Spectrometer]:
        result:List[Spectrometer]=[]

        spectrometers = SpectrometerUtil().getSpectrometers()

        for spectrometerId, spectrometer in spectrometers.items():
            spectrometerSensor = SpectrometerSensorUtil().getSensorByCodeName(spectrometer.spectrometerSensor.codeName)
            if spectrometerSensor is not None:
                isSensorConnected = SpectrometerSensorUtil().isSensorConnected(spectrometerSensor)
                if isSensorConnected:
                    result.append(spectrometer)
        return result



