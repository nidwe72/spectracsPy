from typing import Dict

from logic.persistence.database.spectrometerSensorChip.PersistenceParametersGetSpectrometerSensorChips import \
    PersistenceParametersGetSpectrometerSensorChips
from logic.persistence.database.spectrometerStyle import PersistenceParametersGetSpectrometerStyles
from model.databaseEntity.DbBase import session_factory
from model.databaseEntity.spectral.device import SpectrometerStyle
from model.databaseEntity.spectral.device.SpectrometerSensorChip import SpectrometerSensorChip


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
