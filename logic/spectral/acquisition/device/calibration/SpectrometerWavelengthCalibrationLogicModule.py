from typing import Dict

import numpy as np

from PySide6.QtGui import QImage, QColor
from matplotlib import pyplot as plt
from numpy import poly1d, float32, float64
from rascal.atlas import Atlas
from rascal.calibrator import Calibrator
from rascal.util import refine_peaks
from scipy.signal import find_peaks, peak_prominences

from base.Singleton import Singleton
from logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from logic.model.util.SpectrometerCalibrationProfileUtil import SpectrometerCalibrationProfileUtil
from logic.spectral.acquisition.device.calibration.SpectrometerWavelengthCalibrationLogicModuleParameters import \
    SpectrometerWavelengthCalibrationLogicModuleParameters
from logic.spectral.util.PeakSelectionLogicModuleParameters import PeakSelectionLogicModuleParameters
from logic.spectral.util.PeakSelectrionLogicModule import PeakSelectionLogicModule
from logic.spectral.util.SpectralColorUtil import SpectralColorUtil
from logic.spectral.util.SpectralLineMasterDataUtil import SpectralLineMasterDataUtil
from logic.spectral.util.SpectrallineUtil import SpectralLineUtil
from model.databaseEntity.spectral.device import SpectrometerCalibrationProfile
from model.databaseEntity.spectral.device.SpectralLine import SpectralLine
from model.databaseEntity.spectral.device.SpectralLineMasterData import SpectralLineMasterData
from model.databaseEntity.spectral.device.SpectralLineMasterDataColorName import SpectralLineMasterDataColorName

# This module proceeds as follows:
# * A fixed number of the most prominent peaks for a device is retrieved
# * A lookup table with the according spectral lines is looped trough
#  * The table holds the measured intensities [to_do: use normalized values] captured with some predefined exposure
#  * If the difference to the measured intensity is too high the module failed
# * The more generic algorithm RASCAL did ot work (sometime very good results, but also mistakes)
class SpectrometerWavelengthCalibrationLogicModule(Singleton):

    __moduleParameters:SpectrometerWavelengthCalibrationLogicModuleParameters=None

    model:SpectrometerCalibrationProfile=None

    __peaks: Dict[int, int] = None
    __originalPeaks: Dict[int, int] = None
    __image: QImage = None

    __spectralLinesByPixelIndices: Dict[int, SpectralLine] = None

    @property
    def moduleParameters(self):
        return self.__moduleParameters

    @moduleParameters.setter
    def moduleParameters(self, moduleParameters):
        self.__moduleParameters=moduleParameters

    #average the spectrum
    #detect peaks
    #plot peaks
    #run rascal
    #plot rascal result
    def execute(self):
        spectrum = self.moduleParameters.videoSignal.spectrum

        intensities = list(spectrum.valuesByNanometers.values())
        nanometersArrayFloat = np.asarray(intensities, float32)

        plt.title("spectrum")
        plt.xlabel("X axis")
        plt.ylabel("Y axis")
        plt.plot(list(spectrum.valuesByNanometers.keys()), list(spectrum.valuesByNanometers.values()), color="blue")
        plt.show()


        for prominence in range(1,100):
            peaks, _ = find_peaks(nanometersArrayFloat, distance=3, width=3, rel_height=0.5, prominence=prominence)
            if len(peaks)==10:
                break

        nanometersAtPeaks=nanometersArrayFloat[peaks.flatten().tolist()]


        prominences = peak_prominences(nanometersArrayFloat, peaks)[0]

        spectralLineMasterDatasByNames = SpectralLineMasterDataUtil().createTransientSpectralLineMasterDatasByNames()

        spectralLinesToUse = [SpectralLineMasterDataColorName.MERCURY_FRENCH_VIOLET,
                              SpectralLineMasterDataColorName.MERCURY_BLUE,
                              SpectralLineMasterDataColorName.TERBIUM_AQUA,
                              SpectralLineMasterDataColorName.MERCURY_MANGO_GREEN,
                              SpectralLineMasterDataColorName.MERCURY_OR_TERBIUM_LEMON_GLACIER,
                              SpectralLineMasterDataColorName.EUROPIUM_MIDDLE_YELLOW,
                              SpectralLineMasterDataColorName.EUROPIUM_CYBER_YELLOW,
                              SpectralLineMasterDataColorName.EUROPIUM_AMBER,
                              SpectralLineMasterDataColorName.EUROPIUM_INTERNATIONAL_ORANGE,
                              SpectralLineMasterDataColorName.EUROPIUM_VIVID_GAMBOGE]

        spectralLineMasterDatasByNames = dict(
            map(lambda key: (key, spectralLineMasterDatasByNames.get(key, None)), spectralLinesToUse))

        peaksBySpectralLineNames=dict(zip(spectralLinesToUse,peaks))

        code=[];

        differences=[]

        spectrumIntensitiesAtPeaks=[]
        for spectralLineName in spectralLinesToUse:
            peakPixel=peaksBySpectralLineNames[spectralLineName]
            spectralLine=spectralLineMasterDatasByNames[spectralLineName]
            spectralLineIntensity=spectralLine.intensity
            spectrumIntensity=spectrum.valuesByNanometers.get(peakPixel)
            spectrumIntensitiesAtPeaks.append(spectrumIntensity)
            difference=abs(spectralLineIntensity-spectrumIntensity)
            differences.append(difference)

            code.append(f"transientSpectralLineMasterData[SpectralLineMasterDataColorName.{spectralLineName}].intensity={spectrumIntensity}");

        peakSelectionLogicModule = PeakSelectionLogicModule()
        peakSelectionLogicModule.setModuleParameters(PeakSelectionLogicModuleParameters().setSpectrum(
            spectrum).addSelectByProminence(10))
        peakSelectionLogicModule.execute()



        return

        #
        # nanometersArrayFloat=nanometersArrayFloat*10
        #
        # peaks = refine_peaks(nanometersArrayFloat, peaks, window_width=5)
        #
        # atlas=self.createAtlas()
        #
        # c = Calibrator(peaks, spectrum=nanometersArrayFloat)
        # c.plot_arc()
        # c.set_hough_properties(
        #     num_slopes=5000,
        #     range_tolerance=500.0,
        #     xbins=1000,
        #     ybins=1000,
        #     # min_wavelength=405.4*10,
        #     # max_wavelength=631.1*10,
        #     min_wavelength=380 * 10,
        #     max_wavelength=640 * 10,
        #
        # )
        # c.set_ransac_properties(sample_size=5, top_n_candidate=5, filter_close=True)
        #
        # c.set_atlas(atlas, candidate_tolerance=5.0)
        #
        # c.do_hough_transform()
        #
        # # Run the wavelength calibration
        # (
        #     best_p,
        #     matched_peaks,
        #     matched_atlas,
        #     rms,
        #     residual,
        #     peak_utilisation,
        #     atlas_utilisation,
        # ) = c.fit(max_tries=5000)
        #
        # # Plot the solution
        # c.plot_fit(
        #     best_p, nanometersArrayFloat, plot_atlas=True, log_spectrum=False, tolerance=5.0
        # )
        #
        # pass

    def createAtlas(self):

        result=Atlas()

        spectralLineMasterDatasByNames = SpectralLineMasterDataUtil().createTransientSpectralLineMasterDatasByNames()

        spectralLinesToUse = [SpectralLineMasterDataColorName.MERCURY_FRENCH_VIOLET,
                              SpectralLineMasterDataColorName.MERCURY_BLUE,
                              SpectralLineMasterDataColorName.TERBIUM_AQUA,
                              SpectralLineMasterDataColorName.MERCURY_MANGO_GREEN,
                              SpectralLineMasterDataColorName.MERCURY_OR_TERBIUM_LEMON_GLACIER,
                              SpectralLineMasterDataColorName.EUROPIUM_MIDDLE_YELLOW,
                              SpectralLineMasterDataColorName.EUROPIUM_CYBER_YELLOW,
                              SpectralLineMasterDataColorName.EUROPIUM_AMBER,
                              SpectralLineMasterDataColorName.EUROPIUM_INTERNATIONAL_ORANGE,
                              SpectralLineMasterDataColorName.EUROPIUM_VIVID_GAMBOGE]

        spectralLineMasterDatasByNames = dict(
            map(lambda key: (key, spectralLineMasterDatasByNames.get(key, None)), spectralLinesToUse))


        elements=[]
        wavelengths=[]
        intensities=[]

        maxNanometer = 650
        # maxNanometer=740



        for spectralLineMasterData in spectralLineMasterDatasByNames.values():
            elements.append('Hg')
            nanometer=spectralLineMasterData.nanometer
            wavelengths.append(nanometer*10)
            intensities.append(spectralLineMasterData.intensity)

        elementsArray=np.asarray(elements,str)
        wavelengthsArray=np.asarray(wavelengths, float64)
        intensitiesArray = np.asarray(intensities, float64)

        result.add_user_atlas(elementsArray,wavelengthsArray,intensitiesArray)

        return result


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
        polynomialCoefficients=np.polyfit(np.array(pixelIndices),np.array(nanometers),3)

        model = self.getModel()
        model.interpolationCoefficientA=polynomialCoefficients[0]
        model.interpolationCoefficientB = polynomialCoefficients[1]
        model.interpolationCoefficientC = polynomialCoefficients[2]
        model.interpolationCoefficientD = polynomialCoefficients[3]

        return

    def __getSpectralLinesByPixelIndices_processSpectralLineTerbiumAqua(self):
        spectralLine =self.__getSpectralLineWithName(SpectralLineMasterDataColorName.TERBIUM_AQUA)
        self.__getSpectralLinesByPixelIndices_processSpectralLineByFindingBestColorMatch(spectralLine)
        self.__removePeak(spectralLine.pixelIndex)

    def __getSpectralLinesByPixelIndices_processSpectralLineMercuryFrenchViolet(self):
        spectralLine = self.__getSpectralLineWithName(SpectralLineMasterDataColorName.MERCURY_FRENCH_VIOLET)
        pixelIndex = list(self.__peaks.keys())[0]
        self.__getSpectralLinesByPixelIndices_processSpectralLineBySuppliedPixelIndex(spectralLine, pixelIndex)

    def __getSpectralLinesByPixelIndices_processSpectralLineMercuryBlue(self):
        spectralLine = self.__getSpectralLineWithName(SpectralLineMasterDataColorName.MERCURY_BLUE)
        pixelIndex = list(self.__peaks.keys())[1]
        self.__getSpectralLinesByPixelIndices_processSpectralLineBySuppliedPixelIndex(spectralLine, pixelIndex)

    def __getSpectralLinesByPixelIndices_processSpectralLineEuropiumVividGamboge(self):
        spectralLine = self.__getSpectralLineWithName(SpectralLineMasterDataColorName.EUROPIUM_VIVID_GAMBOGE)
        self.__getSpectralLinesByPixelIndices_processSpectralLineByFindingBestColorMatch(spectralLine)

    def __getSpectralLinesByPixelIndices_processSpectralLineEuropiumAmber(self):
        resultSpectralLine = self.__getSpectralLineWithName(SpectralLineMasterDataColorName.EUROPIUM_AMBER)
        referenceSpectralLine = self.__getDetectedSpectralLineOfName(SpectralLineMasterDataColorName.EUROPIUM_VIVID_GAMBOGE)
        self.__getSpectralLinesByPixelIndices_processSpectralLineGetSpectraLineOffsetToReferenceSpectralLine(
            resultSpectralLine,
            referenceSpectralLine, -1)

    def __getSpectralLinesByPixelIndices_processSpectralLineEuropiumCyberYellow(self):
        resultSpectralLine = self.__getSpectralLineWithName(SpectralLineMasterDataColorName.EUROPIUM_CYBER_YELLOW)
        referenceSpectralLine = self.__getDetectedSpectralLineOfName(SpectralLineMasterDataColorName.EUROPIUM_AMBER)
        self.__getSpectralLinesByPixelIndices_processSpectralLineGetSpectraLineOffsetToReferenceSpectralLine(
            resultSpectralLine,
            referenceSpectralLine, -1)

    def __getSpectralLinesByPixelIndices_processSpectralLineEuropiumMiddleYellow(self):
        resultSpectralLine = self.__getSpectralLineWithName(SpectralLineMasterDataColorName.EUROPIUM_MIDDLE_YELLOW)
        referenceSpectralLine = self.__getDetectedSpectralLineOfName(SpectralLineMasterDataColorName.EUROPIUM_CYBER_YELLOW)
        self.__getSpectralLinesByPixelIndices_processSpectralLineGetSpectraLineOffsetToReferenceSpectralLine(
            resultSpectralLine,
            referenceSpectralLine, -1)

    def __getSpectralLinesByPixelIndices_processSpectralLineMercuryMangoGreen(self):

        # The following heuristic strategy seems to work
        #   * limit the search to the area between 'TerbiumAqua' and 'EuropiumMiddleYellow'
        #   * limit this area to some middle region of this interval
        #   * collect the spectral lines matching 'MercuryMangoGreen' by color and sort by prominence
        #   * take the two SpectralLine/s with the highest prominences and take the right one

        spectralLine = self.__getSpectralLineWithName(SpectralLineMasterDataColorName.MERCURY_MANGO_GREEN)

        leftSpectralLine = self.__getDetectedSpectralLineOfName(SpectralLineMasterDataColorName.TERBIUM_AQUA)
        rightSpectralLine = self.__getDetectedSpectralLineOfName(SpectralLineMasterDataColorName.EUROPIUM_MIDDLE_YELLOW)

        leftSpectralLinePixelIndex = leftSpectralLine.pixelIndex
        rightSpectralLinePixelIndex = rightSpectralLine.pixelIndex
        width = rightSpectralLinePixelIndex - leftSpectralLinePixelIndex
        offsetWidth = width * 0.3

        startSpectralLinePixelIndex = leftSpectralLinePixelIndex + offsetWidth
        endSpectralLinePixelIndex = rightSpectralLinePixelIndex - offsetWidth

        matchingPixelIndices = []
        matchingSpectralLines: Dict[int, SpectralLine] = {}

        for someIndex in range(len(list(self.__peaks.keys()))):
            someColorPixelIndex = self.__getPeakMatchingSuppliedColorBest(spectralLine.spectralLineMasterData.nanometer)
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


        spectralLine = self.__getSpectralLineWithName(SpectralLineMasterDataColorName.EUROPIUM_RED)

        spectralLineEuropiumVividGamboge = self.__getDetectedSpectralLineOfName(SpectralLineMasterDataColorName.EUROPIUM_VIVID_GAMBOGE)
        spectralLineEuropiumMiddleYellow = self.__getDetectedSpectralLineOfName(SpectralLineMasterDataColorName.EUROPIUM_MIDDLE_YELLOW)

        leftSpectralLine = SpectralLine()
        leftSpectralLine.spectralLineMasterData=SpectralLineMasterData()
        offsetWidth = (spectralLineEuropiumVividGamboge.pixelIndex - spectralLineEuropiumMiddleYellow.pixelIndex) * 1.2
        leftSpectralLine.pixelIndex = spectralLineEuropiumVividGamboge.pixelIndex \
                                      + offsetWidth
        leftSpectralLine.color = ApplicationStyleLogicModule().getPrimaryColor()
        leftSpectralLine.spectralLineMasterData.name = 'leftSpectralLine'

        rightSpectralLine = SpectralLine()
        rightSpectralLine.spectralLineMasterData = SpectralLineMasterData()
        rightSpectralLine.pixelIndex = leftSpectralLine.pixelIndex + offsetWidth
        rightSpectralLine.color = ApplicationStyleLogicModule().getPrimaryColor()
        rightSpectralLine.spectralLineMasterData.name = 'rightSpectralLine'

        # self.__spectralLinesByPixelIndices[leftSpectralLine.pixelIndex] = leftSpectralLine
        # self.__spectralLinesByPixelIndices[rightSpectralLine.pixelIndex] = rightSpectralLine

        startSpectralLinePixelIndex = leftSpectralLine.pixelIndex
        endSpectralLinePixelIndex = rightSpectralLine.pixelIndex

        matchingPixelIndices = []
        matchingSpectralLines: Dict[int, SpectralLine] = {}

        # for someIndex in range(len(list(self.__peaks.keys()))):
        for somePixelIndex in list(self.__peaks.keys()):
            someColorPixelIndex = self.__getPeakMatchingSuppliedColorBest(spectralLine.spectralLineMasterData.nanometer,
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
        spectralLine = self.__getSpectralLineWithName(SpectralLineMasterDataColorName.EUROPIUM_INTERNATIONAL_ORANGE)

        spectralLineEuropiumVividGamboge = self.__getDetectedSpectralLineOfName(SpectralLineMasterDataColorName.EUROPIUM_VIVID_GAMBOGE)
        spectralLineEuropiumMiddleYellow = self.__getDetectedSpectralLineOfName(SpectralLineMasterDataColorName.EUROPIUM_MIDDLE_YELLOW)

        leftSpectralLine = self.__getDetectedSpectralLineOfName(SpectralLineMasterDataColorName.EUROPIUM_VIVID_GAMBOGE)
        rightSpectralLine = self.__getDetectedSpectralLineOfName(SpectralLineMasterDataColorName.EUROPIUM_RED)

        startSpectralLinePixelIndex = leftSpectralLine.pixelIndex
        endSpectralLinePixelIndex = rightSpectralLine.pixelIndex

        matchingPixelIndices = []
        matchingSpectralLines: Dict[int, SpectralLine] = {}

        # for someIndex in range(len(list(self.__peaks.keys()))):
        for somePixelIndex in list(self.__peaks.keys()):
            someColorPixelIndex = self.__getPeakMatchingSuppliedColorBest(spectralLine.spectralLineMasterData.nanometer,
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
        spectralLine.color = SpectralColorUtil().wavelengthToColor(spectralLine.spectralLineMasterData.nanometer)
        spectralLine.pixelIndex = self.__getPeakMatchingSuppliedColorBest(spectralLine.spectralLineMasterData.nanometer)
        self.__getSpectralLinesByPixelIndices_processSpectralLineBySuppliedPixelIndex(spectralLine,
                                                                                      spectralLine.pixelIndex);

    def __getDetectedSpectralLineOfName(self, spectralLineName) -> SpectralLine:
        result = None
        for pixelIndex, spectralLine in self.__spectralLinesByPixelIndices.items():
            if spectralLine.spectralLineMasterData.name == spectralLineName:
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

