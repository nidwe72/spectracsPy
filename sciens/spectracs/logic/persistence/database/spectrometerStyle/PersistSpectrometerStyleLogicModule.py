from typing import Dict

from sciens.spectracs.logic.persistence.database.spectrometerStyle import PersistenceParametersGetSpectrometerStyles
from sciens.spectracs.model.databaseEntity.DbBase import session_factory
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerStyle import SpectrometerStyle


class PersistSpectrometerStyleLogicModule:

    def saveSpectrometerStyle(self, spectrometerStyle:SpectrometerStyle):
        session = session_factory()
        session.add(spectrometerStyle)
        session.commit()

    def getSpectrometerStyles(self,
                              persistenceParametersGetSpectrometerStyles: PersistenceParametersGetSpectrometerStyles) -> \
    Dict[int,SpectrometerStyle]:
        ids = persistenceParametersGetSpectrometerStyles.getIds()
        session = session_factory()
        resultList = session.query(SpectrometerStyle).all()

        result:Dict[int,SpectrometerStyle] = {}
        for spectrometerStyle in resultList:
            result[spectrometerStyle.id]=spectrometerStyle

        return result

