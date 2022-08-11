from typing import Dict

from logic.persistence.database.spectrometer.PersistenceParametersGetSpectrometers import \
    PersistenceParametersGetSpectrometers
from model.databaseEntity.DbBase import session_factory
from model.databaseEntity.spectral.device import Spectrometer


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
