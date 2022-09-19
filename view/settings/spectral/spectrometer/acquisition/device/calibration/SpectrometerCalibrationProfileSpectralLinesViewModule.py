from PyQt6.QtWidgets import QWidget, QGridLayout, QLabel

from logic.spectral.util.SpectrallineUtil import SpectralLineUtil
from model.databaseEntity.spectral.device.SpectralLine import SpectralLine
from view.application.widgets.page.PageWidget import PageWidget
from typing import List, Dict


class SpectrometerCalibrationProfileSpectralLinesViewModule(PageWidget):

    spectralLines:List[SpectralLine]=None
    labelsByNanometers:Dict[float,QLabel]=None

    def _getPageTitle(self):
        return "Spectral lines"

    def getMainContainerWidgets(self):


        result={}
        self.labelsByNanometers={}

        self.spectralLines=list(SpectralLineUtil().sortSpectralLinesByNanometers(list(SpectralLineUtil().getSpectralLinesByNames().values())).values())

        mainWidget=QWidget()
        mainWidgetLayout=QGridLayout()
        mainWidget.setLayout(mainWidgetLayout)

        loopIndex=1
        columnIndex=0
        rowIndex = 0
        for spectralLine in self.spectralLines:
            if loopIndex==6:
                rowIndex = 1
                columnIndex=0

            someLabel=QLabel()
            someLabel.setAutoFillBackground(True)
            self.labelsByNanometers[spectralLine.nanometer]=someLabel

            someLabel.setText(str(spectralLine.nanometer))
            someLabel.setStyleSheet("QLabel { background-color :" + spectralLine.color.name() + " ; color : black; }");

            mainWidgetLayout.addWidget(someLabel,rowIndex,columnIndex,1,1)

            # print('-----')
            # print(rowIndex)
            # print(columnIndex)

            columnIndex += 1
            loopIndex += 1

        result['mainWidget']=mainWidget
        return result


    def setModel(self,spectralLines:List[SpectralLine]):
        self.spectralLines=spectralLines



