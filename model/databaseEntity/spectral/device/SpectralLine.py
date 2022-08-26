from PyQt6.QtGui import QColor
from sqlalchemy import Column, Float
from sqlalchemy import Integer
from sqlalchemy import String

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin


class SpectralLine(DbBaseEntity, DbBaseEntityMixin):
    name = Column(String)
    colorName = Column(String)
    mainColorName = Column(String)
    nanometer = Column(Float)

    color:QColor=None
    pixelIndex:int=None


