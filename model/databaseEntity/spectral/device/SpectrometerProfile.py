from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin


class SpectrometerProfile(DbBaseEntity, DbBaseEntityMixin):

    serial = Column(String)
    spectrometer = relationship("Spectrometer", back_populates="spectrometerProfile", uselist=False)















