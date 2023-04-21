from typing import Dict

from sciens.base.Singleton import Singleton
from sciens.spectracs.logic.persistence.database.spectrometerStyle.PersistSpectrometerStyleLogicModule import \
    PersistSpectrometerStyleLogicModule
from sciens.spectracs.logic.persistence.database.spectrometerStyle.PersistenceParametersGetSpectrometerStyles import \
    PersistenceParametersGetSpectrometerStyles
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerStyle import SpectrometerStyle
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerStyleId import SpectrometerStyleId
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerStyleName import SpectrometerStyleName


class SpectrometerStyleUtil(Singleton):

    def getSpectrometerStyles(self) -> Dict[str, SpectrometerStyle]:
        transientSpectrometerStyles = {}

        styleGreenGold = SpectrometerStyle()
        styleGreenGold.styleId = SpectrometerStyleId.GREEN_GOLD
        styleGreenGold.styleName = SpectrometerStyleName.GREEN_GOLD
        transientSpectrometerStyles[SpectrometerStyleId.GREEN_GOLD] = styleGreenGold

        styleSlightHaze = SpectrometerStyle()
        styleSlightHaze.styleId = SpectrometerStyleId.SLIGHT_HAZE
        styleSlightHaze.styleName = SpectrometerStyleName.SLIGHT_HAZE
        transientSpectrometerStyles[SpectrometerStyleId.SLIGHT_HAZE] = styleSlightHaze


        persistSpectrometerStyleLogicModule = PersistSpectrometerStyleLogicModule()

        # todo:performace
        # do not load always load all SpectrometerStyle/s
        persistenceParametersGetSpectrometerStyles = PersistenceParametersGetSpectrometerStyles()

        spectrometerStylesByIds = persistSpectrometerStyleLogicModule.getSpectrometerStyles(
            persistenceParametersGetSpectrometerStyles)

        spectrometerStylesByStyleIds = self.sortSpectrometerStylesByStyleIds(spectrometerStylesByIds)

        result = {}

        for spectrometerStyleStyleId, spectrometerStyle in transientSpectrometerStyles.items():
            persistedSpectrometerStyle = spectrometerStylesByStyleIds.get(spectrometerStyleStyleId)
            if persistedSpectrometerStyle is None:
                persistSpectrometerStyleLogicModule.saveSpectrometerStyle(spectrometerStyle)
                result[spectrometerStyle.styleId ] = spectrometerStyle
                # print(spectrometerStyleId)
                continue
            else:
                result[spectrometerStyle.styleId] = persistedSpectrometerStyle

        return result


    def getSpectrometerStyleWithId(self,spectrometerStyleId) -> SpectrometerStyle:
        spectrometerStyles = SpectrometerStyleUtil().getSpectrometerStyles()
        result = spectrometerStyles.get(spectrometerStyleId)
        return result

    def sortSpectrometerStylesByStyleIds(self,spectrometerStylesByIds:Dict[int,SpectrometerStyle]):
        result={}
        for spectrometerStyleId, spectrometerStyle in spectrometerStylesByIds.items():
            result[spectrometerStyle.styleId]=spectrometerStyle
        return result

