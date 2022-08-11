from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin


class SpectrometerProfile(DbBaseEntity, DbBaseEntityMixin):

    serial = Column(String)

    spectrometerId = Column(Integer, ForeignKey("spectrometer.id"))
    #spectrometerSensor = relationship("SpectrometerSensor", back_populates="spectrometers")
    spectrometer = relationship("Spectrometer")

    

















