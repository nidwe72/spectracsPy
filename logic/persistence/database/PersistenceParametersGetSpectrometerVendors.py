from typing import List
class PersistenceParametersGetSpectrometerVendors:

    ids:List=[]

    def setIds(self,ids:List):
        self.ids=ids

    def getIds(self)->List:
        return self.ids