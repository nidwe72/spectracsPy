from sciens.base.Singleton import Singleton
from sciens.spectracs.model.databaseEntity.DbBase import session_factory
from sciens.spectracs.model.databaseEntity.application.ApplicationConfig import ApplicationConfig


class PersistApplicationConfigLogicModule(Singleton):

    def getApplicationConfig(self) -> ApplicationConfig:
        session = session_factory()
        resultList = session.query(ApplicationConfig).all()
        result = next(iter(resultList), None)
        return result

    def saveEntity(self, applicationConfig: ApplicationConfig):
        session = session_factory()
        session.add(applicationConfig)
        session.commit()
