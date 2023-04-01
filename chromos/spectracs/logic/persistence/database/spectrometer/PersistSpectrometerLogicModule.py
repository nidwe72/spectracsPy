from typing import Dict

from chromos.spectracs.logic.persistence.database.spectrometer.PersistenceParametersGetSpectrometers import \
    PersistenceParametersGetSpectrometers
from chromos.spectracs.model.databaseEntity.DbBase import session_factory
from chromos.spectracs.model.databaseEntity.spectral.device.Spectrometer import Spectrometer


class PersistSpectrometerLogicModule:

    def saveSpectrometer(self, spectrometer: Spectrometer):
        session = session_factory()
        session.add(spectrometer)
        session.commit()

    def getSpectrometers(self, persistenceParametersGetSpectrometers: PersistenceParametersGetSpectrometers) -> Dict[
        int, Spectrometer]:
        ids = persistenceParametersGetSpectrometers.getIds()
        session = session_factory()
        resultList = session.query(Spectrometer).all()
        result: Dict[int, Spectrometer] = {}
        for spectrometer in resultList:
            result[spectrometer.id] = spectrometer
        return result
