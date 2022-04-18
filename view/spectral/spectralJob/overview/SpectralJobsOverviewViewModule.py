from PyQt6.QtWidgets import QWidget
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QLabel

class SpectralJobsOverviewViewModule(QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout=QGridLayout()
        self.setLayout(layout)

        label=QLabel()
        label.setText("<b>[14.03.2022 16:05] first measurement</b><br/>Quality: excellent")
        layout.addWidget(label, 0, 0, 1, 1)




