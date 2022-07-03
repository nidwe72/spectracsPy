from typing import List
class PersistenceParametersGetSpectrometerSensors:

    ids:List=[]

    def setIds(self,ids:List):
        self.ids=ids

    def getIds(self)->List:
        return self.ids