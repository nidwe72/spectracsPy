class PersistApplicationConfigLogicModuleParameters:

    def __init__(self, *args, **kwargs):
        self.__baseEntity= None

    def getBaseEntity(self):
        return self.__baseEntity

    def setBaseEntity(self, baseEntity):
        self.__baseEntity=baseEntity
        return self

