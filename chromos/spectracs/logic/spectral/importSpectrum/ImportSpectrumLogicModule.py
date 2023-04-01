from chromos.spectracs.logic.spectral.importSpectrum.ImportSpectrumLogicModuleParameters import ImportSpectrumLogicModuleParameters
from chromos.spectracs.logic.spectral.importSpectrum.ImportSpectrumLogicModuleResult import ImportSpectrumLogicModuleResult
from chromos.spectracs.model.spectral.SpectralJob import SpectralJob

from pyspectra.readers.read_dx import read_dx


class ImportSpectrumLogicModule:

    def importSpectrum(self, importSpectrumLogicModuleParameters: ImportSpectrumLogicModuleParameters):
        Foss_single = read_dx()
        filepath = importSpectrumLogicModuleParameters.getFilepath()
        filepath = "/home/nidwe/tmp/test.dx"

        dataFrame = Foss_single.read(file=filepath)

        spectralColumns = dict(enumerate(dataFrame.columns.to_numpy().flatten(), 1))
        spectralValues = dict(enumerate(dataFrame.transpose().to_numpy().flatten(), 1))

        valesByNanometers = dict(zip(spectralColumns.values(), spectralValues.values()))
        spectralJob = SpectralJob()
        spectralJob.setValuesByNanometers(valesByNanometers)
        result = ImportSpectrumLogicModuleResult()
        result.setSpectralJob(spectralJob)

        return result
