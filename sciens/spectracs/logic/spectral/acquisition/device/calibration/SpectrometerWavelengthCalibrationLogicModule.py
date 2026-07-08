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
                                                            SpectralLineMasterDataColorName.TERBIUM_AQUA,
                                                            # Best-effort 6th anchor: the 542.4 partner of the green
                                                            # doublet. Runs LAST so the 5 primary anchors (esp. green
                                                            # + red, needed for the dispersion estimate) already exist;
                                                            # skipped silently if the doublet is unresolved (b).
                                                            SpectralLineMasterDataColorName.MERCURY_MANGO_GREEN_LEFT]

    # Doublet geometry for the best-effort green-left search (nm).
    GREEN_NANOMETER = 546.5
    GREEN_LEFT_NANOMETER = 542.4
    RED_NANOMETER = 611.6

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
        # Use .name (the bare member, e.g. MERCURY_MANGO_GREEN) — NOT f"{enum}". This enum is a
        # (str, Enum); on Python 3.10 f"{member}" yields the value, but on Android's Python 3.11 the
        # enum __str__/__format__ change yields "ClassName.MEMBER", which built a wrong method name
        # and raised AttributeError. .name is identical on both Pythons.
        func = getattr(self, f"_processSpectralLine{spectralLineMasterDataColorName.name}")
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


    def _processSpectralLineMERCURY_MANGO_GREEN_LEFT(self):
        # Best-effort 2nd green anchor (542.4, the left partner of the 546.5 doublet). We do NOT take the
        # global 2nd-most-prominent peak (that is usually the red/blue, not the fainter left green) — instead
        # we search a small window just LEFT of the dominant green peak, sized from the green→red dispersion.
        # If no peak is found there (doublet unresolved), skip: the 5 primary anchors still calibrate (b).
        spectrum = self.moduleParameters.videoSignal.spectrum
        linesByNames = SpectralLineUtil().sortSpectralLinesByNames(self.getModuleResult().getSpectralLines())
        greenLine = linesByNames.get(SpectralLineMasterDataColorName.MERCURY_MANGO_GREEN)
        redLine = linesByNames.get(SpectralLineMasterDataColorName.EUROPIUM_VIVID_GAMBOGE)
        if greenLine is None or redLine is None or redLine.pixelIndex <= greenLine.pixelIndex:
            return

        dispersion = (self.RED_NANOMETER - self.GREEN_NANOMETER) / (redLine.pixelIndex - greenLine.pixelIndex)  # nm/px
        if dispersion <= 0:
            return
        doubletPixels = (self.GREEN_NANOMETER - self.GREEN_LEFT_NANOMETER) / dispersion
        leftBoundPixel = int(greenLine.pixelIndex - 2.5 * doubletPixels)
        rightBoundPixel = int(greenLine.pixelIndex - 0.3 * doubletPixels)
        if rightBoundPixel <= leftBoundPixel:
            return

        leftBound = SpectralLine()
        leftBound.pixelIndex = leftBoundPixel
        rightBound = SpectralLine()
        rightBound.pixelIndex = rightBoundPixel

        moduleParameters = SpectralLinesSelectionLogicModuleParameters()
        moduleParameters.setSpectrum(spectrum) \
            .addSelectByProminence(1, leftSpectralLine=leftBound, rightSpectralLine=rightBound)
        logicModule = SpectralLinesSelectionLogicModule()
        logicModule.setModuleParameters(moduleParameters)
        selected = logicModule.execute().getSpectralLines()
        if not selected:
            return  # doublet unresolved -> best-effort skip

        spectralLine = selected.pop()
        spectralLine.spectralLineMasterData = SpectralLineMasterDataUtil().getSpectralLineMasterDataByName(
            SpectralLineMasterDataColorName.MERCURY_MANGO_GREEN_LEFT)
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
