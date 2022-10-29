import os
import pkgutil

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QProgressBar

from PySide6 import QtCore

from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from model.application.applicationStatus.ApplicationStatusSignal import ApplicationStatusSignal
from resource.ResourceUtil import ResourceUtil


class MainStatusBarViewModule(QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFixedHeight(100)

        layout=QGridLayout()
        layout.setContentsMargins(0,0,0,0)
        self.setLayout(layout)

        self.label=QLabel()

        pixmap = QPixmap()
        pixmap.loadFromData(ResourceUtil().getResourceData('logo.png'), 'png')
        self.label.setPixmap(pixmap)
        self.label.setScaledContents(True)
        self.label.setMinimumWidth(int(480 * 1.5))

        layout.addWidget(self.label,0,0, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        self.progressBar=QProgressBar(self)
        self.progressBar.setMinimumWidth(int(480 * 1.5))
        self.resetProgressBar()

        layout.addWidget(self.progressBar, 1, 0, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        ApplicationContextLogicModule().getApplicationSignalsProvider().applicationStatusSignal.connect(
            self.handleApplicationStatusSignal)

    def resetProgressBar(self):
        self.progressBar.setValue(0)
        self.progressBar.setFormat('ready for action...')

    def handleApplicationStatusSignal(self,applicationStatusSignal:ApplicationStatusSignal):

        if applicationStatusSignal.isStatusReset:
            self.resetProgressBar()
        else:
            self.progressBar.setFormat(applicationStatusSignal.text)
            percents = applicationStatusSignal.currentStepIndex / float(applicationStatusSignal.stepsCount) * 100.0
            self.progressBar.setValue(percents)






