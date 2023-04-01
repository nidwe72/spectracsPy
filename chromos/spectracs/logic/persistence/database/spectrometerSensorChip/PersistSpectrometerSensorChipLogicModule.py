from typing import Dict

from chromos.spectracs.logic.persistence.database.spectrometerSensorChip.PersistenceParametersGetSpectrometerSensorChips import \
    PersistenceParametersGetSpectrometerSensorChips
from chromos.spectracs.model.databaseEntity.DbBase import session_factory
from chromos.spectracs.model.databaseEntity.spectral.device.SpectrometerSensorChip import SpectrometerSensorChip


class PersistSpectrometerSensorChipLogicModule:

    def saveSpectrometerSensorChip(self, spectrometerSensorChip: SpectrometerSensorChip):
        session = session_factory()
        session.add(spectrometerSensorChip)
        session.commit()

    def getSpectrometerSensorChips(self,
                                   persistenceParametersGetSpectrometerSensorChips: PersistenceParametersGetSpectrometerSensorChips) -> \
            Dict[int, SpectrometerSensorChip]:
        ids = persistenceParametersGetSpectrometerSensorChips.getIds()
        session = session_factory()
        resultList = session.query(SpectrometerSensorChip).all()

        result: Dict[int, SpectrometerSensorChip] = {}
        for spectrometerSensorChip in resultList:
            result[spectrometerSensorChip.id] = spectrometerSensorChip

        return result
