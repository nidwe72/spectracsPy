from model.databaseEntity.spectral.device.SpectrometerSensor import SpectrometerSensor


class SpectrometerSensorUtil:

    @staticmethod
    def getHardwareId(spectrometerSensor:SpectrometerSensor):
        result=spectrometerSensor.vendorId+'_'+spectrometerSensor.modelId
        return result