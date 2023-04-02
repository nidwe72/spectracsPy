from typing import Dict

from sciens.spectracs.logic.persistence.database.spectrometerSensor.PersistenceParametersGetSpectrometerSensors import \
    PersistenceParametersGetSpectrometerSensors
from sciens.spectracs.model.databaseEntity.DbBase import session_factory
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerSensor import SpectrometerSensor


class PersistSpectrometerSensorLogicModule:

    def saveSpectrometerSensor(self,spectrometerSensor:SpectrometerSensor):
        session = session_factory()
        session.add(spectrometerSensor)
        session.commit()

    def getSpectrometerSensors(self,persistenceParametersGetSpectrometerSensors:PersistenceParametersGetSpectrometerSensors) -> Dict[int,SpectrometerSensor]:

        ids = persistenceParametersGetSpectrometerSensors.getIds()
        session = session_factory()
        resultList = session.query(SpectrometerSensor).all()
        result:Dict[int,SpectrometerSensor] = {}
        for spectrometerSensor in resultList:
            result[spectrometerSensor.id]=spectrometerSensor
        return result
