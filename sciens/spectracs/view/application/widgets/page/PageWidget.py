from PySide6 import QtGui
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget, QGridLayout, QGroupBox, QPushButton, QLabel, QStyleOption, QFrame

from PySide6.QtCore import Qt

from sciens.spectracs.logic.appliction.style.Metrics import Metrics
from sciens.spectracs.view.application.widgets.page.PageLabel import PageLabel

class PageWidget(QFrame):
    mainContainerWidgets = None
    verticalLayout:bool=True
    # Single-content pages (one field) set this so their titled container is
    # demoted to a borderless section label, not a frame (spec C2b / E5).
    borderlessMainContainer:bool=False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def initialize(self):

        layout=QGridLayout()
        layout.setSpacing(Metrics.S)
        self.setLayout(layout)


        if self._isTopMostPageWidget():
            # Page-level container: the one place that gets an outer margin.
            layout.setContentsMargins(Metrics.M, Metrics.M, Metrics.M, Metrics.M)
        else:
            # Nested page widgets stay flush so margins don't compound.
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
        result.setProperty("plain", True)  # borderless holder (spec C2)

        layout = QGridLayout()
        layout.setSpacing(Metrics.S)
        layout.setContentsMargins(0, 0, 0, 0)  # align nav buttons to content edge (spec C7)
        result.setLayout(layout);

        return result

    def createMainContainer(self):
        title=self._getPageTitle()
        result=QGroupBox(title)

        borderless=False
        if self._isTopMostPageWidget():
            result.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            result.setObjectName('PageWidget_topMost')
            borderless=True
        elif self.borderlessMainContainer:
            result.setProperty("sectionLabel", True)
            borderless=True
        elif title == "":
            # Untitled nested container: nothing to label, so no frame - else it
            # double-borders with the surrounding widgets (spec C8).
            result.setProperty("plain", True)
            borderless=True

        #result.setFlat(True)

        layout=QGridLayout()
        if borderless:
            # Borderless container: no frame to protect, so NO horizontal indent
            # - otherwise nested peers stair-step out of alignment. Vertical only.
            layout.setContentsMargins(0, Metrics.S, 0, Metrics.S)
        else:
            # Bordered panel: uniform inner padding (P=M) so content does not
            # hug the frame and matches every other panel (spec C6).
            layout.setContentsMargins(Metrics.M, Metrics.M, Metrics.M, Metrics.M)
        layout.setSpacing(Metrics.S)
        result.setLayout(layout)
        row=0
        mainContainerWidgets = self.getMainContainerWidgets()
        for mainContainerWidgetName,mainContainerWidget in mainContainerWidgets.items():
            if self.verticalLayout:
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
        # No own margins: the field aligns to its container's content edge, so
        # peers at different nesting depths line up (spec C7).
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Metrics.S)
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



