from PyQt6.QtGui import QColor
from sqlalchemy import Column, Float, ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin


class SpectralLineMasterData(DbBaseEntity, DbBaseEntityMixin):
    name = Column(String)
    colorName = Column(String)
    mainColorName = Column(String)
    nanometer = Column(Float)
    prominence = Column(Float)
    pixelIndex = Column(Integer)



