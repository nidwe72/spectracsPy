from typing import Dict

from chromos.spectracs.logic.model.util.databaseEntity.SqlUtil import SqlUtil
from chromos.spectracs.logic.persistence.database.applicationConfig.PersistApplicationConfigToSpectrometerProfileLogicModuleParameters import \
    PersistApplicationConfigToSpectrometerProfileLogicModuleParameters
from chromos.spectracs.model.databaseEntity.application.ApplicationConfigToSpectrometerProfile import \
    ApplicationConfigToSpectrometerProfile


class PersistGetApplicationConfigToSpectrometerProfilesLogicModule:

    def __init__(self, *args, **kwargs):
        self.__moduleParameters: PersistApplicationConfigToSpectrometerProfileLogicModuleParameters = None

    def getEntities(self) -> \
            Dict[str, ApplicationConfigToSpectrometerProfile]:

        moduleParameters=self.getModuleParameters()

        baseEntity = moduleParameters.getBaseEntity()
        selectStatement = SqlUtil.createSelect(baseEntity)
        result = SqlUtil.executeSelect(baseEntity, selectStatement)

        return result

    def getModuleParameters(self)->PersistApplicationConfigToSpectrometerProfileLogicModuleParameters:
        if self.__moduleParameters is None:
            self.__moduleParameters=PersistApplicationConfigToSpectrometerProfileLogicModuleParameters()
        return self.__moduleParameters