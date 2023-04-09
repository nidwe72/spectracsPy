from PySide6.QtCore import QObject, QEvent
from PySide6.QtWidgets import QWidget

from base import SingletonQObject


class Polisher(QObject,metaclass=SingletonQObject):

    def eventFilter(self, objectInstance: QObject, event: QEvent) -> bool:

        if event.type()==QEvent.Type.DynamicPropertyChange:
            if isinstance(objectInstance, QWidget):
                objectInstance.style().unpolish(objectInstance)
                objectInstance.style().polish(objectInstance)

        return super().eventFilter(objectInstance, event)
