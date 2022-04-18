from PyQt6.QtCore import QObject


class NavigationHandlerLogicModule(QObject):

    def __init__(self,parent):
        super().__init__()
        self.parent = parent
        print(NavigationHandlerLogicModule)

    def handleNavigationSignal(self,navigationSignal):
        print("handleNavigationSignal")
        target=navigationSignal.getTarget()
        print("target")
        print(target)



