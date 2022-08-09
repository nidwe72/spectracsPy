import typing
from base.Singleton import Singleton
from model.databaseEntity.spectral.device.SpectrometerSensorChip import SpectrometerSensorChip


class SpectrometerSensorChipUtil(Singleton):

    def getSupportedSpectrometerSensorChips(self) -> typing.Dict[str, SpectrometerSensorChip]:

        result = {}

        sensorSonySonix6366=SpectrometerSensorChip()
        sensorSonySonix6366.vendorName="Sonix"
        sensorSonySonix6366.productName = "6366"

        result[sensorSonySonix6366.vendorName+'_'+sensorSonySonix6366.productName]=sensorSonySonix6366

        return result
