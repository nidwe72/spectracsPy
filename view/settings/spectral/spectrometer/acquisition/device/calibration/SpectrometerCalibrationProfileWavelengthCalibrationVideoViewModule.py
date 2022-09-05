from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPen, QBrush, QColor, QImage

from typing import Dict
from typing import List
from typing import Tuple

from logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from logic.spectral.acquisition.device.calibration.SpectrometerWavelengthCalibrationLogicModule import \
    SpectrometerWavelengthCalibrationLogicModule
from model.signal.SpectrometerCalibrationProfileHoughLinesVideoSignal import \
    SpectrometerCalibrationProfileHoughLinesVideoSignal
from model.signal.SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal import \
    SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal
from model.databaseEntity.spectral.device.SpectralLine import SpectralLine
from model.spectral.SpectralPeak import SpectralPeak
from model.spectral.SpectrumSampleType import SpectrumSampleType
from view.application.widgets.graphicsScene.BaseGraphicsLineItem import BaseGraphicsLineItem
from view.application.widgets.video.BaseVideoViewModule import BaseVideoViewModule

from scipy.signal import find_peaks
from scipy.signal import peak_prominences


import numpy as np


class SpectrometerCalibrationProfileWavelengthCalibrationVideoViewModule(
    BaseVideoViewModule[SpectrometerCalibrationProfileHoughLinesVideoSignal]):

    peaksClusters:Dict[int,List[SpectralPeak]]=None

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

    def handleVideoThreadSignal(self, videoSignal: SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal):

        if videoSignal.currentFrameIndex==1:
            self.phaseZeroInExecution = True
            self.phaseOneInExecution = False
            self.phaseTwoInExecution = False
            self.prominence=self.prominenceStart
            self.spectralLinesByPixelIndices = {}
            self.peaksClusters:Dict[int,List[SpectralPeak]]={}
            self.phaseOneCurrentStep = 0

            for item in self.scene.items():
                if isinstance(item,BaseGraphicsLineItem):
                    self.scene.removeItem(item)


        image = videoSignal.image
        scene = self.videoWidget.scene()
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
                peaks = self.getPeaks()
                self.spectrometerWavelengthCalibrationLogicModule = SpectrometerWavelengthCalibrationLogicModule()
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
                pen = QPen(QBrush(spectralLine.color), 3)
                pen.setStyle(Qt.PenStyle.DotLine)
                lineItem.setPen(pen)
                self.scene.addItem(lineItem)

        self.videoWidget.fitInView(self.imageItem, Qt.AspectRatioMode.KeepAspectRatio)


    def __getSpectralPeaks(self,videoSignal: SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal)->Dict[int,SpectralPeak]:
        result= {}
        spectra = videoSignal.spectralJob.getSpectra(SpectrumSampleType.UNSPECIFIED)
        spectrum=spectra[-1]
        spectrumValuesNpArray=np.array(list(spectrum.valuesByNanometers.values()))
        peaks, _ = find_peaks(spectrumValuesNpArray, distance=10, height=10, width=3, rel_height=1,prominence=self.prominence)
        prominences = peak_prominences(spectrumValuesNpArray, peaks)[0]
        peaksList=peaks.tolist()

        for somePeak, someProminence in zip(peaks, prominences):
            spectralPeak=SpectralPeak()
            spectralPeak.pixelIndex=somePeak.item()
            spectralPeak.prominence = someProminence.item()
            result[spectralPeak.pixelIndex]=spectralPeak

        return result


    def __assignToPeakCluster(self, spectralPeak:SpectralPeak):
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

    def getPeaks(self)->Dict[int,SpectralPeak]:
        result= {}
        for someClusterIndex,spectralPeaksOfCluster in self.peaksClusters.items():
            pixelIndicesOfCluster=[]
            prominencesOfCluster=[]
            for spectralPeak in spectralPeaksOfCluster:
                pixelIndicesOfCluster.append(spectralPeak.pixelIndex)
                prominencesOfCluster.append(spectralPeak.prominence)

            meanPixelIndex = int(np.array(pixelIndicesOfCluster).mean())
            meanProminence=float(np.array(prominencesOfCluster).mean())

            meanSpectralPeak=SpectralPeak()
            meanSpectralPeak.pixelIndex=meanPixelIndex
            meanSpectralPeak.prominence = meanProminence

            result[meanPixelIndex]=meanSpectralPeak

        result = dict(sorted(result.items()))

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


