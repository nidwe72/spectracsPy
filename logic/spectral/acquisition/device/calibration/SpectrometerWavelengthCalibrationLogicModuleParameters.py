from model.signal.SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal import \
    SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal


class SpectrometerWavelengthCalibrationLogicModuleParameters:
    pass

    __videoSignal: SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal

    @property
    def videoSignal(self):
        return self.__videoSignal

    @videoSignal.setter
    def videoSignal(self, videoSignal):
        self.__videoSignal = videoSignal
