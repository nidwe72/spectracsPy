from typing import Dict
from typing import List

import numpy as np
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPixmap, QPen, QBrush

from logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModule import ImageSpectrumAcquisitionLogicModule
from logic.spectral.acquisition.ImageSpectrumAcquisitionLogicModuleParameters import \
    ImageSpectrumAcquisitionLogicModuleParameters
from logic.spectral.acquisition.device.calibration.SpectrometerWavelengthCalibrationLogicModule import \
    SpectrometerWavelengthCalibrationLogicModule
from logic.spectral.acquisition.device.calibration.SpectrometerWavelengthCalibrationLogicModuleParameters import \
    SpectrometerWavelengthCalibrationLogicModuleParameters
from logic.spectral.acquisition.device.calibration.SpectrometerWavelengthCalibrationLogicModuleResult import \
    SpectrometerWavelengthCalibrationLogicModuleResult
from logic.spectral.util.SpectralColorUtil import SpectralColorUtil
from logic.spectral.util.SpectrallineUtil import SpectralLineUtil
from logic.spectral.util.SpectrumUtil import SpectrumUtil
from model.databaseEntity.spectral.device import SpectrometerCalibrationProfile
from model.databaseEntity.spectral.device.SpectralLine import SpectralLine
from model.signal.SpectrometerCalibrationProfileHoughLinesVideoSignal import \
    SpectrometerCalibrationProfileHoughLinesVideoSignal
from model.signal.SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal import \
    SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal
from model.spectral.Spectrum import Spectrum
from model.spectral.SpectrumSampleType import SpectrumSampleType
from view.application.widgets.graphicsScene.BaseGraphicsLineItem import BaseGraphicsLineItem
from view.application.widgets.video.BaseVideoViewModule import BaseVideoViewModule


from scipy.signal import find_peaks, peak_prominences


class SpectrometerCalibrationProfileWavelengthCalibrationVideoViewModule(
    BaseVideoViewModule[SpectrometerCalibrationProfileHoughLinesVideoSignal]):
    __model: SpectrometerCalibrationProfile = None

    peaksClusters:Dict[int,List[SpectralLine]]=None

    prominence:int=0
    prominenceStart:int=200
    prominenceEnd: int = 20
    prominenceStep=10

    phaseZeroInExecution:bool=False

    phaseOneInExecution: bool = False
    phaseOneCurrentStep=0
    phaseOneStepsCount=40

    phaseTwoInExecution: bool = False

    spectralLinesByPixelIndices:Dict[int,SpectralLine]=None

    spectrometerWavelengthCalibrationLogicModule:SpectrometerWavelengthCalibrationLogicModule = None

    __spectrum:Spectrum=None

    @property
    def spectrum(self):
        return self.__spectrum

    @spectrum.setter
    def spectrum(self, spectrum):
        self.__spectrum=spectrum

    def handleVideoThreadSignal(self, videoSignal: SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal):

        peaks=None

        for item in self.scene.items():
            if isinstance(item, BaseGraphicsLineItem):
                self.scene.removeItem(item)

        if videoSignal.currentFrameIndex==1:
            self.spectrum=Spectrum()

        spectrometerWavelengthCalibrationLogicModuleResult:SpectrometerWavelengthCalibrationLogicModuleResult=None

        if videoSignal.currentFrameIndex==videoSignal.framesCount:

            videoSignal.spectrum=self.spectrum

            spectrometerWavelengthCalibrationLogicModule = SpectrometerWavelengthCalibrationLogicModule()
            spectrometerWavelengthCalibrationLogicModuleParameters = SpectrometerWavelengthCalibrationLogicModuleParameters()
            spectrometerWavelengthCalibrationLogicModule.moduleParameters = spectrometerWavelengthCalibrationLogicModuleParameters
            spectrometerWavelengthCalibrationLogicModuleParameters.videoSignal=videoSignal
            spectrometerWavelengthCalibrationLogicModuleResult = spectrometerWavelengthCalibrationLogicModule.execute()

        else:


            imageAcquisitionLogicModule = ImageSpectrumAcquisitionLogicModule()
            logicModuleParameters = ImageSpectrumAcquisitionLogicModuleParameters()
            logicModuleParameters.setVideoSignal(videoSignal)
            logicModuleParameters.spectrum=self.spectrum
            logicModuleParameters.setAcquireColors(True)
            imageAcquisitionLogicModule.execute(logicModuleParameters)

            SpectrumUtil().mean(self.spectrum)
            SpectrumUtil().smooth(self.spectrum)

            for prominence in range(1, 100):
                peaks, _ = find_peaks(list(self.spectrum.valuesByNanometers.values()), distance=3, width=3, rel_height=0.5, prominence=prominence)
                if len(peaks) == 10:
                    break

            #debugPurpose
            # plt.title("spectrum")
            # plt.xlabel("X axis")
            # plt.ylabel("Y axis")
            # plt.plot(list(self.spectrum.valuesByNanometers.keys()), list(self.spectrum.valuesByNanometers.values()), color="blue")
            # plt.show()


        image = videoSignal.image
        somePixmap = QPixmap.fromImage(image)
        self.imageItem.setPixmap(somePixmap)


        if peaks is not None:

            # debugPurpose
            # print('peaks')
            # print(peaks.tolist())

            for peakIndex in peaks.tolist():
                lineItem = BaseGraphicsLineItem()
                lineItem.setLine(peakIndex, 0, peakIndex, videoSignal.image.height())
                pen = QPen(QBrush(Qt.white), 1)
                pen.setStyle(Qt.PenStyle.DotLine)
                lineItem.setPen(pen)

                self.scene.addItem(lineItem)

        if spectrometerWavelengthCalibrationLogicModuleResult is not None:
            spectralLines = spectrometerWavelengthCalibrationLogicModuleResult.getSpectralLines()
            for spectralLine in spectralLines:
                lineItem = BaseGraphicsLineItem()
                lineItem.setLine(spectralLine.pixelIndex, 0, spectralLine.pixelIndex, videoSignal.image.height())
                pen = QPen(QBrush(Qt.white), 3)
                pen.setStyle(Qt.PenStyle.DotLine)
                lineItem.setPen(pen)

                self.scene.addItem(lineItem)

        self._fitInView()
        return


    def handleVideoThreadSignalOld(self, videoSignal: SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal):

        if videoSignal.currentFrameIndex==1:
            self.phaseZeroInExecution = True
            self.phaseOneInExecution = False
            self.phaseTwoInExecution = False
            self.prominence=self.prominenceStart
            self.spectralLinesByPixelIndices = {}
            self.peaksClusters:Dict[int,List[SpectralLine]]={}
            self.phaseOneCurrentStep = 0

        for item in self.scene.items():
            if isinstance(item,BaseGraphicsLineItem):
                self.scene.removeItem(item)


        image = videoSignal.image
        somePixmap = QPixmap.fromImage(image)
        self.imageItem.setPixmap(somePixmap)

        if self.phaseZeroInExecution:
            self.prominence=self.prominence-self.prominenceStep

        spectralPeaks=self.__getSpectralPeaks(videoSignal)

        if len(spectralPeaks)>=3 and self.phaseZeroInExecution:
            self.phaseZeroInExecution = False
            self.phaseOneInExecution = True

        # print('-----step-----')
        # print(peaksList)
        # print(prominences)

        for peakIndex,spectralPeak in spectralPeaks.items():
            if self.phaseOneInExecution or self.phaseTwoInExecution:
                self.__assignToPeakCluster(spectralPeak)

            lineItem = BaseGraphicsLineItem()
            lineItem.setLine(peakIndex,0,peakIndex,image.height())
            self.scene.addItem(lineItem)

        if self.phaseOneInExecution:
            self.phaseOneCurrentStep=self.phaseOneCurrentStep+1

        if self.phaseOneCurrentStep>self.phaseOneStepsCount:
            if self.phaseOneInExecution:
                peaks = self.getPeaks(3)
                if self.spectrometerWavelengthCalibrationLogicModule is None:
                    self.spectrometerWavelengthCalibrationLogicModule = SpectrometerWavelengthCalibrationLogicModule()
                self.spectrometerWavelengthCalibrationLogicModule.setModel(self.getModel())
                self.spectrometerWavelengthCalibrationLogicModule.setPeaks(peaks)
                self.spectrometerWavelengthCalibrationLogicModule.setImage(image)
                self.spectralLinesByPixelIndices = self.spectrometerWavelengthCalibrationLogicModule.getSpectralLinesByPixelIndicesPhaseOne()

                self.phaseOneInExecution = False
                self.phaseTwoInExecution = True
                self.prominence=self.prominenceEnd

        if self.phaseTwoInExecution:
            print()
            for peakPixelIndex,spectralLine in self.spectralLinesByPixelIndices.items():
                lineItem = BaseGraphicsLineItem()
                lineItem.setLine(peakPixelIndex, 0, peakPixelIndex, image.height())
                pen = QPen(QBrush(spectralLine.color), 3)
                pen.setStyle(Qt.PenStyle.DotLine)
                lineItem.setPen(pen)
                self.scene.addItem(lineItem)


        if videoSignal.currentFrameIndex>videoSignal.framesCount-1:
            self.removeNotSeparatedPeakClusters()

            for item in self.scene.items():
                if isinstance(item,BaseGraphicsLineItem):
                    self.scene.removeItem(item)

            peaks = self.getPeaks()
            self.spectrometerWavelengthCalibrationLogicModule.setPeaks(peaks)
            self.spectrometerWavelengthCalibrationLogicModule.setImage(image)
            self.spectralLinesByPixelIndices = self.spectrometerWavelengthCalibrationLogicModule.getSpectralLinesByPixelIndicesPhaseTwo()

            for peakPixelIndex in list(peaks.keys()):
                lineItem = BaseGraphicsLineItem()
                lineItem.setLine(peakPixelIndex, 0, peakPixelIndex, image.height())
                pen = QPen(QBrush(ApplicationStyleLogicModule().getPrimaryTextColor()), 1)

                pen.setStyle(Qt.PenStyle.DotLine)
                lineItem.setPen(pen)

                self.scene.addItem(lineItem)

            for peakPixelIndex,spectralLine in self.spectralLinesByPixelIndices.items():
                lineItem = BaseGraphicsLineItem()
                lineItem.setLine(peakPixelIndex, 0, peakPixelIndex, image.height())
                pen = QPen(QBrush(SpectralColorUtil().wavelengthToColor(spectralLine.spectralLineMasterData.nanometer)), 3)
                pen.setStyle(Qt.PenStyle.DotLine)
                lineItem.setPen(pen)
                self.scene.addItem(lineItem)

            videoSignal.model=self.spectrometerWavelengthCalibrationLogicModule.getModel()

        self._fitInView()

    def _fitInView(self):
        regionOfInterestY2 = self.getModel().regionOfInterestY2
        if regionOfInterestY2 is not None:

            topLeft=QPointF(0, regionOfInterestY2)
            if topLeft is not None:

                imageWidth = self.imageItem.pixmap().width()
                if imageWidth>0:
                    bottomRight = QPointF(imageWidth, self.getModel().regionOfInterestY1)
                    fitRectangle = QRectF()
                    fitRectangle.setBottomLeft(topLeft)
                    fitRectangle.setBottomRight(bottomRight)
                    self.videoWidget.fitInView(fitRectangle, Qt.AspectRatioMode.KeepAspectRatio)
                    self.videoWidget.centerOn(topLeft)
                    self.videoWidget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        else:
            super()._fitInView()

    def __getSpectralPeaks(self,videoSignal: SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal)->Dict[int,SpectralLine]:
        result= {}
        spectra = videoSignal.spectralJob.getSpectra(SpectrumSampleType.UNSPECIFIED)
        spectrum=spectra[-1]
        spectrumValuesNpArray=np.array(list(spectrum.valuesByNanometers.values()))
        peaks, _ = find_peaks(spectrumValuesNpArray, distance=10, height=10, width=3, rel_height=1,prominence=self.prominence)
        prominences = peak_prominences(spectrumValuesNpArray, peaks)[0]

        for somePeak, someProminence in zip(peaks, prominences):
            spectralPeak=SpectralLine()
            spectralPeak.pixelIndex=somePeak.item()
            spectralPeak.prominence = someProminence.item()
            result[spectralPeak.pixelIndex]=spectralPeak

        return result


    def __assignToPeakCluster(self, spectralPeak:SpectralLine):
        minimalPeakGap=15
        clusterPeakIndex=None
        for somePeakIndex,someSpectralPeak in self.peaksClusters.items():
            if abs(somePeakIndex-spectralPeak.pixelIndex)<minimalPeakGap:
                clusterPeakIndex=somePeakIndex
                break

        if clusterPeakIndex is None:
            clusterPeakIndex=spectralPeak.pixelIndex
            self.peaksClusters[clusterPeakIndex] = []

        cluster=self.peaksClusters[clusterPeakIndex]
        cluster.append(spectralPeak)
        self.peaksClusters[clusterPeakIndex] = cluster

    def removeNotSeparatedPeakClusters(self):
        minimalClusterDistance=10
        clusterIndices = list(self.peaksClusters.keys())
        custerIndicesToRemove=[]
        for clusterIndexToCheck in clusterIndices:
            for someClusterIndexToCheck in clusterIndices:
                someClusterDistance=abs(clusterIndexToCheck-someClusterIndexToCheck)
                if someClusterDistance>0 and someClusterDistance<minimalClusterDistance:
                    custerIndicesToRemove.append(clusterIndexToCheck)
                    break
        for custerIndexToRemove in custerIndicesToRemove:
            self.peaksClusters.pop(custerIndexToRemove)

    def getPeaks(self,prominencesCount=0)->Dict[int,SpectralLine]:
        result= {}

        for someClusterIndex,spectralPeaksOfCluster in self.peaksClusters.items():
            pixelIndicesOfCluster=[]
            prominencesOfCluster=[]
            for spectralPeak in spectralPeaksOfCluster:
                pixelIndicesOfCluster.append(spectralPeak.pixelIndex)
                prominencesOfCluster.append(spectralPeak.prominence)

            meanPixelIndex = int(np.array(pixelIndicesOfCluster).mean())
            meanProminence=float(np.array(prominencesOfCluster).mean())

            meanSpectralPeak=SpectralLine()
            meanSpectralPeak.pixelIndex=meanPixelIndex
            meanSpectralPeak.prominence = meanProminence

            result[meanPixelIndex]=meanSpectralPeak

        meanResult = dict(sorted(result.items()))

        if prominencesCount==0:
            result=meanResult
        else:
            result={}
            spectralLinesByProminences=SpectralLineUtil().sortSpectralLinesByProminences(list(meanResult.values()));
            index=0
            for spectralLine in spectralLinesByProminences:
                if index>=prominencesCount:
                    break
                result[spectralLine.pixelIndex]=spectralLine
                index=index+1

        return result

    def getDistancesBetweenNeighboursByPeakIndices(self):
        peaks=list(self.getPeaks().values())

        distancesMap={}

        for iterateIndex, peakIndex in enumerate(peaks):

            distance = 999
            if iterateIndex==0 or iterateIndex==len(peaks)-1 :
                distance=999
            else:
                leftPeakIndex=peaks[iterateIndex-1]
                rightPeakIndex=peaks[iterateIndex+1]
                distance=rightPeakIndex-leftPeakIndex

            distancesMap[peakIndex]=distance

        result = sorted(distancesMap.items(), key=lambda x: x[1])

        return result

    def initialize(self):
        super().initialize()

    def setModel(self,model: SpectrometerCalibrationProfile):
        self.__model=model
        if self.spectrometerWavelengthCalibrationLogicModule is None:
            self.spectrometerWavelengthCalibrationLogicModule = SpectrometerWavelengthCalibrationLogicModule()
        self.spectrometerWavelengthCalibrationLogicModule.setModel(model)

    def getModel(self)->SpectrometerCalibrationProfile:
        return self.__model


