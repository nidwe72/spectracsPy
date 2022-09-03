from typing import Dict
from PyQt6.QtGui import QImage, QColor


from base.Singleton import Singleton
from logic.spectral.util.SpectralColorUtil import SpectralColorUtil
from model.databaseEntity.spectral.device.SpectralLine import SpectralLine
class SpectrometerWavelengthCalibrationLogicModule(Singleton):

    spectralLinesByNames:Dict[str,SpectralLine]=None
    __peaks:Dict[int,int]=None
    __originalPeaks: Dict[int, int] = None
    __image:QImage=None

    __spectralLinesByPixelIndices:Dict[int,SpectralLine]=None

    def getSpectralLinesByNames(self):

        #https: // www.johndcook.com / wavelength_to_RGB.html
        #https://www.color-name.com/hex/00f6ff

        if self.spectralLinesByNames is None:

            self.spectralLinesByNames={}

            spectralLineMercuryFrenchViolet=SpectralLine()
            spectralLineMercuryFrenchViolet.name = 'MercuryFrenchViolet'
            spectralLineMercuryFrenchViolet.colorName='french violet'
            spectralLineMercuryFrenchViolet.mainColorName = 'violet'
            spectralLineMercuryFrenchViolet.nanometer =405.4
            spectralLineMercuryFrenchViolet.color = SpectralColorUtil().wavelengthToColor(
                spectralLineMercuryFrenchViolet.nanometer)
            self.spectralLinesByNames[spectralLineMercuryFrenchViolet.name]=spectralLineMercuryFrenchViolet

            spectralLineMercuryBlue=SpectralLine()
            spectralLineMercuryBlue.name = 'MercuryBlue'
            spectralLineMercuryBlue.colorName='blue'
            spectralLineMercuryBlue.mainColorName = 'blue'
            spectralLineMercuryBlue.nanometer =436.6
            spectralLineMercuryBlue.color = SpectralColorUtil().wavelengthToColor(
                spectralLineMercuryBlue.nanometer)
            self.spectralLinesByNames[spectralLineMercuryBlue.name]=spectralLineMercuryBlue

            spectralLineTerbiumAqua=SpectralLine()
            spectralLineTerbiumAqua.name = 'TerbiumAqua'
            spectralLineTerbiumAqua.colorName='aqua'
            spectralLineTerbiumAqua.mainColorName = 'cyan'
            spectralLineTerbiumAqua.nanometer =487.7
            spectralLineTerbiumAqua.color = SpectralColorUtil().wavelengthToColor(
                spectralLineTerbiumAqua.nanometer)
            spectralLineTerbiumAqua.color = SpectralColorUtil().wavelengthToColor(spectralLineTerbiumAqua.nanometer)
            self.spectralLinesByNames[spectralLineTerbiumAqua.name]=spectralLineTerbiumAqua

            spectralLineMercuryMangoGreen=SpectralLine()
            spectralLineMercuryMangoGreen.name = 'MercuryMangoGreen'
            spectralLineMercuryMangoGreen.colorName='mango green'
            spectralLineMercuryMangoGreen.mainColorName = 'green'
            spectralLineMercuryMangoGreen.nanometer =546.5
            spectralLineMercuryMangoGreen.color = SpectralColorUtil().wavelengthToColor(
                spectralLineMercuryMangoGreen.nanometer)
            spectralLineMercuryMangoGreen.color = SpectralColorUtil().wavelengthToColor(spectralLineMercuryMangoGreen.nanometer)
            self.spectralLinesByNames[spectralLineMercuryMangoGreen.name]=spectralLineMercuryMangoGreen

            spectralLinEuropiumMiddleYellow=SpectralLine()
            spectralLinEuropiumMiddleYellow.name = 'EuropiumMiddleYellow'
            spectralLinEuropiumMiddleYellow.colorName='middle yellow'
            spectralLinEuropiumMiddleYellow.mainColorName = 'yellow'
            spectralLinEuropiumMiddleYellow.nanometer =587.6
            spectralLinEuropiumMiddleYellow.color = SpectralColorUtil().wavelengthToColor(spectralLinEuropiumMiddleYellow.nanometer)
            self.spectralLinesByNames[spectralLinEuropiumMiddleYellow.name]=spectralLinEuropiumMiddleYellow

            spectralLinEuropiumCyberYellow=SpectralLine()
            spectralLinEuropiumCyberYellow.name = 'EuropiumCyberYellow'
            spectralLinEuropiumCyberYellow.colorName='cyber yellow'
            spectralLinEuropiumCyberYellow.mainColorName = 'yellow'
            spectralLinEuropiumCyberYellow.nanometer =593.4
            spectralLinEuropiumCyberYellow.color = SpectralColorUtil().wavelengthToColor(spectralLinEuropiumCyberYellow.nanometer)
            self.spectralLinesByNames[spectralLinEuropiumCyberYellow.name]=spectralLinEuropiumCyberYellow

            spectralLinEuropiumAmber=SpectralLine()
            spectralLinEuropiumAmber.name = 'EuropiumAmber'
            spectralLinEuropiumAmber.colorName='amber'
            spectralLinEuropiumAmber.mainColorName = 'yellow'
            spectralLinEuropiumAmber.nanometer =599.7
            spectralLinEuropiumAmber.color = SpectralColorUtil().wavelengthToColor(
                spectralLinEuropiumAmber.nanometer)
            self.spectralLinesByNames[spectralLinEuropiumAmber.name]=spectralLinEuropiumAmber

            spectralLinEuropiumVividGamboge=SpectralLine()
            spectralLinEuropiumVividGamboge.name = 'EuropiumVividGamboge'
            spectralLinEuropiumVividGamboge.colorName='vivid gamboge'
            spectralLinEuropiumVividGamboge.mainColorName = 'orange'
            spectralLinEuropiumVividGamboge.nanometer =611.6
            spectralLinEuropiumVividGamboge.color = SpectralColorUtil().wavelengthToColor(
                spectralLinEuropiumVividGamboge.nanometer)
            self.spectralLinesByNames[spectralLinEuropiumVividGamboge.name]=spectralLinEuropiumVividGamboge

            spectralLinEuropiumInternationalOrange=SpectralLine()
            spectralLinEuropiumInternationalOrange.name = 'EuropiumInternationalOrange'
            spectralLinEuropiumInternationalOrange.colorName='International Orange'
            spectralLinEuropiumInternationalOrange.mainColorName = 'orange'
            spectralLinEuropiumInternationalOrange.nanometer =631.1
            spectralLinEuropiumInternationalOrange.color = SpectralColorUtil().wavelengthToColor(
                spectralLinEuropiumInternationalOrange.nanometer)
            self.spectralLinesByNames[spectralLinEuropiumInternationalOrange.name]=spectralLinEuropiumInternationalOrange

            spectralLinEuropiumRed=SpectralLine()
            spectralLinEuropiumRed.name = 'EuropiumRed'
            spectralLinEuropiumRed.colorName='red'
            spectralLinEuropiumRed.mainColorName = 'red'
            spectralLinEuropiumRed.nanometer =650.8
            spectralLinEuropiumRed.color = SpectralColorUtil().wavelengthToColor(
                spectralLinEuropiumRed.nanometer)
            self.spectralLinesByNames[spectralLinEuropiumRed.name]=spectralLinEuropiumRed

        return self.spectralLinesByNames

    def getSpectralLinesByPixelIndicesPhaseOne(self)->Dict[int, SpectralLine]:
        self.__spectralLinesByPixelIndices={}
        self.__getSpectralLinesByPixelIndices_processSpectralLineEuropiumVividGamboge()

        return self.__spectralLinesByPixelIndices

    def getSpectralLinesByPixelIndicesPhaseTwo(self)->Dict[int, SpectralLine]:

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

        #self.__getSpectralLinesByPixelIndices_processSpectralLineEuropiumRed();
        return self.__spectralLinesByPixelIndices

    def __getSpectralLinesByPixelIndices_processSpectralLineTerbiumAqua(self):
        spectralLinesByNames = self.getSpectralLinesByNames();
        spectralLine= spectralLinesByNames['TerbiumAqua']
        self.__getSpectralLinesByPixelIndices_processSpectralLineByFindingBestColorMatch(spectralLine)
        self.__removePeak(spectralLine.pixelIndex)

    def __getSpectralLinesByPixelIndices_processSpectralLineMercuryFrenchViolet(self):
        spectralLinesByNames = self.getSpectralLinesByNames();
        spectralLine= spectralLinesByNames['MercuryFrenchViolet']
        pixelIndex=list(self.__peaks.keys())[0]
        self.__getSpectralLinesByPixelIndices_processSpectralLineBySuppliedPixelIndex(spectralLine,pixelIndex)

    def __getSpectralLinesByPixelIndices_processSpectralLineMercuryBlue(self):
        spectralLinesByNames = self.getSpectralLinesByNames();
        spectralLine= spectralLinesByNames['MercuryBlue']
        pixelIndex=list(self.__peaks.keys())[1]
        self.__getSpectralLinesByPixelIndices_processSpectralLineBySuppliedPixelIndex(spectralLine,pixelIndex)

    def __getSpectralLinesByPixelIndices_processSpectralLineEuropiumVividGamboge(self):
        spectralLinesByNames = self.getSpectralLinesByNames();
        spectralLine= spectralLinesByNames['EuropiumVividGamboge']
        self.__getSpectralLinesByPixelIndices_processSpectralLineByFindingBestColorMatch(spectralLine)

    def __getSpectralLinesByPixelIndices_processSpectralLineEuropiumRed(self):
        spectralLinesByNames = self.getSpectralLinesByNames();
        spectralLine= spectralLinesByNames['EuropiumRed']
        self.__getSpectralLinesByPixelIndices_processSpectralLineByFindingBestColorMatch(spectralLine)

    def __getSpectralLinesByPixelIndices_processSpectralLineEuropiumAmber(self):
        spectralLinesByNames = self.getSpectralLinesByNames();
        resultSpectralLine= spectralLinesByNames['EuropiumAmber']
        referenceSpectralLine=self.__getDetectedSpectralLineOfName('EuropiumVividGamboge')
        self.__getSpectralLinesByPixelIndices_processSpectralLineGetSpectraLineOffsetToReferenceSpectralLine(resultSpectralLine,
                                                                                                                referenceSpectralLine,-1)
    def __getSpectralLinesByPixelIndices_processSpectralLineEuropiumCyberYellow(self):
        spectralLinesByNames = self.getSpectralLinesByNames();
        resultSpectralLine= spectralLinesByNames['EuropiumCyberYellow']
        referenceSpectralLine=self.__getDetectedSpectralLineOfName('EuropiumAmber')
        self.__getSpectralLinesByPixelIndices_processSpectralLineGetSpectraLineOffsetToReferenceSpectralLine(resultSpectralLine,
                                                                                                                referenceSpectralLine,-1)
    def __getSpectralLinesByPixelIndices_processSpectralLineEuropiumMiddleYellow(self):
        spectralLinesByNames = self.getSpectralLinesByNames();
        resultSpectralLine= spectralLinesByNames['EuropiumMiddleYellow']
        referenceSpectralLine=self.__getDetectedSpectralLineOfName('EuropiumCyberYellow')
        self.__getSpectralLinesByPixelIndices_processSpectralLineGetSpectraLineOffsetToReferenceSpectralLine(resultSpectralLine,
                                                                                                                referenceSpectralLine,-1)


    def __getSpectralLinesByPixelIndices_processSpectralLineMercuryMangoGreen(self):

        #The following heuristic strategy seems to work
        #   limit the search to the area between 'TerbiumAqua' and 'EuropiumMiddleYellow'
        #   limit this area to some middle region of this interval
        #   collect the spectral lines matching 'MercuryMangoGreen' by color
        #   the SpectralLine with the highest pixel index is taken
        #       attention: this only works if there is no peak right to 'MercuryMangoGreen'.
        #       For now this assumption seems to hold. Probably it would make sense to take into account
        #       also green line prominences.

        spectralLinesByNames = self.getSpectralLinesByNames();
        spectralLine= spectralLinesByNames['MercuryMangoGreen']

        leftSpectralLine=self.__getDetectedSpectralLineOfName('TerbiumAqua')
        rightSpectralLine = self.__getDetectedSpectralLineOfName('EuropiumMiddleYellow')

        leftSpectralLinePixelIndex = leftSpectralLine.pixelIndex
        rightSpectralLinePixelIndex = rightSpectralLine.pixelIndex
        width = rightSpectralLinePixelIndex - leftSpectralLinePixelIndex
        offsetWidth = width * 0.3

        startSpectralLinePixelIndex = leftSpectralLinePixelIndex + offsetWidth
        endSpectralLinePixelIndex = rightSpectralLinePixelIndex - offsetWidth

        matchingPixelIndices = []
        for index in range(len(list(self.__peaks.keys()))):
            somePixelIndex = self.getPeakMatchingSuppliedColorBest(spectralLine.nanometer)
            if somePixelIndex > startSpectralLinePixelIndex and somePixelIndex < endSpectralLinePixelIndex:
                matchingPixelIndices.append(somePixelIndex)
                self.__removePeak(somePixelIndex)
            elif somePixelIndex > leftSpectralLinePixelIndex and somePixelIndex < rightSpectralLinePixelIndex:
                self.__removePeak(somePixelIndex)

        lastMatchingPixelIndex=max(matchingPixelIndices)
        spectralLine.pixelIndex = lastMatchingPixelIndex
        self.__spectralLinesByPixelIndices[lastMatchingPixelIndex] = spectralLine

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

    def __getSpectralLinesByPixelIndices_processSpectralLineBySuppliedPixelIndex(self,spectralLine:SpectralLine,pixelIndex:int):
        spectralLine.pixelIndex=pixelIndex
        self.__spectralLinesByPixelIndices[pixelIndex] = spectralLine
        self.__removePeak(spectralLine.pixelIndex)


    def __getSpectralLinesByPixelIndices_processSpectralLineByFindingBestColorMatch(self,spectralLine:SpectralLine):
        spectralLine.color=SpectralColorUtil().wavelengthToColor(spectralLine.nanometer)
        spectralLine.pixelIndex=self.getPeakMatchingSuppliedColorBest(spectralLine.nanometer)
        self.__getSpectralLinesByPixelIndices_processSpectralLineBySuppliedPixelIndex(spectralLine,spectralLine.pixelIndex);

    def __getDetectedSpectralLineOfName(self,spectralLineName)->SpectralLine:
        result=None
        for pixelIndex,spectralLine in self.__spectralLinesByPixelIndices.items():
            if spectralLine.name==spectralLineName:
                result=spectralLine
                break
        return result

    def __getPeaksBetweenSuppliedSpectralLines(self,leftSpectralLine:SpectralLine,rightSpectralLine:SpectralLine):
        result=[]
        leftSpectralLinePixelIndex=leftSpectralLine.pixelIndex
        rightSpectralLinePixelIndex = rightSpectralLine.pixelIndex
        for peak in list(self.__peaks.values()):
            if peak>leftSpectralLinePixelIndex and peak<rightSpectralLinePixelIndex:
                result.append(peak)
        return result

    def setPeaks(self,peaks:Dict[int,int]):
        self.__peaks=peaks.copy()
        self.__originalPeaks = peaks.copy()

    def setImage(self,image:QImage):
        self.__image=image

    def getPeakMatchingSuppliedColorBest(self,wavelength):
        suppliedColor=SpectralColorUtil().wavelengthToColor(wavelength)
        distancesByPixelIndices={}
        for peak in self.__peaks:
            #todo:hard-coded
            pixelColor=self.__image.pixelColor(peak,392)
            colorDifference=SpectralColorUtil().getColorDifference(suppliedColor,pixelColor)
            distancesByPixelIndices[peak]=colorDifference
            continue
        foo= sorted(distancesByPixelIndices.items(), key=lambda x: x[1])
        result=foo[0][0]
        return result

    def __removePeak(self,peak:int):
        try:
            self.__peaks.pop(peak)
        except KeyError:
            pass



