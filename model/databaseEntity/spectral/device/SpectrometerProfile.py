from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin


class SpectrometerProfile(DbBaseEntity, DbBaseEntityMixin):

    spectrometerSensorId = Column(Integer, ForeignKey("parent.id"))
    serial = Column(String)

    spectrometerSensorId = Column(Integer, ForeignKey("spectrometer_sensor.id"))

spectrometerSensor = relationship("spectrometer_sensor", back_populates="child")











