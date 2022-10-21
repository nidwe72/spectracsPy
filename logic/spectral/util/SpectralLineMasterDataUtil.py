from base.Singleton import Singleton
from logic.spectral.util.SpectralColorUtil import SpectralColorUtil
from model.databaseEntity.spectral.device.SpectralLineMasterData import SpectralLineMasterData
from model.databaseEntity.spectral.device.SpectralLineMasterDataColorName import SpectralLineMasterDataColorName


class SpectralLineMasterDataUtil(Singleton):

    def createSpectralLineMasterDatasByNames(self):

        # https: // www.johndcook.com / wavelength_to_RGB.html
        # https://www.color-name.com/hex/00f6ff

        result = {}

        spectralLineMercuryFrenchViolet = SpectralLineMasterData()
        spectralLineMercuryFrenchViolet.name = SpectralLineMasterDataColorName.MERCURY_FRENCH_VIOLET
        spectralLineMercuryFrenchViolet.colorName = 'french violet'
        spectralLineMercuryFrenchViolet.mainColorName = 'violet'
        spectralLineMercuryFrenchViolet.nanometer = 405.4
        result[
            spectralLineMercuryFrenchViolet.name] = spectralLineMercuryFrenchViolet

        spectralLineMercuryBlue = SpectralLineMasterData()
        spectralLineMercuryBlue.name = SpectralLineMasterDataColorName.MERCURY_BLUE
        spectralLineMercuryBlue.colorName = 'blue'
        spectralLineMercuryBlue.mainColorName = 'blue'
        spectralLineMercuryBlue.nanometer = 436.6
        result[spectralLineMercuryBlue.name] = spectralLineMercuryBlue

        spectralLineTerbiumAqua = SpectralLineMasterData()
        spectralLineTerbiumAqua.name = SpectralLineMasterDataColorName.TERBIUM_AQUA
        spectralLineTerbiumAqua.colorName = 'aqua'
        spectralLineTerbiumAqua.mainColorName = 'cyan'
        spectralLineTerbiumAqua.nanometer = 487.7
        result[spectralLineTerbiumAqua.name] = spectralLineTerbiumAqua

        spectralLineMercuryMangoGreen = SpectralLineMasterData()
        spectralLineMercuryMangoGreen.name = SpectralLineMasterDataColorName.MERCURY_MANGO_GREEN
        spectralLineMercuryMangoGreen.colorName = 'mango green'
        spectralLineMercuryMangoGreen.mainColorName = 'green'
        spectralLineMercuryMangoGreen.nanometer = 546.5
        result[spectralLineMercuryMangoGreen.name] = spectralLineMercuryMangoGreen

        spectralLinEuropiumMiddleYellow = SpectralLineMasterData()
        spectralLinEuropiumMiddleYellow.name = SpectralLineMasterDataColorName.EUROPIUM_MIDDLE_YELLOW
        spectralLinEuropiumMiddleYellow.colorName = 'middle yellow'
        spectralLinEuropiumMiddleYellow.mainColorName = 'yellow'
        spectralLinEuropiumMiddleYellow.nanometer = 587.6
        result[spectralLinEuropiumMiddleYellow.name] = spectralLinEuropiumMiddleYellow

        spectralLinEuropiumCyberYellow = SpectralLineMasterData()
        spectralLinEuropiumCyberYellow.name = SpectralLineMasterDataColorName.EUROPIUM_CYBER_YELLOW
        spectralLinEuropiumCyberYellow.colorName = 'cyber yellow'
        spectralLinEuropiumCyberYellow.mainColorName = 'yellow'
        spectralLinEuropiumCyberYellow.nanometer = 593.4
        result[spectralLinEuropiumCyberYellow.name] = spectralLinEuropiumCyberYellow

        spectralLinEuropiumAmber = SpectralLineMasterData()
        spectralLinEuropiumAmber.name = SpectralLineMasterDataColorName.EUROPIUM_AMBER
        spectralLinEuropiumAmber.colorName = 'amber'
        spectralLinEuropiumAmber.mainColorName = 'yellow'
        spectralLinEuropiumAmber.nanometer = 599.7
        result[spectralLinEuropiumAmber.name] = spectralLinEuropiumAmber

        spectralLinEuropiumVividGamboge = SpectralLineMasterData()
        spectralLinEuropiumVividGamboge.name = SpectralLineMasterDataColorName.EUROPIUM_VIVID_GAMBOGE
        spectralLinEuropiumVividGamboge.colorName = 'vivid gamboge'
        spectralLinEuropiumVividGamboge.mainColorName = 'orange'
        spectralLinEuropiumVividGamboge.nanometer = 611.6
        result[spectralLinEuropiumVividGamboge.name] = spectralLinEuropiumVividGamboge

        spectralLinEuropiumInternationalOrange = SpectralLineMasterData()
        spectralLinEuropiumInternationalOrange.name = SpectralLineMasterDataColorName.EUROPIUM_INTERNATIONAL_ORANGE
        spectralLinEuropiumInternationalOrange.colorName = 'International Orange'
        spectralLinEuropiumInternationalOrange.mainColorName = 'orange'
        spectralLinEuropiumInternationalOrange.nanometer = 631.1
        result[spectralLinEuropiumInternationalOrange.name] = spectralLinEuropiumInternationalOrange

        spectralLinEuropiumRed = SpectralLineMasterData()
        spectralLinEuropiumRed.name = SpectralLineMasterDataColorName.EUROPIUM_RED
        spectralLinEuropiumRed.colorName = 'red'
        spectralLinEuropiumRed.mainColorName = 'red'
        spectralLinEuropiumRed.nanometer = 650.8
        result[spectralLinEuropiumRed.name] = spectralLinEuropiumRed

        return result
