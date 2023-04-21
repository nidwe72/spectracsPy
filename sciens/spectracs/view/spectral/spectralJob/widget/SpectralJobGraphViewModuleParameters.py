from sciens.spectracs.model.spectral.SpectrumSampleType import SpectrumSampleType
from spectracs.view.spectral.spectralJob.widget.SpectralJobGraphViewModulePolicyParameter import \
    SpectralJobGraphViewModulePolicyParameter


class SpectralJobGraphViewModuleParameters:
    def __init__(self):
        self.spectrumSampleType = SpectrumSampleType.UNSPECIFIED
        self.policy = SpectralJobGraphViewModulePolicyParameter.PLOT_SPECTRA

    def setSpectrumSampleType(self, spectrumSampleType: SpectrumSampleType):
        self.spectrumSampleType = spectrumSampleType

    def getSpectrumSampleType(self):
        return self.spectrumSampleType

    def setPolicy(self, policy: SpectralJobGraphViewModulePolicyParameter):
        self.policy = policy

    def getPolicy(self):
        return self.policy
