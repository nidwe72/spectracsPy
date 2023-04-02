from sciens.spectracs.model.databaseEntity.application.ApplicationConfigToSpectrometerProfile import \
    ApplicationConfigToSpectrometerProfile

class PersistApplicationConfigToSpectrometerProfileLogicModuleParameters:

    def __init__(self, *args, **kwargs):
        self.__baseEntity: ApplicationConfigToSpectrometerProfile = None

    def getBaseEntity(self) -> ApplicationConfigToSpectrometerProfile:
        if self.__baseEntity is None:
            self.__baseEntity = ApplicationConfigToSpectrometerProfile()
        return self.__baseEntity

    def setBaseEntity(self, baseEntity: ApplicationConfigToSpectrometerProfile):
        self.__baseEntity = baseEntity
        return self
