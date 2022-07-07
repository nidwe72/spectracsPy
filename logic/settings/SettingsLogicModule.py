from logic.model.util.spectrometerSensor.SpectrometerSensorUtil import SpectrometerSensorUtil
from logic.persistence.database.spectrometerSensor.PersistSpectrometerSensorLogicModule import \
    PersistSpectrometerSensorLogicModule
from logic.persistence.database.spectrometerSensor.PersistenceParametersGetSpectrometerSensors import \
    PersistenceParametersGetSpectrometerSensors
from model.databaseEntity.spectral.device.SpectrometerProfile import SpectrometerProfile
import typing

from model.databaseEntity.spectral.device.SpectrometerSensor import SpectrometerSensor


class SettingsLogicModule:

    def getSupportedSpectrometerSensors(self)->typing.Dict[str, SpectrometerSensor]:

        persistSpectrometerSensorLogicModule=PersistSpectrometerSensorLogicModule()
        persistenceParametersGetSpectrometerSensors=PersistenceParametersGetSpectrometerSensors()
        persistedSpectrometerSensors=persistSpectrometerSensorLogicModule.getSpectrometerSensors(persistenceParametersGetSpectrometerSensors)

        result={}

        microdiaDevice=SpectrometerSensor()
        microdiaDevice.codeName = "ThunderOptics"
        microdiaDevice.name = "Microdia 0c45:6366"
        microdiaDevice.description = "Thunder optics"
        microdiaDevice.vendorId="0c45"
        microdiaDevice.vendorName = "Microdia"
        microdiaDevice.modelId = "6366"
        result[microdiaDevice.name]=microdiaDevice

        sonixDevice=SpectrometerSensor()
        sonixDevice.name = "Sonix 0c45:6366"
        sonixDevice.codeName = "Spectracs InVision Mars"
        sonixDevice.description = "Waveshare"
        sonixDevice.vendorId="0c45"
        sonixDevice.vendorName = "Sonix"
        sonixDevice.modelId = "7777"
        result[sonixDevice.name]=sonixDevice

        hardwareId=SpectrometerSensorUtil.getHardwareId(microdiaDevice)
        print(hardwareId)













        return result

