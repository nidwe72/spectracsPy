from chromos.base.Singleton import Singleton
from chromos.spectracs.logic.persistence.database.applicationConfig.PersistApplicationConfigLogicModule import \
    PersistApplicationConfigLogicModule
from chromos.spectracs.model.databaseEntity.application.ApplicationConfig import ApplicationConfig


class ApplicationConfigUtil(Singleton):

    def getApplicationConfig(self)->ApplicationConfig:
        result = PersistApplicationConfigLogicModule().getApplicationConfig()
        if result is None:
            result=ApplicationConfig()
            PersistApplicationConfigLogicModule().saveEntity(result)
        return result
