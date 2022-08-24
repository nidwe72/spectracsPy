from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPen, QBrush

from typing import Dict
from typing import List

from scipy import signal

from logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from model.signal.SpectrometerCalibrationProfileHoughLinesVideoSignal import \
    SpectrometerCalibrationProfileHoughLinesVideoSignal
from model.signal.SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal import \
    SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal
from model.spectral.SpectralLine import SpectralLine
from model.spectral.SpectrumSampleType import SpectrumSampleType
from view.application.widgets.graphicsScene.BaseGraphicsLineItem import BaseGraphicsLineItem
from view.application.widgets.video.BaseVideoViewModule import BaseVideoViewModule

from scipy.signal import find_peaks
from scipy.signal import peak_prominences

from scipy.signal import find_peaks_cwt


import peakutils

import numpy as np

class SpectrometerCalibrationProfileWavelengthCalibrationVideoViewModule(
    BaseVideoViewModule[SpectrometerCalibrationProfileHoughLinesVideoSignal]):

    peaksClusters:Dict[int,List[int]]=None

    def handleVideoThreadSignal(self, videoSignal: SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal):

        if videoSignal.currentFrameIndex==1:
            self.peaksClusters={}

        image = videoSignal.image
        scene = self.videoWidget.scene()
        somePixmap = QPixmap.fromImage(image)
        self.imageItem.setPixmap(somePixmap)

        spectra = videoSignal.spectralJob.getSpectra(SpectrumSampleType.UNSPECIFIED)
        spectrum=spectra[-1]

        spectrumValuesNpArray=np.array(list(spectrum.valuesByNanometers.values()))


        #spectrum = electrocardiogram()[2000:4000]

        #peaks, _ = find_peaks(spectrumValuesNpArray, prominence = 1, width = 20)

        #,plateau_size=3


        peaks, _ = find_peaks(spectrumValuesNpArray, distance=20, height=10, width=3, rel_height=1,prominence=20)

        #peaks, _ = find_peaks(spectrumValuesNpArray, distance=20,height=10,width=5,threshold=1)

        prominences = peak_prominences(spectrumValuesNpArray, peaks)[0]

        foo=spectrumValuesNpArray[peaks]-prominences

        bar=spectrumValuesNpArray[peaks]

        peaksList=peaks.tolist()



        #peaksList = peakutils.indexes(spectrumValuesNpArray, thres=0.5, min_dist=30)

        #peaksList = peakutils.indexes(spectrumValuesNpArray, thres=0.1, min_dist=30)

        #peaksList = peakutils.indexes(spectrumValuesNpArray, thres=0.8, min_dist=30)

        print(peaksList)

        for peakIndex in peaksList:
            self.assignToPeakCuster(peakIndex)

            lineItem = BaseGraphicsLineItem()
            lineItem.setLine(peakIndex,0,peakIndex,image.height())
            self.scene.addItem(lineItem)

        if videoSignal.currentFrameIndex>videoSignal.framesCount-1:
            self.removeNotSeparatedPeakClusters()
            for item in self.scene.items():
                if isinstance(item,BaseGraphicsLineItem):
                    self.scene.removeItem(item)

            #yellow//10//593

            distances = self.getDistancesBetweenNeighboursByPeakIndices()
            threeDistances = dict(list(distances)[:3])

            self.getSpectralLinesByPixelIndices()

            for peak in list(self.getPeaks().values()):
                lineItem = BaseGraphicsLineItem()
                lineItem.setLine(peak, 0, peak, image.height())
                pen = QPen(QBrush(ApplicationStyleLogicModule().getPrimaryColor()), 1)

                if threeDistances.get(peak) is not None:
                    pen = QPen(QBrush(ApplicationStyleLogicModule().getPrimaryTextColor()), 1)

                pen.setStyle(Qt.PenStyle.DotLine)
                lineItem.setPen(pen)

                self.scene.addItem(lineItem)

            print('self.peaksClusters')
            print(self.peaksClusters)

        self.videoWidget.fitInView(self.imageItem, Qt.AspectRatioMode.KeepAspectRatio)

    def assignToPeakCuster(self,peakIndex):
        minimalPeakGap=10
        clusterPeakIndex=None
        for somePeakIndex in list(self.peaksClusters.keys()):
            if abs(somePeakIndex-peakIndex)<minimalPeakGap:
                clusterPeakIndex=somePeakIndex
                break

        if clusterPeakIndex is None:
            clusterPeakIndex=peakIndex
            self.peaksClusters[clusterPeakIndex] = []

        cluster=self.peaksClusters[clusterPeakIndex]
        cluster.append(peakIndex)
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

    def getPeaks(self)->Dict[int,int]:
        result= {}
        for someClusterIndex,cluster in self.peaksClusters.items():
            mean = int(np.array(cluster).mean())
            result[mean]=mean

        result=dict(sorted(result.items()))
        return result

    def getSpectralLinesByPixelIndices(self)->Dict[int,SpectralLine]:

        #https: // www.johndcook.com / wavelength_to_RGB.html
        #https://www.color-name.com/hex/00f6ff

        result={}

        #405.4//mercuryPurple//8200c9//French Violet(violet)
        #436.6//mercury//1a00ff//Blue(blue)
        #487.7//#00f6ff//terbium//aqua (cyan)//Aquamarin

        #xxx#542.4//8aff00//Chartreuse (Web) (green)//Kräuterlikör-Grün
        #546.5//mercury//97ff00//Mango Green (green)
        #587.6//europium//Middle Yellow(yellow)
        #593.4//europium//Cyber Yellow(yellow)
        #599.7//europium//ffbf00//Amber(yellow)//Bernstein//
        #611.6//ff9600//Vivid Gamboge(orange)//Lebendiges Gelb-Orange
        #631.1//International Orange (Aerospace)//orange
        #650.8//Red

        peaks = self.getPeaks()

        distances = self.getDistancesBetweenNeighboursByPeakIndices()
        threeDistances = dict(list(distances)[:3])
        threeDistancesPixelIndices = list(dict(list(distances)[:3]).keys())

        spectralLineMercuryMiddleYellow=SpectralLine()
        spectralLineMercuryMiddleYellow.colorName='middle yellow'
        spectralLineMercuryMiddleYellow.mainColorName = 'yellow'
        spectralLineMercuryMiddleYellow.nanometer =587.6
        spectralLineMercuryMiddleYellow.pixelIndex = threeDistancesPixelIndices[0]
        result[spectralLineMercuryMiddleYellow.pixelIndex]=spectralLineMercuryMiddleYellow


        spectralLineMercuryFrenchViolet=SpectralLine()
        spectralLineMercuryFrenchViolet.colorName='french violet'
        spectralLineMercuryFrenchViolet.mainColorName = 'violet'





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



