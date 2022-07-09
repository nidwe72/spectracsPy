from logic.model.util.spectrometerSensor.SpectrometerSensorUtil import SpectrometerSensorUtil
from logic.persistence.database.spectrometerSensor.PersistSpectrometerSensorLogicModule import \
    PersistSpectrometerSensorLogicModule
from logic.persistence.database.spectrometerSensor.PersistenceParametersGetSpectrometerSensors import \
    PersistenceParametersGetSpectrometerSensors
from model.databaseEntity.spectral.device import Spectrometer
from model.databaseEntity.spectral.device.SpectrometerSensor import SpectrometerSensor
from model.databaseEntity.spectral.device.SpectrometerSensorCodeName import SpectrometerSensorCodeName
import typing




class SettingsLogicModule:

    def getSupportedSpectrometerSensors(self)->typing.Dict[str, SpectrometerSensor]:

        persistSpectrometerSensorLogicModule=PersistSpectrometerSensorLogicModule()
        persistenceParametersGetSpectrometerSensors=PersistenceParametersGetSpectrometerSensors()
        persistedSpectrometerSensors=persistSpectrometerSensorLogicModule.getSpectrometerSensors(persistenceParametersGetSpectrometerSensors)

        result={}

        microdiaDevice=SpectrometerSensor()
        microdiaDevice.codeName = SpectrometerSensorCodeName.AUTOMAT
        microdiaDevice.name = "Microdia 0c45:6366"
        microdiaDevice.description = "Thunder optics"
        microdiaDevice.vendorId="0c45"
        microdiaDevice.sellerName = "ThunderOptics"
        microdiaDevice.vendorName = "Microdia"
        microdiaDevice.modelId = "6366"
        result[microdiaDevice.codeName]=microdiaDevice

        # elp8KDevice=SpectrometerSensor()
        # elp8KDevice.name = "Sonix 0c45:6366"
        # elp8KDevice.codeName = SpectrometerSensorCodeName.EXAKTA
        # elp8KDevice.description = "Waveshare"
        # elp8KDevice.vendorId="0c45"
        # elp8KDevice.vendorName = "Sonix"
        # elp8KDevice.modelId = "7777"
        # result[elp8KDevice.name]=elp8KDevice

        hardwareId=SpectrometerSensorUtil.getHardwareId(microdiaDevice)
        print(hardwareId)

    def getSpectrometers(self) -> typing.Dict[str, Spectrometer]:

        result = {}

        spectrometerSpectracsInvisionExaktaGreenGold=Spectrometer()
        spectrometerSpectracsInvisionExaktaGreenGold.vendorId = 'Spectracs';
        spectrometerSpectracsInvisionExaktaGreenGold.produceId='InVision-EXAKTA-GreenGold'
        spectrometerSpectracsInvisionExaktaGreenGold.vendorName='Spectracs'
        spectrometerSpectracsInvisionExaktaGreenGold.modelName = 'InVision'
        spectrometerSpectracsInvisionExaktaGreenGold.codeName='GreenGold'
        spectrometerSpectracsInvisionExaktaGreenGold.spectrometerSensorCodeName=SpectrometerSensorCodeName.EXAKTA;
        spectrometerSpectracsInvisionExaktaGreenGold.spectrometerSensor=\
            SpectrometerSensorUtil.getSensorByCodeName(SpectrometerSensorCodeName.EXAKTA)

        result[spectrometerSpectracsInvisionExaktaGreenGold.vendorId+':'+spectrometerSpectracsInvisionExaktaGreenGold.produceId]=\
            spectrometerSpectracsInvisionExaktaGreenGold

        spectrometerSpectracsILightAutomatGreenGold=Spectrometer()
        spectrometerSpectracsILightAutomatGreenGold.vendorId = 'Spectracs';
        spectrometerSpectracsILightAutomatGreenGold.produceId='InLight-AUTOMAT-GreenGold'
        spectrometerSpectracsILightAutomatGreenGold.vendorName='Spectracs'
        spectrometerSpectracsILightAutomatGreenGold.modelName = 'InLight'
        spectrometerSpectracsILightAutomatGreenGold.codeName='GreenGold'
        spectrometerSpectracsILightAutomatGreenGold.spectrometerSensorCodeName=SpectrometerSensorCodeName.AUTOMAT;
        spectrometerSpectracsILightAutomatGreenGold.spectrometerSensor=\
            SpectrometerSensorUtil.getSensorByCodeName(SpectrometerSensorCodeName.AUTOMAT)


        result[spectrometerSpectracsILightAutomatGreenGold.vendorId+':'+spectrometerSpectracsILightAutomatGreenGold.produceId]=\
            spectrometerSpectracsILightAutomatGreenGold


        return result

