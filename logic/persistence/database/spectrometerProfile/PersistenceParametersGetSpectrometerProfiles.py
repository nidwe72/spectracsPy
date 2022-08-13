from typing import List

class PersistenceParametersGetSpectrometerProfiles:
    ids: List = []

    def setIds(self, ids: List):
        self.ids = ids

    def getIds(self) -> List:
        return self.ids
