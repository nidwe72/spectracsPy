from base.Singleton import Singleton
from logic.persistence.database.applicationConfig.PersistApplicationConfigLogicModule import \
    PersistApplicationConfigLogicModule
from model.databaseEntity.application.ApplicationConfig import ApplicationConfig


class ApplicationConfigUtil(Singleton):

    def getApplicationConfig(self)->ApplicationConfig:
        result = PersistApplicationConfigLogicModule().getApplicationConfig()
        if result is None:
            result=ApplicationConfig()
            PersistApplicationConfigLogicModule().saveApplicationConfig(result)
        return result
