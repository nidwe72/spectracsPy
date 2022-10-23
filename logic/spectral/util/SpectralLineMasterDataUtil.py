from typing import Dict
from base.Singleton import Singleton
from logic.persistence.database.spectralLineMasterData.PersistSpectralLineMasterDataLogicModule import \
    PersistSpectralLineMasterDataLogicModule
from logic.persistence.database.spectralLineMasterData.PersistenceParametersGetSpectralLineMasterDatas import \
    PersistenceParametersGetSpectralLineMasterDatas
from logic.spectral.util.SpectralColorUtil import SpectralColorUtil
from model.databaseEntity.spectral.device.SpectralLineMasterData import SpectralLineMasterData
from model.databaseEntity.spectral.device.SpectralLineMasterDataColorName import SpectralLineMasterDataColorName


class SpectralLineMasterDataUtil(Singleton):

    def createSpectralLineMasterDatasByNames(self):

        # https: // www.johndcook.com / wavelength_to_RGB.html
        # https://www.color-name.com/hex/00f6ff

        transientSpectralLineMasterData = {}

        spectralLineMercuryFrenchViolet = SpectralLineMasterData()
        spectralLineMercuryFrenchViolet.name = SpectralLineMasterDataColorName.MERCURY_FRENCH_VIOLET
        spectralLineMercuryFrenchViolet.colorName = 'french violet'
        spectralLineMercuryFrenchViolet.mainColorName = 'violet'
        spectralLineMercuryFrenchViolet.nanometer = 405.4
        transientSpectralLineMasterData[
            spectralLineMercuryFrenchViolet.name] = spectralLineMercuryFrenchViolet

        spectralLineMercuryBlue = SpectralLineMasterData()
        spectralLineMercuryBlue.name = SpectralLineMasterDataColorName.MERCURY_BLUE
        spectralLineMercuryBlue.colorName = 'blue'
        spectralLineMercuryBlue.mainColorName = 'blue'
        spectralLineMercuryBlue.nanometer = 436.6
        transientSpectralLineMasterData[spectralLineMercuryBlue.name] = spectralLineMercuryBlue

        spectralLineTerbiumAqua = SpectralLineMasterData()
        spectralLineTerbiumAqua.name = SpectralLineMasterDataColorName.TERBIUM_AQUA
        spectralLineTerbiumAqua.colorName = 'aqua'
        spectralLineTerbiumAqua.mainColorName = 'cyan'
        spectralLineTerbiumAqua.nanometer = 487.7
        transientSpectralLineMasterData[spectralLineTerbiumAqua.name] = spectralLineTerbiumAqua

        spectralLineMercuryMangoGreen = SpectralLineMasterData()
        spectralLineMercuryMangoGreen.name = SpectralLineMasterDataColorName.MERCURY_MANGO_GREEN
        spectralLineMercuryMangoGreen.colorName = 'mango green'
        spectralLineMercuryMangoGreen.mainColorName = 'green'
        spectralLineMercuryMangoGreen.nanometer = 546.5
        transientSpectralLineMasterData[spectralLineMercuryMangoGreen.name] = spectralLineMercuryMangoGreen

        spectralLinEuropiumMiddleYellow = SpectralLineMasterData()
        spectralLinEuropiumMiddleYellow.name = SpectralLineMasterDataColorName.EUROPIUM_MIDDLE_YELLOW
        spectralLinEuropiumMiddleYellow.colorName = 'middle yellow'
        spectralLinEuropiumMiddleYellow.mainColorName = 'yellow'
        spectralLinEuropiumMiddleYellow.nanometer = 587.6
        transientSpectralLineMasterData[spectralLinEuropiumMiddleYellow.name] = spectralLinEuropiumMiddleYellow

        spectralLinEuropiumCyberYellow = SpectralLineMasterData()
        spectralLinEuropiumCyberYellow.name = SpectralLineMasterDataColorName.EUROPIUM_CYBER_YELLOW
        spectralLinEuropiumCyberYellow.colorName = 'cyber yellow'
        spectralLinEuropiumCyberYellow.mainColorName = 'yellow'
        spectralLinEuropiumCyberYellow.nanometer = 593.4
        transientSpectralLineMasterData[spectralLinEuropiumCyberYellow.name] = spectralLinEuropiumCyberYellow

        spectralLinEuropiumAmber = SpectralLineMasterData()
        spectralLinEuropiumAmber.name = SpectralLineMasterDataColorName.EUROPIUM_AMBER
        spectralLinEuropiumAmber.colorName = 'amber'
        spectralLinEuropiumAmber.mainColorName = 'yellow'
        spectralLinEuropiumAmber.nanometer = 599.7
        transientSpectralLineMasterData[spectralLinEuropiumAmber.name] = spectralLinEuropiumAmber

        spectralLinEuropiumVividGamboge = SpectralLineMasterData()
        spectralLinEuropiumVividGamboge.name = SpectralLineMasterDataColorName.EUROPIUM_VIVID_GAMBOGE
        spectralLinEuropiumVividGamboge.colorName = 'vivid gamboge'
        spectralLinEuropiumVividGamboge.mainColorName = 'orange'
        spectralLinEuropiumVividGamboge.nanometer = 611.6
        transientSpectralLineMasterData[spectralLinEuropiumVividGamboge.name] = spectralLinEuropiumVividGamboge

        spectralLinEuropiumInternationalOrange = SpectralLineMasterData()
        spectralLinEuropiumInternationalOrange.name = SpectralLineMasterDataColorName.EUROPIUM_INTERNATIONAL_ORANGE
        spectralLinEuropiumInternationalOrange.colorName = 'International Orange'
        spectralLinEuropiumInternationalOrange.mainColorName = 'orange'
        spectralLinEuropiumInternationalOrange.nanometer = 631.1
        transientSpectralLineMasterData[
            spectralLinEuropiumInternationalOrange.name] = spectralLinEuropiumInternationalOrange

        spectralLinEuropiumRed = SpectralLineMasterData()
        spectralLinEuropiumRed.name = SpectralLineMasterDataColorName.EUROPIUM_RED
        spectralLinEuropiumRed.colorName = 'red'
        spectralLinEuropiumRed.mainColorName = 'red'
        spectralLinEuropiumRed.nanometer = 650.8
        transientSpectralLineMasterData[spectralLinEuropiumRed.name] = spectralLinEuropiumRed

        persistSpectralLineMasterDataLogicModule = PersistSpectralLineMasterDataLogicModule()

        # todo:performance
        # do not load always load all SpectralLineMasterData/s
        persistenceParametersGetSpectralLineMasterDatas = PersistenceParametersGetSpectralLineMasterDatas()

        persistedSpectralLineMasterDatasByNames = persistSpectralLineMasterDataLogicModule.getSpectralLineMasterDatas(
            persistenceParametersGetSpectralLineMasterDatas)

        persistedSpectralLineMasterDatasByNames = self.sortSpectralLineMasterDatasByNames(persistedSpectralLineMasterDatasByNames)

        result = {}

        for spectralLineMasterDataName, spectralLineMasterData in transientSpectralLineMasterData.items():
            persistedSpectralLineMasterData = persistedSpectralLineMasterDatasByNames.get(spectralLineMasterDataName)
            if persistedSpectralLineMasterData is None:
                persistSpectralLineMasterDataLogicModule.saveSpectralLineMasterData(spectralLineMasterData)
                result[spectralLineMasterData.name] = spectralLineMasterData
                continue
            else:
                result[spectralLineMasterData.name] = persistedSpectralLineMasterData

        return result

    def sortSpectralLineMasterDatasByNames(self, spectralLineMasterDatasByIds: Dict[int, SpectralLineMasterData]):
        result = {}
        for spectralLineMasterDataId, spectralLineMasterData in spectralLineMasterDatasByIds.items():
            result[spectralLineMasterData.name] = spectralLineMasterData
        return result
