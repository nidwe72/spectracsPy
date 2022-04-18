from PyQt6.QtWidgets import QStackedWidget
from view.home.HomeViewModule import HomeViewModule


class MainViewModule(QStackedWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        module = HomeViewModule()
        self.addWidget(module)
