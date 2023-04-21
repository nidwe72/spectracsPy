from PySide6.QtWidgets import QGridLayout, QFrame

from sciens.spectracs.view.main.MainStatusBarViewModule import MainStatusBarViewModule

from sciens.spectracs.view.main.MainViewModule import MainViewModule


class MainContainerViewModule(QFrame):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout=QGridLayout()
        self.setLayout(layout)

        self.mainStatusBarViewModule=MainStatusBarViewModule()
        layout.addWidget(self.mainStatusBarViewModule, 0, 0, 1, 1)

        self.mainViewModule = MainViewModule()
        layout.addWidget(self.mainViewModule,1,0,1,1)
        layout.setRowStretch(0,100)






