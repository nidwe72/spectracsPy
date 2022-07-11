from typing import Dict

from model.databaseEntity.spectral.device import SpectrometerVendor
from model.databaseEntity.spectral.device.SpectrometerVendorId import SpectrometerVendorId
from model.databaseEntity.spectral.device.SpectrometerVendorName import SpectrometerVendorName


class SpectrometerVendorUtil:

    @staticmethod
    def getSpectrometerVendors()->Dict[str,SpectrometerVendor]:
        result={}

        vendorSpectracs=SpectrometerVendor()
        vendorSpectracs.vendorId=SpectrometerVendorId.SPECTRACS
        vendorSpectracs.vendorName = SpectrometerVendorName.SPECTRACS
        result[SpectrometerVendorId.SPECTRACS.name]=vendorSpectracs

        return result

    @staticmethod
    def getSpectrometerVendorWithId(spectrometerVendorId)->SpectrometerVendor:
        spectrometerVendors=SpectrometerVendorUtil.getSpectrometerVendors()
        result=spectrometerVendors.get(spectrometerVendorId)
        return result