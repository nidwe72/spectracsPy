from typing import List

from sciens.base.Singleton import Singleton
from sciens.spectracs.logic.model.util.SpectrometerCalibrationProfileUtil import SpectrometerCalibrationProfileUtil
from sciens.spectracs.logic.spectral.acquisition.device.calibration.SpectrometerWavelengthCalibrationLogicModuleParameters import \
    SpectrometerWavelengthCalibrationLogicModuleParameters
from sciens.spectracs.logic.spectral.acquisition.device.calibration.SpectrometerWavelengthCalibrationLogicModuleResult import \
    SpectrometerWavelengthCalibrationLogicModuleResult
from sciens.spectracs.logic.spectral.spectralLine.SpectralLinesSelectionLogicModule import SpectralLinesSelectionLogicModule
from sciens.spectracs.logic.spectral.spectralLine.SpectralLinesSelectionLogicModuleParameters import \
    SpectralLinesSelectionLogicModuleParameters
from sciens.spectracs.logic.spectral.util.SpectralLineMasterDataUtil import SpectralLineMasterDataUtil
from sciens.spectracs.logic.spectral.util.SpectrallineUtil import SpectralLineUtil
from sciens.spectracs.model.databaseEntity.spectral.device.SpectralLine import SpectralLine
from sciens.spectracs.model.databaseEntity.spectral.device.SpectralLineMasterDataColorName import SpectralLineMasterDataColorName
from sciens.spectracs.model.databaseEntity.spectral.device.calibration.SpectrometerCalibrationProfile import \
    SpectrometerCalibrationProfile


class SpectrometerWavelengthCalibrationLogicModule(Singleton):
    __moduleParameters: SpectrometerWavelengthCalibrationLogicModuleParameters = None

    # (A) Anchor on the green mercury line FIRST (it is the single most prominent CFL line), then the
    # red europium line to its right. The remaining lines grow leftward from green. Processing order
    # matters: each later step references lines found by earlier steps.
    spectralLineMasterDataColorNamesToProcess: List[str] = [SpectralLineMasterDataColorName.MERCURY_MANGO_GREEN,
                                                            SpectralLineMasterDataColorName.EUROPIUM_VIVID_GAMBOGE,
                                                            SpectralLineMasterDataColorName.MERCURY_FRENCH_VIOLET,
                                                            SpectralLineMasterDataColorName.MERCURY_BLUE,
                                                            SpectralLineMasterDataColorName.TERBIUM_AQUA]

    model: SpectrometerCalibrationProfile = None

    # __peaks: Dict[int, int] = None
    # __originalPeaks: Dict[int, int] = None
    # __image: QImage = None

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

    def execute(self) :
        self.setModuleResult(SpectrometerWavelengthCalibrationLogicModuleResult())

        for spectralLineMasterDataColorName in self.spectralLineMasterDataColorNamesToProcess:
            self._processSpectralLine(spectralLineMasterDataColorName)

    def _processSpectralLine(self, spectralLineMasterDataColorName):
        func = getattr(self, f"_processSpectralLine{spectralLineMasterDataColorName}")
        func()

    def _processSpectralLineEUROPIUM_VIVID_GAMBOGE(self) -> SpectralLine:
        # (A) Europium red 611 is the most prominent peak to the RIGHT of the green anchor. Selecting by
        # prominence + position (rather than absolute intensity) avoids mislabelling the second
        # green-doublet peak as the red line, which collapsed calibration on virtual/over-exposed images.
        spectrum = self.moduleParameters.videoSignal.spectrum
        logicModule = SpectralLinesSelectionLogicModule()

        detectedSpectralLinesByNames = SpectralLineUtil().sortSpectralLinesByNames(self.getModuleResult().getSpectralLines())
        leftSpectralLine = detectedSpectralLinesByNames[SpectralLineMasterDataColorName.MERCURY_MANGO_GREEN]

        moduleParameters = SpectralLinesSelectionLogicModuleParameters()
        moduleParameters.setSpectrum(spectrum) \
            .addSelectByProminence(1, leftSpectralLine=leftSpectralLine)
        logicModule.setModuleParameters(moduleParameters)

        spectralLine = logicModule.execute().getSpectralLines().pop()

        spectralLine.spectralLineMasterData = SpectralLineMasterDataUtil().getSpectralLineMasterDataByName(
            SpectralLineMasterDataColorName.EUROPIUM_VIVID_GAMBOGE)

        self.getModuleResult().getSpectralLines().append(spectralLine)

        return;

    def _processSpectralLineMERCURY_MANGO_GREEN(self) -> SpectralLine:
        # (A) Green mercury 546 is the single most prominent line of a CFL spectrum, so anchor on it by
        # prominence (robust to exposure) instead of absolute intensity. This is the primary anchor and
        # is selected with no left/right bound (whole spectrum).
        spectrum = self.moduleParameters.videoSignal.spectrum
        logicModule = SpectralLinesSelectionLogicModule()

        moduleParameters = SpectralLinesSelectionLogicModuleParameters()
        moduleParameters.setSpectrum(spectrum) \
            .addSelectByProminence(1)
        logicModule.setModuleParameters(moduleParameters)

        spectralLine = logicModule.execute().getSpectralLines().pop()

        spectralLine.spectralLineMasterData = SpectralLineMasterDataUtil().getSpectralLineMasterDataByName(
            SpectralLineMasterDataColorName.MERCURY_MANGO_GREEN)

        self.getModuleResult().getSpectralLines().append(spectralLine)


    def _processSpectralLineMERCURY_FRENCH_VIOLET(self) -> SpectralLine:
        spectrum = self.moduleParameters.videoSignal.spectrum
        logicModule = SpectralLinesSelectionLogicModule()

        detectedSpectralLinesByNames=SpectralLineUtil().sortSpectralLinesByNames(self.getModuleResult().getSpectralLines())
        rightSpectralLine=detectedSpectralLinesByNames[SpectralLineMasterDataColorName.MERCURY_MANGO_GREEN];

        moduleParameters = SpectralLinesSelectionLogicModuleParameters()
        moduleParameters.setSpectrum(spectrum) \
            .addSelectByProminence(10,rightSpectralLine=rightSpectralLine) \
            .addSelectByPixelIndex(1,reverse=False)
        logicModule.setModuleParameters(moduleParameters)

        spectralLine = logicModule.execute().getSpectralLines().pop()

        spectralLine.spectralLineMasterData = SpectralLineMasterDataUtil().getSpectralLineMasterDataByName(
            SpectralLineMasterDataColorName.MERCURY_FRENCH_VIOLET)

        self.getModuleResult().getSpectralLines().append(spectralLine)


    def _processSpectralLineMERCURY_BLUE(self) -> SpectralLine:
        spectrum = self.moduleParameters.videoSignal.spectrum
        logicModule = SpectralLinesSelectionLogicModule()

        detectedSpectralLinesByNames=SpectralLineUtil().sortSpectralLinesByNames(self.getModuleResult().getSpectralLines())
        leftSpectralLine = detectedSpectralLinesByNames[SpectralLineMasterDataColorName.MERCURY_FRENCH_VIOLET];
        rightSpectralLine=detectedSpectralLinesByNames[SpectralLineMasterDataColorName.MERCURY_MANGO_GREEN];

        moduleParameters = SpectralLinesSelectionLogicModuleParameters()
        moduleParameters.setSpectrum(spectrum) \
            .addSelectByProminence(2,leftSpectralLine=leftSpectralLine,rightSpectralLine=rightSpectralLine) \
            .addSelectByPixelIndex(1,reverse=False)
        logicModule.setModuleParameters(moduleParameters)

        spectralLine = logicModule.execute().getSpectralLines().pop()

        spectralLine.spectralLineMasterData = SpectralLineMasterDataUtil().getSpectralLineMasterDataByName(
            SpectralLineMasterDataColorName.MERCURY_BLUE)

        self.getModuleResult().getSpectralLines().append(spectralLine)

    #
    def _processSpectralLineTERBIUM_AQUA(self) -> SpectralLine:
        spectrum = self.moduleParameters.videoSignal.spectrum
        logicModule = SpectralLinesSelectionLogicModule()

        detectedSpectralLinesByNames=SpectralLineUtil().sortSpectralLinesByNames(self.getModuleResult().getSpectralLines())
        leftSpectralLine = detectedSpectralLinesByNames[SpectralLineMasterDataColorName.MERCURY_BLUE];
        rightSpectralLine=detectedSpectralLinesByNames[SpectralLineMasterDataColorName.MERCURY_MANGO_GREEN];

        moduleParameters = SpectralLinesSelectionLogicModuleParameters()
        moduleParameters.setSpectrum(spectrum) \
            .addSelectByProminence(1,leftSpectralLine=leftSpectralLine,rightSpectralLine=rightSpectralLine)

        logicModule.setModuleParameters(moduleParameters)

        spectralLine = logicModule.execute().getSpectralLines().pop()

        spectralLine.spectralLineMasterData = SpectralLineMasterDataUtil().getSpectralLineMasterDataByName(
            SpectralLineMasterDataColorName.TERBIUM_AQUA)

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
