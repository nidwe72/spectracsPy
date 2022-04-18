from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QWidget


class SpectralJobViewModule(QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout=QGridLayout()
        self.setLayout(layout)

        importButton=QPushButton()
        importButton.setText("import")
        layout.addWidget(importButton,0,0,1,1)





