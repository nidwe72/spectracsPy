from logic.spectral.util.IPeakSelectionLogicModuleSelectionParameter import IPeakSelectionLogicModuleSelectionParameter


class PeakSelectionLogicModuleSelectByProminenceParameter(IPeakSelectionLogicModuleSelectionParameter):
    __count: int = None

    @property
    def count(self):
        return self.__count

    @count.setter
    def count(self, count):
        self.__count = count
