from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPen, QBrush

from typing import Dict
from typing import List

from logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from model.signal.SpectrometerCalibrationProfileHoughLinesVideoSignal import \
    SpectrometerCalibrationProfileHoughLinesVideoSignal
from model.signal.SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal import \
    SpectrometerCalibrationProfileWavelengthCalibrationVideoSignal
from model.spectral.SpectrumSampleType import SpectrumSampleType
from view.application.widgets.graphicsScene.BaseGraphicsLineItem import BaseGraphicsLineItem
from view.application.widgets.video.BaseVideoViewModule import BaseVideoViewModule

from scipy.signal import find_peaks


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

        peaks, _ = find_peaks(spectrumValuesNpArray, prominence = 1, width = 20)
        peaksList=peaks.tolist()

        #peaksList = peakutils.indexes(spectrumValuesNpArray, thres=0.5, min_dist=30)

        peaksList = peakutils.indexes(spectrumValuesNpArray, thres=0.1, min_dist=30)

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
            for peak in self.getPeaks():
                lineItem = BaseGraphicsLineItem()
                lineItem.setLine(peak, 0, peak, image.height())
                pen = QPen(QBrush(ApplicationStyleLogicModule().getPrimaryColor()), 1)
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

    def getPeaks(self):
        result=[]
        for someClusterIndex,cluster in self.peaksClusters.items():
            result.append(np.array(cluster).mean())
        return result

    def initialize(self):
        super().initialize()

