from sciens.base.Singleton import Singleton
from sciens.spectracs.logic.spectral.util.SpectrallineUtil import SpectralLineUtil
from sciens.spectracs.model.databaseEntity.spectral.device.SpectralLine import SpectralLine
from sciens.spectracs.model.databaseEntity.spectral.device.calibration.SpectrometerCalibrationProfile import \
    SpectrometerCalibrationProfile


class SpectrometerCalibrationProfileUtil(Singleton):

    def initializeSpectrometerCalibrationProfile(self,spectrometerCalibrationProfile:SpectrometerCalibrationProfile):
        # if len(spectrometerCalibrationProfile.spectralLines)==0:
        #     spectralLines = list(SpectralLineUtil().sortSpectralLinesByNanometers(
        #         list(SpectralLineUtil().createSpectralLinesByNames().values())).values())
        #     spectrometerCalibrationProfile.spectralLines=spectralLines
        return

    def getMatchingSpectralLine(self,spectrometerCalibrationProfile:SpectrometerCalibrationProfile, spectralLine:SpectralLine)->SpectralLine:
        result=SpectralLineUtil().sortSpectralLinesByNanometers(spectrometerCalibrationProfile.getSpectralLines())[spectralLine.spectralLineMasterData.nanometer]
        return result

    def getSpectralLineWithName(self,spectrometerCalibrationProfile:SpectrometerCalibrationProfile,name:str)->SpectralLine:
        for spectralLine in spectrometerCalibrationProfile.getSpectralLines():
            if spectralLine.spectralLineMasterData.name==name:
                result=spectralLine
                break
        return result
