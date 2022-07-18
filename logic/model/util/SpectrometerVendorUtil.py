from typing import Dict

from base.Singleton import Singleton
from logic.persistence.database.PersistSpectrometerVendorLogicModule import PersistSpectrometerVendorLogicModule
from logic.persistence.database.PersistenceParametersGetSpectrometerVendors import \
    PersistenceParametersGetSpectrometerVendors
from model.databaseEntity.spectral.device import SpectrometerVendor
from model.databaseEntity.spectral.device.SpectrometerVendorId import SpectrometerVendorId
from model.databaseEntity.spectral.device.SpectrometerVendorName import SpectrometerVendorName


class SpectrometerVendorUtil(Singleton):
    persistedSpectrometerVendors:Dict[int,SpectrometerVendor]= {}

    def getSpectrometerVendors(self) -> Dict[str, SpectrometerVendor]:

        transientSpectrometerVendors={}

        vendorSpectracs=SpectrometerVendor()
        vendorSpectracs.vendorId=SpectrometerVendorId.SPECTRACS
        vendorSpectracs.vendorName = SpectrometerVendorName.SPECTRACS
        transientSpectrometerVendors[SpectrometerVendorId.SPECTRACS.name]=vendorSpectracs

        persistSpectrometerVendorLogicModule=PersistSpectrometerVendorLogicModule()

        #todo:performace
        #do not load always load all SpectrometerVendor/s
        persistenceParametersGetSpectrometerVendors=PersistenceParametersGetSpectrometerVendors()

        spectrometerVendorsByIds=persistSpectrometerVendorLogicModule.getSpectrometerVendors(persistenceParametersGetSpectrometerVendors)

        spectrometerVendorsByVendorIds=self.sortSpectrometerVendorsByVendorIds(spectrometerVendorsByIds)

        result={}

        for spectrometerVendorVendorId, spectrometerVendor in transientSpectrometerVendors.items():
            persistedSpectrometerVendor=spectrometerVendorsByVendorIds.get(spectrometerVendorVendorId)
            if persistedSpectrometerVendor is None:
                persistSpectrometerVendorLogicModule.saveSpectrometerVendor(spectrometerVendor)
                spectrometerVendorId=spectrometerVendor.id
                result[spectrometerVendor.id] = spectrometerVendor
                print(spectrometerVendorId)
                continue
            else:
                result[spectrometerVendor.id]=persistedSpectrometerVendor

        return result

    def getSpectrometerVendorWithId(self,spectrometerVendorId)->SpectrometerVendor:
        spectrometerVendors=self.getSpectrometerVendors()
        spectrometerVendors=self.sortSpectrometerVendorsByVendorIds(spectrometerVendors)

        result=spectrometerVendors.get(spectrometerVendorId)
        return result


    def sortSpectrometerVendorsByVendorIds(self,spectrometerVendorsByIds:Dict[int,SpectrometerVendor]):
        result={}
        for spectrometerVendorId, spectrometerVendor in spectrometerVendorsByIds.items():
            result[spectrometerVendor.vendorId]=spectrometerVendor
        return result

