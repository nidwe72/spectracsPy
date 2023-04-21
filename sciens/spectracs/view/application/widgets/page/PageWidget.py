from PySide6 import QtGui
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget, QGridLayout, QGroupBox, QPushButton, QLabel, QStyleOption, QFrame

from PySide6.QtCore import Qt

from spectracs.view.application.widgets.page.PageLabel import PageLabel

class PageWidget(QFrame):
    mainContainerWidgets = None
    verticalLayout:bool=True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def initialize(self):

        layout=QGridLayout()
        self.setLayout(layout)


        if not self._isTopMostPageWidget():
            layout.setContentsMargins(0,0,0,0)
            self.setContentsMargins(0,0,0,0)

        mainContainer = self.createMainContainer()
        layout.addWidget(mainContainer, 0, 0, 1, 1)
        layout.setRowStretch(0,90)

        if self._isTopMostPageWidget():
            navigationGroupBox = self.createNavigationGroupBox()
            layout.addWidget(navigationGroupBox,1,0,1,1)


    def createNavigationGroupBox(self):
        result = QGroupBox("")

        layout = QGridLayout()
        result.setLayout(layout);

        return result

    def createMainContainer(self):
        result=QGroupBox(self._getPageTitle())

        if self._isTopMostPageWidget():
            result.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            result.setObjectName('PageWidget_topMost')

        #result.setFlat(True)

        layout=QGridLayout()
        layout.setContentsMargins
        result.setLayout(layout)
        row=0
        mainContainerWidgets = self.getMainContainerWidgets()
        for mainContainerWidgetName,mainContainerWidget in mainContainerWidgets.items():
            if self.verticalLayout:
                layout.setContentsMargins(0, 5, 5, 5)
                layout.addWidget(mainContainerWidget,row,0,1,1)
            else:
                layout.addWidget(mainContainerWidget, 0, row, 1, 1)
            row=row+1

        return result

    def _getPageTitle(self):
        return '';

    def getMainContainerWidgets(self):
        if self.mainContainerWidgets is None:
            self.mainContainerWidgets={}
        return self.mainContainerWidgets

    def createLabeledComponent(self,label:str,component:QWidget):
        container=QWidget()

        layout=QGridLayout()
        container.setLayout(layout)
        labelComponent=PageLabel(label)
        layout.addWidget(labelComponent,0,0,1,1)
        layout.setColumnStretch(0,30)

        layout.addWidget(component, 0, 1, 1, 1)
        layout.setColumnStretch(1, 70)

        return container

    def _isTopMostPageWidget(self):
        parent=self.parent()
        result=not isinstance(parent,PageWidget)
        return result

    def setStylesheetOnlySelf(self, stylesheet: str) -> None:
        objectName = self.objectName() if self.objectName() != "" else str(id(self))
        self.setObjectName(objectName)
        self.setStyleSheet("#%s {%s}" % (objectName, stylesheet))



