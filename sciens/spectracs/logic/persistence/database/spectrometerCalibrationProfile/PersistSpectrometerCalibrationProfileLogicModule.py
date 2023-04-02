from sciens.spectracs.model.databaseEntity.DbBase import session_factory
from sciens.spectracs.model.databaseEntity.spectral.device.calibration.SpectrometerCalibrationProfile import \
    SpectrometerCalibrationProfile


class PersistSpectrometerCalibrationProfileLogicModule:

    def saveSpectrometerCalibrationProfile(self, spectrometerCalibrationProfile: SpectrometerCalibrationProfile):
        session = session_factory()
        session.add(spectrometerCalibrationProfile)
        session.commit()
