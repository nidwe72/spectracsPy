from typing import Dict
from sciens.base.Singleton import Singleton
from sciens.spectracs.logic.persistence.database.spectralLineMasterData.PersistSpectralLineMasterDataLogicModule import \
    PersistSpectralLineMasterDataLogicModule
from sciens.spectracs.logic.persistence.database.spectralLineMasterData.PersistenceParametersGetSpectralLineMasterDatas import \
    PersistenceParametersGetSpectralLineMasterDatas
from sciens.spectracs.model.databaseEntity.spectral.device.SpectralLineMasterData import SpectralLineMasterData
from sciens.spectracs.model.databaseEntity.spectral.device.SpectralLineMasterDataColorName import SpectralLineMasterDataColorName


class SpectralLineMasterDataUtil(Singleton):

    def createTransientSpectralLineMasterDatasByNames(self):

        # https: // www.johndcook.com / wavelength_to_RGB.html
        # https://www.color-name.com/hex/00f6ff

        transientSpectralLineMasterData = {}

        #[CFL#1]
        spectralLineMercuryFrenchViolet = SpectralLineMasterData()
        spectralLineMercuryFrenchViolet.name = SpectralLineMasterDataColorName.MERCURY_FRENCH_VIOLET
        spectralLineMercuryFrenchViolet.colorName = 'french violet'
        spectralLineMercuryFrenchViolet.mainColorName = 'violet'
        spectralLineMercuryFrenchViolet.nanometer = 405.4
        spectralLineMercuryFrenchViolet.light = 'CFL'
        spectralLineMercuryFrenchViolet.intensity = 0
        spectralLineMercuryFrenchViolet.description = 'mercury'
        transientSpectralLineMasterData[
            spectralLineMercuryFrenchViolet.name] = spectralLineMercuryFrenchViolet

        #[CFL#2]
        spectralLineMercuryBlue = SpectralLineMasterData()
        spectralLineMercuryBlue.name = SpectralLineMasterDataColorName.MERCURY_BLUE
        spectralLineMercuryBlue.colorName = 'blue'
        spectralLineMercuryBlue.mainColorName = 'blue'
        spectralLineMercuryBlue.nanometer = 436.6
        spectralLineMercuryBlue.light = 'CFL'
        spectralLineMercuryBlue.intensity = 0
        spectralLineMercuryBlue.description = 'mercury'
        transientSpectralLineMasterData[spectralLineMercuryBlue.name] = spectralLineMercuryBlue

        #[CFL#3]
        spectralLineTerbiumAqua = SpectralLineMasterData()
        spectralLineTerbiumAqua.name = SpectralLineMasterDataColorName.TERBIUM_AQUA
        spectralLineTerbiumAqua.colorName = 'aqua'
        spectralLineTerbiumAqua.mainColorName = 'cyan'
        spectralLineTerbiumAqua.nanometer = 487.7
        spectralLineTerbiumAqua.light = 'CFL'
        spectralLineTerbiumAqua.intensity = 0
        spectralLineTerbiumAqua.description = 'terbium from Tb3+'
        transientSpectralLineMasterData[spectralLineTerbiumAqua.name] = spectralLineTerbiumAqua

        #[CFL#4]
        spectralLineMercuryMangoGreenLeft = SpectralLineMasterData()
        spectralLineMercuryMangoGreenLeft.name = SpectralLineMasterDataColorName.MERCURY_MANGO_GREEN_LEFT
        spectralLineMercuryMangoGreenLeft.colorName = 'mango green 1'
        spectralLineMercuryMangoGreenLeft.mainColorName = 'green'
        spectralLineMercuryMangoGreenLeft.nanometer = 542.4
        spectralLineMercuryMangoGreenLeft.light = 'CFL'
        spectralLineMercuryMangoGreenLeft.intensity = 0
        spectralLineMercuryMangoGreenLeft.description = 'terbium from Tb3+'
        transientSpectralLineMasterData[spectralLineMercuryMangoGreenLeft.name] = spectralLineMercuryMangoGreenLeft

        # [CFL#5]
        spectralLineMercuryMangoGreen = SpectralLineMasterData()
        spectralLineMercuryMangoGreen.name = SpectralLineMasterDataColorName.MERCURY_MANGO_GREEN
        spectralLineMercuryMangoGreen.colorName = 'mango green'
        spectralLineMercuryMangoGreen.mainColorName = 'green'
        spectralLineMercuryMangoGreen.nanometer = 546.5
        spectralLineMercuryMangoGreen.light = 'CFL'
        spectralLineMercuryMangoGreen.intensity = 0
        spectralLineMercuryMangoGreen.description = 'mercury'
        transientSpectralLineMasterData[spectralLineMercuryMangoGreen.name] = spectralLineMercuryMangoGreen

        # [CFL#6]
        spectralLinMercuryOrTerbiumLemonGlacier = SpectralLineMasterData()
        spectralLinMercuryOrTerbiumLemonGlacier.name = SpectralLineMasterDataColorName.MERCURY_OR_TERBIUM_LEMON_GLACIER
        spectralLinMercuryOrTerbiumLemonGlacier.colorName = 'lemon glacier'
        spectralLinMercuryOrTerbiumLemonGlacier.mainColorName = 'yellow'
        spectralLinMercuryOrTerbiumLemonGlacier.nanometer = 577.7
        spectralLinMercuryOrTerbiumLemonGlacier.light = 'CFL'
        spectralLinMercuryOrTerbiumLemonGlacier.intensity = 0
        spectralLinMercuryOrTerbiumLemonGlacier.description = 'likely terbium from Tb3+ or mercury'
        transientSpectralLineMasterData[spectralLinMercuryOrTerbiumLemonGlacier.name] = spectralLinMercuryOrTerbiumLemonGlacier

        # [CFL#7]
        spectralLinMercuryOrTerbiumYellow = SpectralLineMasterData()
        spectralLinMercuryOrTerbiumYellow.name = SpectralLineMasterDataColorName.MERCURY_OR_TERBIUM_YELLOW
        spectralLinMercuryOrTerbiumYellow.colorName = 'yellow'
        spectralLinMercuryOrTerbiumYellow.mainColorName = 'yellow'
        spectralLinMercuryOrTerbiumYellow.nanometer = 580.2
        spectralLinMercuryOrTerbiumYellow.light = 'CFL'
        spectralLinMercuryOrTerbiumYellow.intensity = 0
        spectralLinMercuryOrTerbiumYellow.description = 'mercury or terbium'
        transientSpectralLineMasterData[spectralLinMercuryOrTerbiumYellow.name] = spectralLinMercuryOrTerbiumYellow

        # [CFL#8]
        spectralLinTerbiumOrEuropiumYellowRose = SpectralLineMasterData()
        spectralLinTerbiumOrEuropiumYellowRose.name = SpectralLineMasterDataColorName.TERBIUM_OR_EUROPIUM_YELLOW_ROSE
        spectralLinTerbiumOrEuropiumYellowRose.colorName = 'yellow rose'
        spectralLinTerbiumOrEuropiumYellowRose.mainColorName = 'yellow'
        spectralLinTerbiumOrEuropiumYellowRose.nanometer = 584.0
        spectralLinTerbiumOrEuropiumYellowRose.light = 'CFL'
        spectralLinTerbiumOrEuropiumYellowRose.intensity = 0
        spectralLinTerbiumOrEuropiumYellowRose.description = 'possibly terbium from Tb3+ or europium in Eu+3:Y2O3'
        transientSpectralLineMasterData[spectralLinTerbiumOrEuropiumYellowRose.name] = spectralLinTerbiumOrEuropiumYellowRose

        # [CFL#9]
        spectralLinEuropiumMiddleYellow = SpectralLineMasterData()
        spectralLinEuropiumMiddleYellow.name = SpectralLineMasterDataColorName.EUROPIUM_MIDDLE_YELLOW
        spectralLinEuropiumMiddleYellow.colorName = 'middle yellow'
        spectralLinEuropiumMiddleYellow.mainColorName = 'yellow'
        spectralLinEuropiumMiddleYellow.nanometer = 587.6
        spectralLinEuropiumMiddleYellow.light = 'CFL'
        spectralLinEuropiumMiddleYellow.intensity = 0
        spectralLinEuropiumMiddleYellow.description = 'europium in Eu + 3: Y2O3'
        transientSpectralLineMasterData[spectralLinEuropiumMiddleYellow.name] = spectralLinEuropiumMiddleYellow

        # [CFL#10]
        spectralLinEuropiumCyberYellow = SpectralLineMasterData()
        spectralLinEuropiumCyberYellow.name = SpectralLineMasterDataColorName.EUROPIUM_CYBER_YELLOW
        spectralLinEuropiumCyberYellow.colorName = 'cyber yellow'
        spectralLinEuropiumCyberYellow.mainColorName = 'yellow'
        spectralLinEuropiumCyberYellow.nanometer = 593.4
        spectralLinEuropiumCyberYellow.light = 'CFL'
        spectralLinEuropiumCyberYellow.intensity = 0
        spectralLinEuropiumCyberYellow.description = 'europium in Eu + 3: Y2O3'
        transientSpectralLineMasterData[spectralLinEuropiumCyberYellow.name] = spectralLinEuropiumCyberYellow

        # [CFL#11]
        spectralLinEuropiumAmber = SpectralLineMasterData()
        spectralLinEuropiumAmber.name = SpectralLineMasterDataColorName.EUROPIUM_AMBER
        spectralLinEuropiumAmber.colorName = 'amber'
        spectralLinEuropiumAmber.mainColorName = 'yellow'
        spectralLinEuropiumAmber.nanometer = 599.7
        spectralLinEuropiumAmber.light = 'CFL'
        spectralLinEuropiumAmber.intensity = 0
        spectralLinEuropiumAmber.description = 'europium in Eu + 3: Y2O3'
        transientSpectralLineMasterData[spectralLinEuropiumAmber.name] = spectralLinEuropiumAmber

        # [CFL#12]
        spectralLinEuropiumVividGamboge = SpectralLineMasterData()
        spectralLinEuropiumVividGamboge.name = SpectralLineMasterDataColorName.EUROPIUM_VIVID_GAMBOGE
        spectralLinEuropiumVividGamboge.colorName = 'vivid gamboge'
        spectralLinEuropiumVividGamboge.mainColorName = 'orange'
        spectralLinEuropiumVividGamboge.nanometer = 611.6
        spectralLinEuropiumVividGamboge.light = 'CFL'
        spectralLinEuropiumVividGamboge.intensity = 0
        spectralLinEuropiumVividGamboge.description = 'europium in Eu + 3: Y2O3'
        transientSpectralLineMasterData[spectralLinEuropiumVividGamboge.name] = spectralLinEuropiumVividGamboge

        # [CFL#13]
        spectralLineTerbiumVividOrange = SpectralLineMasterData()
        spectralLineTerbiumVividOrange.name = SpectralLineMasterDataColorName.TERBIUM_VIVID_ORANGE
        spectralLineTerbiumVividOrange.colorName = 'vivid orange'
        spectralLineTerbiumVividOrange.mainColorName = 'orange'
        spectralLineTerbiumVividOrange.nanometer = 625.7
        spectralLineTerbiumVividOrange.light = 'CFL'
        spectralLineTerbiumVividOrange.intensity = 0
        spectralLineTerbiumVividOrange.description = 'likely terbium from Tb3+'
        transientSpectralLineMasterData[spectralLineTerbiumVividOrange.name] = spectralLineTerbiumVividOrange

        # [CFL#14]
        spectralLinEuropiumInternationalOrange = SpectralLineMasterData()
        spectralLinEuropiumInternationalOrange.name = SpectralLineMasterDataColorName.EUROPIUM_INTERNATIONAL_ORANGE
        spectralLinEuropiumInternationalOrange.colorName = 'International Orange'
        spectralLinEuropiumInternationalOrange.mainColorName = 'orange'
        spectralLinEuropiumInternationalOrange.nanometer = 631.1
        spectralLinEuropiumInternationalOrange.light = 'CFL'
        spectralLinEuropiumInternationalOrange.intensity = 0
        spectralLinEuropiumInternationalOrange.description = 'europium in Eu + 3: Y2O3'
        transientSpectralLineMasterData[
            spectralLinEuropiumInternationalOrange.name] = spectralLinEuropiumInternationalOrange

        # [CFL#15]
        spectralLinEuropiumRed = SpectralLineMasterData()
        spectralLinEuropiumRed.name = SpectralLineMasterDataColorName.EUROPIUM_RED
        spectralLinEuropiumRed.colorName = 'red'
        spectralLinEuropiumRed.mainColorName = 'red'
        spectralLinEuropiumRed.nanometer = 650.8
        spectralLinEuropiumRed.light = 'CFL'
        spectralLinEuropiumRed.intensity = 0
        spectralLinEuropiumRed.description = 'europium in Eu + 3: Y2O3'
        transientSpectralLineMasterData[spectralLinEuropiumRed.name] = spectralLinEuropiumRed

        # [CFL#16]
        spectralLinEuropiumRedFar660 = SpectralLineMasterData()
        spectralLinEuropiumRedFar660.name = SpectralLineMasterDataColorName.EUROPIUM_RED_FAR_660
        spectralLinEuropiumRedFar660.colorName = 'far red 660'
        spectralLinEuropiumRedFar660.mainColorName = 'red'
        spectralLinEuropiumRedFar660.nanometer = 662.6
        spectralLinEuropiumRedFar660.light = 'CFL'
        spectralLinEuropiumRedFar660.intensity = 0
        spectralLinEuropiumRedFar660.description = 'europium in Eu + 3: Y2O3'
        transientSpectralLineMasterData[spectralLinEuropiumRedFar660.name] = spectralLinEuropiumRedFar660

        # [CFL#17]
        spectralLinEuropiumRedFar680 = SpectralLineMasterData()
        spectralLinEuropiumRedFar680.name = SpectralLineMasterDataColorName.EUROPIUM_RED_FAR_680
        spectralLinEuropiumRedFar680.colorName = 'far red 660'
        spectralLinEuropiumRedFar680.mainColorName = 'red'
        spectralLinEuropiumRedFar680.nanometer = 687.7
        spectralLinEuropiumRedFar680.light = 'CFL'
        spectralLinEuropiumRedFar680.intensity = 0
        spectralLinEuropiumRedFar680.description = 'likely europium in Eu + 3: Y2O3'
        transientSpectralLineMasterData[spectralLinEuropiumRedFar680.name] = spectralLinEuropiumRedFar680

        # [CFL#18]
        spectralLinEuropiumRedFar690 = SpectralLineMasterData()
        spectralLinEuropiumRedFar690.name = SpectralLineMasterDataColorName.EUROPIUM_RED_FAR_690
        spectralLinEuropiumRedFar690.colorName = 'far red 690'
        spectralLinEuropiumRedFar690.mainColorName = 'red'
        spectralLinEuropiumRedFar690.nanometer = 693.7
        spectralLinEuropiumRedFar690.light = 'CFL'
        spectralLinEuropiumRedFar690.intensity = 0
        spectralLinEuropiumRedFar690.description = 'likely europium in Eu+3:Y2O3'
        transientSpectralLineMasterData[spectralLinEuropiumRedFar690.name] = spectralLinEuropiumRedFar690

        # [CFL#19]
        spectralLinEuropiumRedFar700 = SpectralLineMasterData()
        spectralLinEuropiumRedFar700.name = SpectralLineMasterDataColorName.EUROPIUM_RED_FAR_700
        spectralLinEuropiumRedFar700.colorName = 'far red 700'
        spectralLinEuropiumRedFar700.mainColorName = 'red'
        spectralLinEuropiumRedFar700.nanometer = 707
        spectralLinEuropiumRedFar700.light = 'CFL'
        spectralLinEuropiumRedFar700.intensity = 0
        spectralLinEuropiumRedFar700.description = 'likely europium in Eu+3:Y2O3'
        transientSpectralLineMasterData[spectralLinEuropiumRedFar700.name] = spectralLinEuropiumRedFar700

        # [CFL#20]
        spectralLinEuropiumRedFar710 = SpectralLineMasterData()
        spectralLinEuropiumRedFar710.name = SpectralLineMasterDataColorName.EUROPIUM_RED_FAR_710
        spectralLinEuropiumRedFar710.colorName = 'far red 710'
        spectralLinEuropiumRedFar710.mainColorName = 'red'
        spectralLinEuropiumRedFar710.nanometer = 712.3
        spectralLinEuropiumRedFar710.light = 'CFL'
        spectralLinEuropiumRedFar710.intensity = 0
        spectralLinEuropiumRedFar710.description = 'likely europium in Eu+3:Y2O3'
        transientSpectralLineMasterData[spectralLinEuropiumRedFar710.name] = spectralLinEuropiumRedFar710

        # [CFL#21]
        spectralLineArgonRedFar760 = SpectralLineMasterData()
        spectralLineArgonRedFar760.name = SpectralLineMasterDataColorName.ARGON_RED_FAR_760
        spectralLineArgonRedFar760.colorName = 'far red 760'
        spectralLineArgonRedFar760.mainColorName = 'red'
        spectralLineArgonRedFar760.nanometer = 760.0
        spectralLineArgonRedFar760.light = 'CFL'
        spectralLineArgonRedFar760.intensity = 0
        spectralLineArgonRedFar760.description = 'likely argon'
        transientSpectralLineMasterData[spectralLineArgonRedFar760.name] = spectralLineArgonRedFar760

        # [CFL#22]
        spectralLineArgonRedFar810 = SpectralLineMasterData()
        spectralLineArgonRedFar810.name = SpectralLineMasterDataColorName.ARGON_RED_FAR_810
        spectralLineArgonRedFar810.colorName = 'far red 760'
        spectralLineArgonRedFar810.mainColorName = 'red'
        spectralLineArgonRedFar810.nanometer = 811.0
        spectralLineArgonRedFar810.light = 'CFL'
        spectralLineArgonRedFar810.intensity = 0
        spectralLineArgonRedFar810.description = 'likely argon'
        transientSpectralLineMasterData[spectralLineArgonRedFar810.name] = spectralLineArgonRedFar810

        transientSpectralLineMasterData[
            SpectralLineMasterDataColorName.MERCURY_FRENCH_VIOLET].intensity = 56.75320988323069
        transientSpectralLineMasterData[SpectralLineMasterDataColorName.MERCURY_BLUE].intensity = 90.29270028910736
        transientSpectralLineMasterData[SpectralLineMasterDataColorName.TERBIUM_AQUA].intensity = 120.32584679648508
        transientSpectralLineMasterData[
            SpectralLineMasterDataColorName.MERCURY_MANGO_GREEN].intensity = 207.62219062846142
        transientSpectralLineMasterData[
            SpectralLineMasterDataColorName.MERCURY_OR_TERBIUM_LEMON_GLACIER].intensity = 97.33694045865732
        transientSpectralLineMasterData[
            SpectralLineMasterDataColorName.EUROPIUM_MIDDLE_YELLOW].intensity = 113.23782055267287
        transientSpectralLineMasterData[
            SpectralLineMasterDataColorName.EUROPIUM_CYBER_YELLOW].intensity = 102.17695614687108
        transientSpectralLineMasterData[SpectralLineMasterDataColorName.EUROPIUM_AMBER].intensity = 72.30732109981693
        transientSpectralLineMasterData[
            SpectralLineMasterDataColorName.EUROPIUM_INTERNATIONAL_ORANGE].intensity = 213.96991040605366
        transientSpectralLineMasterData[
            SpectralLineMasterDataColorName.EUROPIUM_VIVID_GAMBOGE].intensity = 56.689921606840784

        return transientSpectralLineMasterData


    def createSpectralLineMasterDatasByNames(self):

        transientSpectralLineMasterData=self.createTransientSpectralLineMasterDatasByNames()

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
            else:
                result[spectralLineMasterData.name] = persistedSpectralLineMasterData

        return result

    def sortSpectralLineMasterDatasByNames(self, spectralLineMasterDatasByIds: Dict[int, SpectralLineMasterData]):
        result = {}
        for spectralLineMasterDataId, spectralLineMasterData in spectralLineMasterDatasByIds.items():
            result[spectralLineMasterData.name] = spectralLineMasterData
        return result

    def getSpectralLineMasterDataByName(self,spectralLineMasterDataName)->SpectralLineMasterData:
        spectralLineMasterDatasByNames = self.createSpectralLineMasterDatasByNames()
        result=spectralLineMasterDatasByNames[spectralLineMasterDataName]
        return result

