from PyQt6.QtWidgets import QWidget, QGridLayout, QLabel, QLineEdit

from logic.spectral.util.SpectrallineUtil import SpectralLineUtil
from model.databaseEntity.spectral.device import SpectrometerCalibrationProfile
from model.databaseEntity.spectral.device.SpectralLine import SpectralLine
from view.application.widgets.page.PageWidget import PageWidget
from typing import List, Dict


class SpectrometerCalibrationProfileSpectralLinesViewModule(PageWidget):

    __model:SpectrometerCalibrationProfile=None
    labelsByNanometers:Dict[float,QLabel]=None

    def _getPageTitle(self):
        return "Spectral lines"

    def getMainContainerWidgets(self):


        result={}
        self.labelsByNanometers={}

        spectralLines=self.__getModel().spectralLines

        mainWidget=QWidget()
        mainWidgetLayout=QGridLayout()
        mainWidget.setLayout(mainWidgetLayout)

        loopIndex=1
        columnIndex=0
        rowIndex = 0
        for spectralLine in spectralLines:
            if loopIndex==6:
                rowIndex = 1
                columnIndex=0

            someLabel=QLabel()
            someLabel.setAutoFillBackground(True)
            self.labelsByNanometers[spectralLine.nanometer]=someLabel

            spectralLineWidget=QWidget()
            spectralLineWidgetLayout=QGridLayout()
            spectralLineWidget.setLayout(spectralLineWidgetLayout)

            someLabel.setText(str(spectralLine.nanometer))
            someLabel.setStyleSheet("QLabel { background-color :" + spectralLine.color.name() + " ; color : black; }");
            spectralLineWidgetLayout.addWidget(someLabel,0,0,1,1)

            lineEditPixelIndex=QLineEdit()
            spectralLineWidgetLayout.addWidget(lineEditPixelIndex, 0, 1, 1, 1)

            mainWidgetLayout.addWidget(spectralLineWidget,rowIndex,columnIndex,1,1)

            # print('-----')
            # print(rowIndex)
            # print(columnIndex)

            columnIndex += 1
            loopIndex += 1

        result['mainWidget']=mainWidget
        return result


    def setModel(self,model:SpectrometerCalibrationProfile):
        self.__model=model

    def __getModel(self)->SpectrometerCalibrationProfile:
        return self.__model


