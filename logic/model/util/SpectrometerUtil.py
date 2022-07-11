import typing

from logic.model.util.SpectrometerStyleUtil import SpectrometerStyleUtil
from logic.model.util.SpectrometerVendorUtil import SpectrometerVendorUtil
from logic.model.util.spectrometerSensor.SpectrometerSensorUtil import SpectrometerSensorUtil
from model.databaseEntity.spectral.device import Spectrometer
from model.databaseEntity.spectral.device.SpectrometerSensorCodeName import SpectrometerSensorCodeName
from model.databaseEntity.spectral.device.SpectrometerStyleId import SpectrometerStyleId
from model.databaseEntity.spectral.device.SpectrometerVendorId import SpectrometerVendorId


class SpectrometerUtil:

    @staticmethod
    def getSpectrometers() -> typing.Dict[str, Spectrometer]:

        result = {}

        spectrometerSpectracsInvisionExaktaGreenGold = Spectrometer()
        spectrometerSpectracsInvisionExaktaGreenGold.spectrometerVendor = \
            SpectrometerVendorUtil.getSpectrometerVendorWithId(SpectrometerVendorId.SPECTRACS)
        spectrometerSpectracsInvisionExaktaGreenGold.vendorId = 'Spectracs';
        spectrometerSpectracsInvisionExaktaGreenGold.vendorName = 'Spectracs'
        spectrometerSpectracsInvisionExaktaGreenGold.productId = 'InVision-EXAKTA-GreenGold'
        spectrometerSpectracsInvisionExaktaGreenGold.modelName = 'InVision'
        spectrometerSpectracsInvisionExaktaGreenGold.codeName = 'GreenGold'
        spectrometerSpectracsInvisionExaktaGreenGold.spectrometerStyle=\
            SpectrometerStyleUtil.getSpectrometerStyleWithId(SpectrometerStyleId.GREEN_GOLD)
        spectrometerSpectracsInvisionExaktaGreenGold.spectrometerSensorCodeName = SpectrometerSensorCodeName.EXAKTA;
        spectrometerSpectracsInvisionExaktaGreenGold.spectrometerSensor = \
            SpectrometerSensorUtil.getSensorByCodeName(SpectrometerSensorCodeName.EXAKTA)

        result[
            spectrometerSpectracsInvisionExaktaGreenGold.vendorId + ':' + spectrometerSpectracsInvisionExaktaGreenGold.productId] = \
            spectrometerSpectracsInvisionExaktaGreenGold

        spectrometerSpectracsInLightAutomatGreenGold = Spectrometer()
        spectrometerSpectracsInLightAutomatGreenGold.spectrometerVendor = \
            SpectrometerVendorUtil.getSpectrometerVendorWithId(SpectrometerVendorId.SPECTRACS)
        spectrometerSpectracsInLightAutomatGreenGold.vendorId = 'Spectracs';
        spectrometerSpectracsInLightAutomatGreenGold.vendorName = 'Spectracs'
        spectrometerSpectracsInLightAutomatGreenGold.productId = 'InLight-AUTOMAT-GreenGold'
        spectrometerSpectracsInLightAutomatGreenGold.modelName = 'InLight'
        spectrometerSpectracsInLightAutomatGreenGold.codeName = 'GreenGold'
        spectrometerSpectracsInLightAutomatGreenGold.spectrometerStyle=\
            SpectrometerStyleUtil.getSpectrometerStyleWithId(SpectrometerStyleId.GREEN_GOLD)
        spectrometerSpectracsInLightAutomatGreenGold.spectrometerSensorCodeName = SpectrometerSensorCodeName.AUTOMAT;
        spectrometerSpectracsInLightAutomatGreenGold.spectrometerSensor = \
            SpectrometerSensorUtil.getSensorByCodeName(SpectrometerSensorCodeName.AUTOMAT)

        result[
            spectrometerSpectracsInLightAutomatGreenGold.vendorId + ':' + spectrometerSpectracsInLightAutomatGreenGold.productId] = \
            spectrometerSpectracsInLightAutomatGreenGold

        return result
