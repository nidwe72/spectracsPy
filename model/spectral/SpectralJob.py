import numpy as np

class SpectralJob:
    valuesByNanometers: dict = None

    def setValuesByNanometers(self, valuesByNanometers):
        self.valuesByNanometers = valuesByNanometers
