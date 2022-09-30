from typing import Dict

import numpy as np

from PyQt6.QtGui import QImage, QColor
from numpy import poly1d

from base.Singleton import Singleton
from logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from logic.model.util.SpectrometerCalibrationProfileUtil import SpectrometerCalibrationProfileUtil
from logic.spectral.util.SpectralColorUtil import SpectralColorUtil
from logic.spectral.util.SpectrallineUtil import SpectralLineUtil
from model.databaseEntity.spectral.device import SpectrometerCalibrationProfile
from model.databaseEntity.spectral.device.SpectralLine import SpectralLine


class SpectrometerWavelengthCalibrationLogicModule(Singleton):

    model:SpectrometerCalibrationProfile=None

    __peaks: Dict[int, int] = None
    __originalPeaks: Dict[int, int] = None
    __image: QImage = None

    __spectralLinesByPixelIndices: Dict[int, SpectralLine] = None

    def setPeaks(self, peaks: Dict[int, int]):
        self.__peaks = peaks.copy()
        self.__originalPeaks = peaks.copy()

    def setImage(self, image: QImage):
        self.__image = image

    def getSpectralLinesByPixelIndices(self):
        return self.__spectralLinesByPixelIndices

    def getSpectralLinesByPixelIndicesPhaseOne(self) -> Dict[int, SpectralLine]:
        self.__spectralLinesByPixelIndices = {}
        self.__getSpectralLinesByPixelIndices_processSpectralLineEuropiumVividGamboge()
        return self.__spectralLinesByPixelIndices

    def getSpectralLinesByPixelIndicesPhaseTwo(self) -> Dict[int, SpectralLine]:

        peakVales = list(self.__spectralLinesByPixelIndices.keys())
        for peak in peakVales:
            self.__removePeak(peak)

        self.__getSpectralLinesByPixelIndices_processSpectralLineMercuryBlue()
        self.__getSpectralLinesByPixelIndices_processSpectralLineMercuryFrenchViolet()
        self.__getSpectralLinesByPixelIndices_processSpectralLineTerbiumAqua()

        self.__getSpectralLinesByPixelIndices_processSpectralLineEuropiumAmber()
        self.__getSpectralLinesByPixelIndices_processSpectralLineEuropiumCyberYellow()
        self.__getSpectralLinesByPixelIndices_processSpectralLineEuropiumMiddleYellow()

        self.__getSpectralLinesByPixelIndices_processSpectralLineMercuryMangoGreen()

        self.__getSpectralLinesByPixelIndices_processSpectralLineEuropiumRed()
        self.__getSpectralLinesByPixelIndices_processSpectralLineEuropiumInternationalOrange()

        self.__spectralLinesByPixelIndices = SpectralLineUtil().sortSpectralLinesByPixelIndices(list(self.__spectralLinesByPixelIndices.values()))

        self.interpolate()

        model = self.getModel()
        for spectralLine in list(self.__spectralLinesByPixelIndices.values()):
            modelSpectraLine = SpectrometerCalibrationProfileUtil().getMatchingSpectralLine(model,spectralLine)
            modelSpectraLine.pixelIndex=spectralLine.pixelIndex

        return self.__spectralLinesByPixelIndices

    def interpolate(self)->poly1d:
        pixelIndices = SpectralLineUtil().getPixelIndices(list(self.__spectralLinesByPixelIndices.values()))
        nanometers = SpectralLineUtil().getNanometers(list(self.__spectralLinesByPixelIndices.values()))
        polynomialCoefficients=np.polyfit(np.array(pixelIndices),np.array(nanometers),4)

        model = self.getModel()
        model.interpolationCoefficientA=polynomialCoefficients[0]
        model.interpolationCoefficientB = polynomialCoefficients[1]
        model.interpolationCoefficientC = polynomialCoefficients[2]
        model.interpolationCoefficientD = polynomialCoefficients[3]

        return

    def __getSpectralLinesByPixelIndices_processSpectralLineTerbiumAqua(self):
        spectralLine =self.__getSpectralLineWithName('TerbiumAqua')
        self.__getSpectralLinesByPixelIndices_processSpectralLineByFindingBestColorMatch(spectralLine)
        self.__removePeak(spectralLine.pixelIndex)

    def __getSpectralLinesByPixelIndices_processSpectralLineMercuryFrenchViolet(self):
        spectralLine = self.__getSpectralLineWithName('MercuryFrenchViolet')
        pixelIndex = list(self.__peaks.keys())[0]
        self.__getSpectralLinesByPixelIndices_processSpectralLineBySuppliedPixelIndex(spectralLine, pixelIndex)

    def __getSpectralLinesByPixelIndices_processSpectralLineMercuryBlue(self):
        spectralLine = self.__getSpectralLineWithName('MercuryBlue')
        pixelIndex = list(self.__peaks.keys())[1]
        self.__getSpectralLinesByPixelIndices_processSpectralLineBySuppliedPixelIndex(spectralLine, pixelIndex)

    def __getSpectralLinesByPixelIndices_processSpectralLineEuropiumVividGamboge(self):
        spectralLine = self.__getSpectralLineWithName('EuropiumVividGamboge')
        self.__getSpectralLinesByPixelIndices_processSpectralLineByFindingBestColorMatch(spectralLine)

    def __getSpectralLinesByPixelIndices_processSpectralLineEuropiumAmber(self):
        resultSpectralLine = self.__getSpectralLineWithName('EuropiumAmber')
        referenceSpectralLine = self.__getDetectedSpectralLineOfName('EuropiumVividGamboge')
        self.__getSpectralLinesByPixelIndices_processSpectralLineGetSpectraLineOffsetToReferenceSpectralLine(
            resultSpectralLine,
            referenceSpectralLine, -1)

    def __getSpectralLinesByPixelIndices_processSpectralLineEuropiumCyberYellow(self):
        resultSpectralLine = self.__getSpectralLineWithName('EuropiumCyberYellow')
        referenceSpectralLine = self.__getDetectedSpectralLineOfName('EuropiumAmber')
        self.__getSpectralLinesByPixelIndices_processSpectralLineGetSpectraLineOffsetToReferenceSpectralLine(
            resultSpectralLine,
            referenceSpectralLine, -1)

    def __getSpectralLinesByPixelIndices_processSpectralLineEuropiumMiddleYellow(self):
        resultSpectralLine = self.__getSpectralLineWithName('EuropiumMiddleYellow')
        referenceSpectralLine = self.__getDetectedSpectralLineOfName('EuropiumCyberYellow')
        self.__getSpectralLinesByPixelIndices_processSpectralLineGetSpectraLineOffsetToReferenceSpectralLine(
            resultSpectralLine,
            referenceSpectralLine, -1)

    def __getSpectralLinesByPixelIndices_processSpectralLineMercuryMangoGreen(self):

        # The following heuristic strategy seems to work
        #   * limit the search to the area between 'TerbiumAqua' and 'EuropiumMiddleYellow'
        #   * limit this area to some middle region of this interval
        #   * collect the spectral lines matching 'MercuryMangoGreen' by color and sort by prominence
        #   * take the two SpectralLine/s with the highest prominences and take the right one

        spectralLine = self.__getSpectralLineWithName('MercuryMangoGreen')

        leftSpectralLine = self.__getDetectedSpectralLineOfName('TerbiumAqua')
        rightSpectralLine = self.__getDetectedSpectralLineOfName('EuropiumMiddleYellow')

        leftSpectralLinePixelIndex = leftSpectralLine.pixelIndex
        rightSpectralLinePixelIndex = rightSpectralLine.pixelIndex
        width = rightSpectralLinePixelIndex - leftSpectralLinePixelIndex
        offsetWidth = width * 0.3

        startSpectralLinePixelIndex = leftSpectralLinePixelIndex + offsetWidth
        endSpectralLinePixelIndex = rightSpectralLinePixelIndex - offsetWidth

        matchingPixelIndices = []
        matchingSpectralLines: Dict[int, SpectralLine] = {}

        for someIndex in range(len(list(self.__peaks.keys()))):
            someColorPixelIndex = self.__getPeakMatchingSuppliedColorBest(spectralLine.nanometer)
            if someColorPixelIndex > startSpectralLinePixelIndex and someColorPixelIndex < endSpectralLinePixelIndex:
                matchingPixelIndices.append(someColorPixelIndex)
                matchingSpectralLines[someColorPixelIndex] = self.__peaks[someColorPixelIndex]
                self.__removePeak(someColorPixelIndex)
            elif someColorPixelIndex > leftSpectralLinePixelIndex and someColorPixelIndex < rightSpectralLinePixelIndex:
                self.__removePeak(someColorPixelIndex)

        matchingSpectralLines = SpectralLineUtil().sortSpectralLinesByProminences(list(matchingSpectralLines.values()))

        resultSpectralLine = matchingSpectralLines[0];

        if len(matchingSpectralLines) >= 2:
            additionalCandidateSpectralLine = matchingSpectralLines[1];
            if additionalCandidateSpectralLine.pixelIndex > resultSpectralLine.pixelIndex:
                resultSpectralLine = additionalCandidateSpectralLine

        spectralLine.pixelIndex = resultSpectralLine.pixelIndex
        self.__spectralLinesByPixelIndices[spectralLine.pixelIndex] = spectralLine

    def __getSpectralLinesByPixelIndices_processSpectralLineEuropiumRed(self):

        # The following heuristic strategy seems to work
        #   * take the following search region
        #       * calculate offsetWidth as the width from 'EuropiumMiddleYellow' to 'EuropiumVividGamboge' times 120%
        #       * The left limit 'EuropiumVividGamboge + offsetWith'
        #       * The right limit is 'left limit + offsetWith'
        #       * This way 'EuropiumInternationalOrange' is one the left of the search region
        #         and some orange-like peak located at the right of the red region is also excluded from the search

        #   * collect the spectral lines matching 'EuropiumRed' by color and sort by prominence
        #   * take the two SpectralLine/s with the highest prominences and take the left one


        spectralLine = self.__getSpectralLineWithName('EuropiumRed')

        spectralLineEuropiumVividGamboge = self.__getDetectedSpectralLineOfName('EuropiumVividGamboge')
        spectralLineEuropiumMiddleYellow = self.__getDetectedSpectralLineOfName('EuropiumMiddleYellow')

        leftSpectralLine = SpectralLine()
        offsetWidth = (spectralLineEuropiumVividGamboge.pixelIndex - spectralLineEuropiumMiddleYellow.pixelIndex) * 1.2
        leftSpectralLine.pixelIndex = spectralLineEuropiumVividGamboge.pixelIndex \
                                      + offsetWidth
        leftSpectralLine.color = ApplicationStyleLogicModule().getPrimaryColor()
        leftSpectralLine.name = 'leftSpectralLine'

        rightSpectralLine = SpectralLine()
        rightSpectralLine.pixelIndex = leftSpectralLine.pixelIndex + offsetWidth
        rightSpectralLine.color = ApplicationStyleLogicModule().getPrimaryColor()
        rightSpectralLine.name = 'rightSpectralLine'

        # self.__spectralLinesByPixelIndices[leftSpectralLine.pixelIndex] = leftSpectralLine
        # self.__spectralLinesByPixelIndices[rightSpectralLine.pixelIndex] = rightSpectralLine

        startSpectralLinePixelIndex = leftSpectralLine.pixelIndex
        endSpectralLinePixelIndex = rightSpectralLine.pixelIndex

        matchingPixelIndices = []
        matchingSpectralLines: Dict[int, SpectralLine] = {}

        # for someIndex in range(len(list(self.__peaks.keys()))):
        for somePixelIndex in list(self.__peaks.keys()):
            someColorPixelIndex = self.__getPeakMatchingSuppliedColorBest(spectralLine.nanometer,
                                                                          startSpectralLinePixelIndex,
                                                                          endSpectralLinePixelIndex)
            if someColorPixelIndex is not None:
                matchingPixelIndices.append(someColorPixelIndex)
                matchingSpectralLines[someColorPixelIndex] = self.__peaks[someColorPixelIndex]
                self.__removePeak(someColorPixelIndex)

        matchingSpectralLines = SpectralLineUtil().sortSpectralLinesByProminences(list(matchingSpectralLines.values()))

        resultSpectralLine = matchingSpectralLines[0];

        if len(matchingSpectralLines) >= 2:
            additionalCandidateSpectralLine = matchingSpectralLines[1];
            if additionalCandidateSpectralLine.pixelIndex < resultSpectralLine.pixelIndex:
                resultSpectralLine = additionalCandidateSpectralLine

        spectralLine.pixelIndex = resultSpectralLine.pixelIndex
        self.__spectralLinesByPixelIndices[spectralLine.pixelIndex] = spectralLine

        pass

    def __getSpectralLinesByPixelIndices_processSpectralLineEuropiumInternationalOrange(self):
        spectralLine = self.__getSpectralLineWithName('EuropiumInternationalOrange')

        spectralLineEuropiumVividGamboge = self.__getDetectedSpectralLineOfName('EuropiumVividGamboge')
        spectralLineEuropiumMiddleYellow = self.__getDetectedSpectralLineOfName('EuropiumMiddleYellow')

        leftSpectralLine = self.__getDetectedSpectralLineOfName('EuropiumVividGamboge')
        rightSpectralLine = self.__getDetectedSpectralLineOfName('EuropiumRed')

        startSpectralLinePixelIndex = leftSpectralLine.pixelIndex
        endSpectralLinePixelIndex = rightSpectralLine.pixelIndex

        matchingPixelIndices = []
        matchingSpectralLines: Dict[int, SpectralLine] = {}

        # for someIndex in range(len(list(self.__peaks.keys()))):
        for somePixelIndex in list(self.__peaks.keys()):
            someColorPixelIndex = self.__getPeakMatchingSuppliedColorBest(spectralLine.nanometer,
                                                                          startSpectralLinePixelIndex,
                                                                          endSpectralLinePixelIndex)
            if someColorPixelIndex is not None:
                matchingPixelIndices.append(someColorPixelIndex)
                matchingSpectralLines[someColorPixelIndex] = self.__peaks[someColorPixelIndex]
                self.__removePeak(someColorPixelIndex)

        matchingSpectralLines = SpectralLineUtil().sortSpectralLinesByProminences(list(matchingSpectralLines.values()))

        resultSpectralLine = matchingSpectralLines[0];

        if len(matchingSpectralLines) >= 2:
            additionalCandidateSpectralLine = matchingSpectralLines[1];
            if additionalCandidateSpectralLine.pixelIndex > resultSpectralLine.pixelIndex:
                resultSpectralLine = additionalCandidateSpectralLine

        spectralLine.pixelIndex = resultSpectralLine.pixelIndex
        self.__spectralLinesByPixelIndices[spectralLine.pixelIndex] = spectralLine

        pass

    def __getSpectralLinesByPixelIndices_processSpectralLineGetSpectraLineOffsetToReferenceSpectralLine(self,
                                                                                                        resultSpectralLine: SpectralLine,
                                                                                                        referenceSpectralLine: SpectralLine,
                                                                                                        offset):
        peakPixelIndices = list(self.__originalPeaks.keys())
        suppliedPixelIndex = referenceSpectralLine.pixelIndex
        resultListIndex = peakPixelIndices.index(suppliedPixelIndex) + offset
        pixelPixelIndex = resultPixelIndex = peakPixelIndices[resultListIndex]
        resultSpectralLine.pixelIndex = pixelPixelIndex
        self.__getSpectralLinesByPixelIndices_processSpectralLineBySuppliedPixelIndex(resultSpectralLine,
                                                                                      pixelPixelIndex)

    def __getSpectralLinesByPixelIndices_processSpectralLineBySuppliedPixelIndex(self, spectralLine: SpectralLine,
                                                                                 pixelIndex: int):
        spectralLine.pixelIndex = pixelIndex
        self.__spectralLinesByPixelIndices[pixelIndex] = spectralLine
        self.__removePeak(spectralLine.pixelIndex)

    def __getSpectralLinesByPixelIndices_processSpectralLineByFindingBestColorMatch(self, spectralLine: SpectralLine):
        spectralLine.color = SpectralColorUtil().wavelengthToColor(spectralLine.nanometer)
        spectralLine.pixelIndex = self.__getPeakMatchingSuppliedColorBest(spectralLine.nanometer)
        self.__getSpectralLinesByPixelIndices_processSpectralLineBySuppliedPixelIndex(spectralLine,
                                                                                      spectralLine.pixelIndex);

    def __getDetectedSpectralLineOfName(self, spectralLineName) -> SpectralLine:
        result = None
        for pixelIndex, spectralLine in self.__spectralLinesByPixelIndices.items():
            if spectralLine.name == spectralLineName:
                result = spectralLine
                break
        return result

    def __getPeaksBetweenSuppliedSpectralLines(self, leftSpectralLine: SpectralLine, rightSpectralLine: SpectralLine):
        result = []
        leftSpectralLinePixelIndex = leftSpectralLine.pixelIndex
        rightSpectralLinePixelIndex = rightSpectralLine.pixelIndex
        for peak in list(self.__peaks.values()):
            if peak > leftSpectralLinePixelIndex and peak < rightSpectralLinePixelIndex:
                result.append(peak)
        return result

    def __getPeakMatchingSuppliedColorBest(self, wavelength, startPixelIndex=0, endPixelIndex=0):
        result = None

        suppliedColor = SpectralColorUtil().wavelengthToColor(wavelength)
        distancesByPixelIndices = {}

        for peak in self.__peaks:

            if startPixelIndex > 0 and endPixelIndex > 0 and not (startPixelIndex < peak < endPixelIndex):
                continue

            measurementPixel=round(self.getModel().regionOfInterestY2-(self.getModel().regionOfInterestY2-self.getModel().regionOfInterestY1)/2.0);
            pixelColor = self.__image.pixelColor(peak, measurementPixel)
            colorDifference = SpectralColorUtil().getColorDifference(suppliedColor, pixelColor)
            distancesByPixelIndices[peak] = colorDifference

        if len(distancesByPixelIndices) > 0:
            distancesByPixelIndicesSorted = sorted(distancesByPixelIndices.items(), key=lambda x: x[1])
            result = distancesByPixelIndicesSorted[0][0]
        return result

    def __removePeak(self, peak: int):
        try:
            self.__peaks.pop(peak)
        except KeyError:
            pass

    def setModel(self,model:SpectrometerCalibrationProfile):
        self.model=model

    def getModel(self):
        return self.model

    def __getSpectralLineWithName(self,name):
        result=SpectrometerCalibrationProfileUtil().getSpectralLineWithName(self.getModel(),name)
        return result


    def __getSpectralLinesByNames(self):
        spectralLines = self.getModel().getSpectralLines()
        result=SpectralLineUtil.sortSpectralLinesByNames(spectralLines)
        return result

