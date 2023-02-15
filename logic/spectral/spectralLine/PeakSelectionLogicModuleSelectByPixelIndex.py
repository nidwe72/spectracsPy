from logic.spectral.spectralLine.ISpectralLinesSelectionLogicModuleSelectionParameter import \
    IPeakSelectionLogicModuleSelectionParameter


class PeakSelectionLogicModuleSelectByPixelIndex(IPeakSelectionLogicModuleSelectionParameter):
    __count: int = 1

    def getCount(self):
        return self.__count

    def setCount(self, count):
        self.__count = count
        return self
