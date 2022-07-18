from typing import Dict

from base.Singleton import Singleton
from model.databaseEntity.spectral.device import SpectrometerStyle
from model.databaseEntity.spectral.device.SpectrometerStyleId import SpectrometerStyleId
from model.databaseEntity.spectral.device.SpectrometerStyleName import SpectrometerStyleName


class SpectrometerStyleUtil(Singleton):

    def getSpectrometerStyles(self) -> Dict[str,SpectrometerStyle]:
        result = {}

        styleGreenGold = SpectrometerStyle()
        styleGreenGold.styleId = SpectrometerStyleId.GREEN_GOLD
        styleGreenGold.styleName = SpectrometerStyleName.GREEN_GOLD
        result[SpectrometerStyleId.GREEN_GOLD] = styleGreenGold

        return result

    def getSpectrometerStyleWithId(self,spectrometerStyleId) -> SpectrometerStyle:
        spectrometerStyles = SpectrometerStyleUtil().getSpectrometerStyles()
        result = spectrometerStyles.get(spectrometerStyleId)
        return result
