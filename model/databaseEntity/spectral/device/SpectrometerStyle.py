from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin

class SpectrometerStyle(DbBaseEntity, DbBaseEntityMixin):
    styleId = Column(String)
    styleName = Column(String)
    description = Column(String)

    #spectrometers = relationship("Spectrometer")
