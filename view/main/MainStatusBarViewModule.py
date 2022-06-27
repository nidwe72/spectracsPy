import os

from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QWidget, QLabel, QGridLayout


from PyQt6 import QtCore

class MainStatusBarViewModule(QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFixedHeight(100)

        layout=QGridLayout()
        layout.setContentsMargins(0,0,0,0)
        self.setLayout(layout)

        self.label=QLabel()

        path = os.path.dirname(os.path.abspath(__file__))+'/logo.png'
        print(path)

        pixmap = QPixmap(path)
        self.label.setPixmap(pixmap)


        # self.label.setStyleSheet("background-color: gray")

        # self.label.setText("Spectracs")
        layout.addWidget(self.label,0,0, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)


