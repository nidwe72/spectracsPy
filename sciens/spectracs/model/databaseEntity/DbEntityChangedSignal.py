from PySide6.QtCore import QObject
from typing import TypeVar, Generic

from sciens.spectracs.model.databaseEntity.DbEntityCrudOperation import DbEntityCrudOperation

E = TypeVar('E')

class DbEntityChangedSignal(QObject,Generic[E]):

    entity:E=None
    operation:DbEntityCrudOperation=None

    def __init__(self,parent=None):
        #super().__init__(parent)
        super().__init__()

    def setEntity(self,entity:E):
        self.entity=entity
        return self

    def setOperation(self,operation:DbEntityCrudOperation):
        self.operation=operation
        return self


