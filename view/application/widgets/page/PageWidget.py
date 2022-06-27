from PyQt6.QtWidgets import QWidget, QGridLayout, QGroupBox, QPushButton, QLabel

from view.application.widgets.page.PageLabel import PageLabel

class PageWidget(QWidget):

    mainContainerWidgets=None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout=QGridLayout()
        self.setLayout(layout)

        mainContainer = self.createMainContainer()
        layout.addWidget(mainContainer, 0, 0, 1, 1)
        layout.setRowStretch(0,90)

        navigationGroupBox = self.createNavigationGroupBox()
        layout.addWidget(navigationGroupBox,1,0,1,1)

    def createNavigationGroupBox(self):
        result = QGroupBox("")

        layout = QGridLayout()
        result.setLayout(layout);

        return result

    def createMainContainer(self):
        result=QWidget()
        layout=QGridLayout()
        result.setLayout(layout)
        row=0
        mainContainerWidgets = self.getMainContainerWidgets()
        for mainContainerWidgetName,mainContainerWidget in mainContainerWidgets.items():
            layout.addWidget(mainContainerWidget,row,0,1,1)
            row=row+1

        return result

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



