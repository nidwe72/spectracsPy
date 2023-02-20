import string
from typing import Dict, List

import numpy as np
from PySide6.QtGui import QImage
from numpy import float32
from scipy.signal import find_peaks

from base.Singleton import Singleton
from logic.model.util.SpectrometerCalibrationProfileUtil import SpectrometerCalibrationProfileUtil
from logic.spectral.acquisition.device.calibration.SpectrometerWavelengthCalibrationLogicModuleParameters import \
    SpectrometerWavelengthCalibrationLogicModuleParameters
from logic.spectral.acquisition.device.calibration.SpectrometerWavelengthCalibrationLogicModuleResult import \
    SpectrometerWavelengthCalibrationLogicModuleResult
from logic.spectral.spectralLine.SpectralLinesSelectionLogicModule import SpectralLinesSelectionLogicModule
from logic.spectral.spectralLine.SpectralLinesSelectionLogicModuleParameters import \
    SpectralLinesSelectionLogicModuleParameters
from logic.spectral.util.SpectralLineMasterDataUtil import SpectralLineMasterDataUtil
from logic.spectral.util.SpectrallineUtil import SpectralLineUtil
from model.databaseEntity.spectral.device import SpectrometerCalibrationProfile
from model.databaseEntity.spectral.device.SpectralLine import SpectralLine
from model.databaseEntity.spectral.device.SpectralLineMasterDataColorName import SpectralLineMasterDataColorName


class SpectrometerWavelengthCalibrationLogicModule(Singleton):
    __moduleParameters: SpectrometerWavelengthCalibrationLogicModuleParameters = None

    spectralLineMasterDataColorNamesToProcess: List[str] = [SpectralLineMasterDataColorName.EUROPIUM_VIVID_GAMBOGE,
                                                            SpectralLineMasterDataColorName.MERCURY_MANGO_GREEN,
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

        spectrum = self.moduleParameters.videoSignal.spectrum
        logicModule = SpectralLinesSelectionLogicModule()

        moduleParameters = SpectralLinesSelectionLogicModuleParameters()
        moduleParameters.setSpectrum(spectrum) \
            .addSelectByProminence(10) \
            .addSelectByIntensity(2).addSelectByPixelIndex(1,reverse=True)
        logicModule.setModuleParameters(moduleParameters)

        spectralLine = logicModule.execute().getSpectralLines().pop()

        spectralLine.spectralLineMasterData = SpectralLineMasterDataUtil().getSpectralLineMasterDataByName(
            SpectralLineMasterDataColorName.EUROPIUM_VIVID_GAMBOGE)

        self.getModuleResult().getSpectralLines().append(spectralLine)

        return;

    def _processSpectralLineMERCURY_MANGO_GREEN(self) -> SpectralLine:
        spectrum = self.moduleParameters.videoSignal.spectrum
        logicModule = SpectralLinesSelectionLogicModule()

        detectedSpectralLinesByNames=SpectralLineUtil().sortSpectralLinesByNames(self.getModuleResult().getSpectralLines())
        rightSpectralLine=detectedSpectralLinesByNames[SpectralLineMasterDataColorName.EUROPIUM_VIVID_GAMBOGE];

        moduleParameters = SpectralLinesSelectionLogicModuleParameters()
        moduleParameters.setSpectrum(spectrum) \
            .addSelectByProminence(10,rightSpectralLine=rightSpectralLine) \
            .addSelectByIntensity(1)
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
