from base.Singleton import Singleton
from logic.spectral.util.SpectrallineUtil import SpectralLineUtil
from model.databaseEntity.spectral.device import SpectrometerCalibrationProfile


class SpectrometerCalibrationProfileUtil(Singleton):

    def initializeSpectrometerCalibrationProfile(self,spectrometerCalibrationProfile:SpectrometerCalibrationProfile):
        if len(spectrometerCalibrationProfile.spectralLines)==0:
            spectralLines = list(SpectralLineUtil().sortSpectralLinesByNanometers(
                list(SpectralLineUtil().getSpectralLinesByNames().values())).values())
            spectrometerCalibrationProfile.spectralLines=spectralLines
        return