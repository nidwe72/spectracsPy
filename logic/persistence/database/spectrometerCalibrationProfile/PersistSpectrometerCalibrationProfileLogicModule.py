from model.databaseEntity.DbBase import session_factory
from model.databaseEntity.spectral.device import SpectrometerCalibrationProfile


class PersistSpectrometerCalibrationProfileLogicModule:

    def saveSpectrometerCalibrationProfile(self, spectrometerCalibrationProfile: SpectrometerCalibrationProfile):
        session = session_factory()
        session.add(spectrometerCalibrationProfile)
        session.commit()
