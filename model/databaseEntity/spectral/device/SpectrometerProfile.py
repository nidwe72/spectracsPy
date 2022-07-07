from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin


class SpectrometerProfile(DbBaseEntity, DbBaseEntityMixin):

    serial = Column(String)

    spectrometerSensorId = Column(Integer, ForeignKey("spectrometer_sensor.id"))
    #parent = relationship("spectrometer_sensor", back_populates="children")
    spectrometerSensor=relationship("SpectrometerSensor", back_populates="spectrometerProfiles")













