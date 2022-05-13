import sys

import cv2
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage

from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from view.main.MainViewModule import MainViewModule

app = QtWidgets.QApplication(sys.argv)

mainViewModule=MainViewModule();
mainViewModule.resize(480*1.5, 640*1.5)
mainViewModule.setWindowTitle("Spectracs")

ApplicationContextLogicModule().getNavigationHandler().mainViewModule=mainViewModule
mainViewModule.show()
sys.exit(app.exec())