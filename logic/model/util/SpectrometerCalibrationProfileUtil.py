from base.Singleton import Singleton
from logic.spectral.util.SpectrallineUtil import SpectralLineUtil
from model.databaseEntity.spectral.device import SpectrometerCalibrationProfile
from model.databaseEntity.spectral.device.SpectralLine import SpectralLine


class SpectrometerCalibrationProfileUtil(Singleton):

    def initializeSpectrometerCalibrationProfile(self,spectrometerCalibrationProfile:SpectrometerCalibrationProfile):
        if len(spectrometerCalibrationProfile.spectralLines)==0:
            spectralLines = list(SpectralLineUtil().sortSpectralLinesByNanometers(
                list(SpectralLineUtil().createSpectralLinesByNames().values())).values())
            spectrometerCalibrationProfile.spectralLines=spectralLines
        return

    def getMatchingSpectralLine(self,spectrometerCalibrationProfile:SpectrometerCalibrationProfile, spectralLine:SpectralLine)->SpectralLine:
        result=SpectralLineUtil().sortSpectralLinesByNanometers(spectrometerCalibrationProfile.getSpectralLines())[spectralLine.nanometer]
        return result

    def getSpectralLineWithName(self,spectrometerCalibrationProfile:SpectrometerCalibrationProfile,name:str)->SpectralLine:
        for spectralLine in spectrometerCalibrationProfile.getSpectralLines():
            if spectralLine.name==name:
                result=spectralLine
                break
        return result
