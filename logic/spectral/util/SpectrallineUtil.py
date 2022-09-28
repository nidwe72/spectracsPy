from operator import attrgetter
from typing import Dict
from typing import List

from base.Singleton import Singleton
from logic.spectral.util.SpectralColorUtil import SpectralColorUtil
from model.databaseEntity.spectral.device.SpectralLine import SpectralLine


class SpectralLineUtil(Singleton):

    def createSpectralLinesByNames(self):

        # https: // www.johndcook.com / wavelength_to_RGB.html
        # https://www.color-name.com/hex/00f6ff

        spectralLinesByNames = {}

        spectralLineMercuryFrenchViolet = SpectralLine()
        spectralLineMercuryFrenchViolet.name = 'MercuryFrenchViolet'
        spectralLineMercuryFrenchViolet.colorName = 'french violet'
        spectralLineMercuryFrenchViolet.mainColorName = 'violet'
        spectralLineMercuryFrenchViolet.nanometer = 405.4
        spectralLineMercuryFrenchViolet.color = SpectralColorUtil().wavelengthToColor(
            spectralLineMercuryFrenchViolet.nanometer)
        spectralLinesByNames[
            spectralLineMercuryFrenchViolet.name] = spectralLineMercuryFrenchViolet

        spectralLineMercuryBlue = SpectralLine()
        spectralLineMercuryBlue.name = 'MercuryBlue'
        spectralLineMercuryBlue.colorName = 'blue'
        spectralLineMercuryBlue.mainColorName = 'blue'
        spectralLineMercuryBlue.nanometer = 436.6
        spectralLineMercuryBlue.color = SpectralColorUtil().wavelengthToColor(
            spectralLineMercuryBlue.nanometer)
        spectralLinesByNames[spectralLineMercuryBlue.name] = spectralLineMercuryBlue

        spectralLineTerbiumAqua = SpectralLine()
        spectralLineTerbiumAqua.name = 'TerbiumAqua'
        spectralLineTerbiumAqua.colorName = 'aqua'
        spectralLineTerbiumAqua.mainColorName = 'cyan'
        spectralLineTerbiumAqua.nanometer = 487.7
        spectralLineTerbiumAqua.color = SpectralColorUtil().wavelengthToColor(
            spectralLineTerbiumAqua.nanometer)
        spectralLineTerbiumAqua.color = SpectralColorUtil().wavelengthToColor(spectralLineTerbiumAqua.nanometer)
        spectralLinesByNames[spectralLineTerbiumAqua.name] = spectralLineTerbiumAqua

        spectralLineMercuryMangoGreen = SpectralLine()
        spectralLineMercuryMangoGreen.name = 'MercuryMangoGreen'
        spectralLineMercuryMangoGreen.colorName = 'mango green'
        spectralLineMercuryMangoGreen.mainColorName = 'green'
        spectralLineMercuryMangoGreen.nanometer = 546.5
        spectralLineMercuryMangoGreen.color = SpectralColorUtil().wavelengthToColor(
            spectralLineMercuryMangoGreen.nanometer)
        spectralLineMercuryMangoGreen.color = SpectralColorUtil().wavelengthToColor(
            spectralLineMercuryMangoGreen.nanometer)
        spectralLinesByNames[spectralLineMercuryMangoGreen.name] = spectralLineMercuryMangoGreen

        spectralLinEuropiumMiddleYellow = SpectralLine()
        spectralLinEuropiumMiddleYellow.name = 'EuropiumMiddleYellow'
        spectralLinEuropiumMiddleYellow.colorName = 'middle yellow'
        spectralLinEuropiumMiddleYellow.mainColorName = 'yellow'
        spectralLinEuropiumMiddleYellow.nanometer = 587.6
        spectralLinEuropiumMiddleYellow.color = SpectralColorUtil().wavelengthToColor(
            spectralLinEuropiumMiddleYellow.nanometer)
        spectralLinesByNames[spectralLinEuropiumMiddleYellow.name] = spectralLinEuropiumMiddleYellow

        spectralLinEuropiumCyberYellow = SpectralLine()
        spectralLinEuropiumCyberYellow.name = 'EuropiumCyberYellow'
        spectralLinEuropiumCyberYellow.colorName = 'cyber yellow'
        spectralLinEuropiumCyberYellow.mainColorName = 'yellow'
        spectralLinEuropiumCyberYellow.nanometer = 593.4
        spectralLinEuropiumCyberYellow.color = SpectralColorUtil().wavelengthToColor(
            spectralLinEuropiumCyberYellow.nanometer)
        spectralLinesByNames[spectralLinEuropiumCyberYellow.name] = spectralLinEuropiumCyberYellow

        spectralLinEuropiumAmber = SpectralLine()
        spectralLinEuropiumAmber.name = 'EuropiumAmber'
        spectralLinEuropiumAmber.colorName = 'amber'
        spectralLinEuropiumAmber.mainColorName = 'yellow'
        spectralLinEuropiumAmber.nanometer = 599.7
        spectralLinEuropiumAmber.color = SpectralColorUtil().wavelengthToColor(
            spectralLinEuropiumAmber.nanometer)
        spectralLinesByNames[spectralLinEuropiumAmber.name] = spectralLinEuropiumAmber

        spectralLinEuropiumVividGamboge = SpectralLine()
        spectralLinEuropiumVividGamboge.name = 'EuropiumVividGamboge'
        spectralLinEuropiumVividGamboge.colorName = 'vivid gamboge'
        spectralLinEuropiumVividGamboge.mainColorName = 'orange'
        spectralLinEuropiumVividGamboge.nanometer = 611.6
        spectralLinEuropiumVividGamboge.color = SpectralColorUtil().wavelengthToColor(
            spectralLinEuropiumVividGamboge.nanometer)
        spectralLinesByNames[spectralLinEuropiumVividGamboge.name] = spectralLinEuropiumVividGamboge

        spectralLinEuropiumInternationalOrange = SpectralLine()
        spectralLinEuropiumInternationalOrange.name = 'EuropiumInternationalOrange'
        spectralLinEuropiumInternationalOrange.colorName = 'International Orange'
        spectralLinEuropiumInternationalOrange.mainColorName = 'orange'
        spectralLinEuropiumInternationalOrange.nanometer = 631.1
        spectralLinEuropiumInternationalOrange.color = SpectralColorUtil().wavelengthToColor(
            spectralLinEuropiumInternationalOrange.nanometer)
        spectralLinesByNames[spectralLinEuropiumInternationalOrange.name] = spectralLinEuropiumInternationalOrange

        spectralLinEuropiumRed = SpectralLine()
        spectralLinEuropiumRed.name = 'EuropiumRed'
        spectralLinEuropiumRed.colorName = 'red'
        spectralLinEuropiumRed.mainColorName = 'red'
        spectralLinEuropiumRed.nanometer = 650.8
        spectralLinEuropiumRed.color = SpectralColorUtil().wavelengthToColor(
            spectralLinEuropiumRed.nanometer)
        spectralLinesByNames[spectralLinEuropiumRed.name] = spectralLinEuropiumRed

        return spectralLinesByNames

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
        spectralLinesCollection.sort(key=attrgetter('nanometer'), reverse=False)
        result = {}
        for spectralLine in spectralLinesCollection:
            result[spectralLine.nanometer] = spectralLine
        return result

    def sortSpectralLinesByNames(self, spectralLinesCollection: List[SpectralLine]) -> Dict[int, SpectralLine]:
        spectralLinesCollection.sort(key=attrgetter('name'), reverse=False)
        result = {}
        for spectralLine in spectralLinesCollection:
            result[spectralLine.name] = spectralLine
        return result

    def getPixelIndices(self, spectralLinesCollection: List[SpectralLine]) -> List[int]:
        result = []
        for spectralLine in spectralLinesCollection:
            result.append(spectralLine.pixelIndex)
        return result

    def getNanometers(self, spectralLinesCollection: List[SpectralLine]) -> List[float]:
        result = []
        for spectralLine in spectralLinesCollection:
            result.append(spectralLine.nanometer)
        return result
