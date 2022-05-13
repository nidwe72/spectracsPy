from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QWidget


from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from model.application.navigation.NavigationSignal import NavigationSignal
from view.application.widgets.video.VideoViewModule import VideoViewModule


class SpectralJobViewModule(QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout=QGridLayout()
        self.setLayout(layout)

        videoViewModule = VideoViewModule()
        layout.addWidget(videoViewModule, 0, 0, 1, 2)

        importButton=QPushButton()
        importButton.setText("Import Spectrum")
        layout.addWidget(importButton,1,0,1,1)
        importButton.clicked.connect(self.onClickedImportButtonButton)

        backButton=QPushButton()
        backButton.setText("Back")
        layout.addWidget(backButton,1,1,1,1)
        backButton.clicked.connect(self.onClickedBackButton)


    def onClickedImportButtonButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SpectralJobImport")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def onClickedBackButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("Home")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)







