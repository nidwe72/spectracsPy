from operator import attrgetter
from typing import Dict
from typing import List

from base.Singleton import Singleton
from logic.spectral.util.SpectralColorUtil import SpectralColorUtil
from logic.spectral.util.SpectralLineMasterDataUtil import SpectralLineMasterDataUtil
from model.databaseEntity.spectral.device.SpectralLine import SpectralLine
from model.databaseEntity.spectral.device.SpectralLineMasterDataColorName import SpectralLineMasterDataColorName


class SpectralLineUtil(Singleton):

    def createSpectralLinesByNames(self):

        # https: // www.johndcook.com / wavelength_to_RGB.html
        # https://www.color-name.com/hex/00f6ff

        spectralLineMasterDatas=SpectralLineMasterDataUtil().createSpectralLineMasterDatasByNames()

        result = {}

        spectralLineMercuryFrenchViolet = SpectralLine()
        spectralLineMercuryFrenchViolet.spectralLineMasterData=spectralLineMasterDatas[SpectralLineMasterDataColorName.MERCURY_FRENCH_VIOLET];
        spectralLineMercuryFrenchViolet.color = SpectralColorUtil().wavelengthToColor(spectralLineMercuryFrenchViolet.spectralLineMasterData.nanometer)
        result[spectralLineMercuryFrenchViolet.spectralLineMasterData.name] = spectralLineMercuryFrenchViolet

        spectralLineMercuryBlue = SpectralLine()
        spectralLineMercuryBlue.spectralLineMasterData = spectralLineMasterDatas[SpectralLineMasterDataColorName.MERCURY_BLUE];
        spectralLineMercuryBlue.color = SpectralColorUtil().wavelengthToColor(
            spectralLineMercuryBlue.spectralLineMasterData.nanometer)
        result[spectralLineMercuryBlue.spectralLineMasterData.name] = spectralLineMercuryBlue

        spectralLineTerbiumAqua = SpectralLine()
        spectralLineTerbiumAqua.spectralLineMasterData = spectralLineMasterDatas[SpectralLineMasterDataColorName.TERBIUM_AQUA];
        spectralLineTerbiumAqua.color = SpectralColorUtil().wavelengthToColor(spectralLineTerbiumAqua.spectralLineMasterData.nanometer)
        result[spectralLineTerbiumAqua.spectralLineMasterData.name] = spectralLineTerbiumAqua

        spectralLineMercuryMangoGreen = SpectralLine()
        spectralLineMercuryMangoGreen.spectralLineMasterData = spectralLineMasterDatas[SpectralLineMasterDataColorName.MERCURY_MANGO_GREEN];
        spectralLineMercuryMangoGreen.color = SpectralColorUtil().wavelengthToColor(
            spectralLineMercuryMangoGreen.spectralLineMasterData.nanometer)
        result[spectralLineMercuryMangoGreen.spectralLineMasterData.name] = spectralLineMercuryMangoGreen

        spectralLinEuropiumMiddleYellow = SpectralLine()
        spectralLinEuropiumMiddleYellow.spectralLineMasterData = spectralLineMasterDatas[SpectralLineMasterDataColorName.EUROPIUM_MIDDLE_YELLOW];
        spectralLinEuropiumMiddleYellow.color = SpectralColorUtil().wavelengthToColor(
            spectralLinEuropiumMiddleYellow.spectralLineMasterData.nanometer)
        result[spectralLinEuropiumMiddleYellow.spectralLineMasterData.name] = spectralLinEuropiumMiddleYellow

        spectralLinEuropiumCyberYellow = SpectralLine()
        spectralLinEuropiumCyberYellow.spectralLineMasterData = spectralLineMasterDatas[SpectralLineMasterDataColorName.EUROPIUM_CYBER_YELLOW];
        spectralLinEuropiumCyberYellow.color = SpectralColorUtil().wavelengthToColor(
            spectralLinEuropiumCyberYellow.spectralLineMasterData.nanometer)
        result[spectralLinEuropiumCyberYellow.spectralLineMasterData.name] = spectralLinEuropiumCyberYellow

        spectralLinEuropiumAmber = SpectralLine()
        spectralLinEuropiumAmber.spectralLineMasterData = spectralLineMasterDatas[SpectralLineMasterDataColorName.EUROPIUM_AMBER];
        spectralLinEuropiumAmber.color = SpectralColorUtil().wavelengthToColor(
            spectralLinEuropiumAmber.spectralLineMasterData.nanometer)
        result[spectralLinEuropiumAmber.spectralLineMasterData.name] = spectralLinEuropiumAmber

        spectralLinEuropiumVividGamboge = SpectralLine()
        spectralLinEuropiumVividGamboge.spectralLineMasterData = spectralLineMasterDatas[SpectralLineMasterDataColorName.EUROPIUM_VIVID_GAMBOGE];
        spectralLinEuropiumVividGamboge.color = SpectralColorUtil().wavelengthToColor(
            spectralLinEuropiumVividGamboge.spectralLineMasterData.nanometer)
        result[spectralLinEuropiumVividGamboge.spectralLineMasterData.name] = spectralLinEuropiumVividGamboge

        spectralLinEuropiumInternationalOrange = SpectralLine()
        spectralLinEuropiumInternationalOrange.spectralLineMasterData = spectralLineMasterDatas[SpectralLineMasterDataColorName.EUROPIUM_INTERNATIONAL_ORANGE];
        spectralLinEuropiumInternationalOrange.color = SpectralColorUtil().wavelengthToColor(
            spectralLinEuropiumInternationalOrange.spectralLineMasterData.nanometer)
        result[spectralLinEuropiumInternationalOrange.spectralLineMasterData.name] = spectralLinEuropiumInternationalOrange

        spectralLinEuropiumRed = SpectralLine()
        spectralLinEuropiumRed.spectralLineMasterData = spectralLineMasterDatas[SpectralLineMasterDataColorName.EUROPIUM_RED];
        spectralLinEuropiumRed.color = SpectralColorUtil().wavelengthToColor(
            spectralLinEuropiumRed.spectralLineMasterData.nanometer)
        result[spectralLinEuropiumRed.spectralLineMasterData.name] = spectralLinEuropiumRed

        return result

    def getSpectralLinesByProminences(self, spectralLinesCollection: List[SpectralLine]) -> Dict[float, SpectralLine]:

        result: Dict[float, SpectralLine] = {}
        for spectralLine in spectralLinesCollection:
            result[spectralLine.prominence] = spectralLine
        return result

    def sortSpectralLinesByProminences(self, spectralLinesCollection: List[SpectralLine]) -> List[SpectralLine]:
        spectralLinesCollection.sort(key=attrgetter('prominence'), reverse=True)
        return spectralLinesCollection

    def sortSpectralLinesByPixelIndices(self, spectralLinesCollection: List[SpectralLine]) -> Dict[int, SpectralLine]:
        spectralLinesCollection.sort(key=attrgetter('pixelIndex'), reverse=False)
        result = {}
        for spectralLine in spectralLinesCollection:
            result[spectralLine.pixelIndex] = spectralLine
        return result

    def sortSpectralLinesByNanometers(self, spectralLinesCollection: List[SpectralLine]) -> Dict[int, SpectralLine]:
        spectralLinesCollection.sort(key=attrgetter('spectralLineMasterData.nanometer'), reverse=False)
        result = {}
        for spectralLine in spectralLinesCollection:
            result[spectralLine.spectralLineMasterData.nanometer] = spectralLine
        return result

    def sortSpectralLinesByNames(self, spectralLinesCollection: List[SpectralLine]) -> Dict[int, SpectralLine]:
        spectralLinesCollection.sort(key=attrgetter('spectralLineMasterData.name'), reverse=False)
        result = {}
        for spectralLine in spectralLinesCollection:
            result[spectralLine.spectralLineMasterData.name] = spectralLine
        return result

    def getPixelIndices(self, spectralLinesCollection: List[SpectralLine]) -> List[int]:
        result = []
        for spectralLine in spectralLinesCollection:
            result.append(spectralLine.pixelIndex)
        return result

    def getNanometers(self, spectralLinesCollection: List[SpectralLine]) -> List[float]:
        result = []
        for spectralLine in spectralLinesCollection:
            result.append(spectralLine.spectralLineMasterData.nanometer)
        return result


