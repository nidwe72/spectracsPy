import sys

from PySide6 import QtWidgets
from PySide6.QtGui import QGuiApplication

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.appliction.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from sciens.spectracs.view.main.MainContainerViewModule import MainContainerViewModule



app = QtWidgets.QApplication(sys.argv)

app.setStyleSheet(ApplicationStyleLogicModule().getApplicationStyleSheet())



mainContainerViewModule = MainContainerViewModule()
geometry = QGuiApplication.primaryScreen().availableGeometry()
mainContainerViewModule.setMinimumWidth(geometry.width()/2)
mainContainerViewModule.setMinimumHeight(geometry.height()*0.9)
mainContainerViewModule.setWindowTitle("Spectracs")

ApplicationContextLogicModule().getNavigationHandler().mainContainerViewModule = mainContainerViewModule
mainContainerViewModule.show()

try:
    import pyi_splash

    pyi_splash.update_text('UI Loaded ...')
    pyi_splash.close()
except:
    pass

sys.exit(app.exec())




