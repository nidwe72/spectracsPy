from sciens.base.Singleton import Singleton
from sciens.spectracs.logic.model.util.SpectrometerCalibrationProfileUtil import SpectrometerCalibrationProfileUtil
from sciens.spectracs.logic.spectral.acquisition.device.calibration.SpectrometerWavelengthCalibrationLogicModuleParameters import \
    SpectrometerWavelengthCalibrationLogicModuleParameters
from sciens.spectracs.logic.spectral.acquisition.device.calibration.SpectrometerWavelengthCalibrationLogicModuleResult import \
    SpectrometerWavelengthCalibrationLogicModuleResult
from sciens.spectracs.logic.spectral.acquisition.device.calibration.WavelengthLineDetectionLogicModule import \
    WavelengthLineDetectionLogicModule
from sciens.spectracs.logic.spectral.util.SpectralLineMasterDataUtil import SpectralLineMasterDataUtil
from sciens.spectracs.logic.spectral.util.SpectrallineUtil import SpectralLineUtil
from sciens.spectracs.model.databaseEntity.spectral.device.SpectralLine import SpectralLine
from sciens.spectracs.model.databaseEntity.spectral.device.calibration.SpectrometerCalibrationProfile import \
    SpectrometerCalibrationProfile


class SpectrometerWavelengthCalibrationLogicModule(Singleton):
    __moduleParameters: SpectrometerWavelengthCalibrationLogicModuleParameters = None

    # The CFL emission lines this calibration detects — the ONE list lives in the detection module. Also read by
    # SpectrometerCalibrationProfileSpectralLinesViewModule to filter which lines it displays.
    spectralLineMasterDataColorNamesToProcess = list(WavelengthLineDetectionLogicModule.NM.keys())

    model: SpectrometerCalibrationProfile = None

    __moduleResult: SpectrometerWavelengthCalibrationLogicModuleResult = None

    def getModuleResult(self) -> SpectrometerWavelengthCalibrationLogicModuleResult:
        if self.__moduleResult is None:
            self.__moduleResult=SpectrometerWavelengthCalibrationLogicModuleResult
        return self.__moduleResult

    def setModuleResult(self, moduleResult):
        self.__moduleResult = moduleResult

    @property
    def moduleParameters(self):
        return self.__moduleParameters

    @moduleParameters.setter
    def moduleParameters(self, moduleParameters):
        self.__moduleParameters = moduleParameters

    def execute(self):
        # The colour-constrained emission-line detection lives in ONE place — WavelengthLineDetectionLogicModule
        # (SPEC_capture_quality.md §13, verified by diagnostics/calibration_fix_test.py) — so this module only wraps
        # the detected lines into SpectralLines + master data for the downstream cubic fit. This replaced the old
        # per-line "most-prominent peak" anchoring, which mislabelled the Europium red line as green at high capture
        # resolution (the green doublet splits and Eu out-prominences it), collapsing the whole calibration.
        self.setModuleResult(SpectrometerWavelengthCalibrationLogicModuleResult())
        spectrum = self.moduleParameters.videoSignal.spectrum
        detected = WavelengthLineDetectionLogicModule().detect(spectrum)
        masterDataUtil = SpectralLineMasterDataUtil()
        for colorName, detectedLine in detected.items():
            spectralLine = SpectralLine()
            spectralLine.pixelIndex = detectedLine.pixelIndex
            spectralLine.prominence = detectedLine.confidence
            spectralLine.spectralLineMasterData = masterDataUtil.getSpectralLineMasterDataByName(colorName)
            self.getModuleResult().getSpectralLines().append(spectralLine)

    def setModel(self, model: SpectrometerCalibrationProfile):
        self.model = model

    def getModel(self):
        return self.model

    def __getSpectralLineWithName(self, name):
        result = SpectrometerCalibrationProfileUtil().getSpectralLineWithName(self.getModel(), name)
        return result

    def __getSpectralLinesByNames(self):
        spectralLines = self.getModel().getSpectralLines()
        result = SpectralLineUtil.sortSpectralLinesByNames(spectralLines)
        return result
