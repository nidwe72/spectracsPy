from PySide6.QtCore import QObject

class SingletonQObject(QObject):
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = QObject.__new__(cls, *args, **kwargs)
        return cls._instance
