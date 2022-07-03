from sqlalchemy.orm import Session

from logic.persistence.database.spectrometerSensor.PersistenceParametersGetSpectrometerSensors import \
    PersistenceParametersGetSpectrometerSensors
from model.databaseEntity.DbBase import session_factory
from model.databaseEntity.spectral.device.SpectrometerSensor import SpectrometerSensor


class PersistSpectrometerSensorLogicModule:

    def saveSpectrometerSensor(self,spectrometerSensor:SpectrometerSensor):
        session = session_factory()
        session.add(spectrometerSensor)
        session.commit()

    def getSpectrometerSensors(self,persistenceParametersGetSpectrometerSensors:PersistenceParametersGetSpectrometerSensors):
        ids = persistenceParametersGetSpectrometerSensors.getIds()
        session = session_factory()
        result=session.query(SpectrometerSensor).all()
        return result


