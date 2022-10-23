from typing import List

class PersistenceParametersGetSpectralLineMasterDatas:
    ids: List = []

    def setIds(self, ids: List):
        self.ids = ids

    def getIds(self) -> List:
        return self.ids
