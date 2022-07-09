from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin

class Spectrometer(DbBaseEntity, DbBaseEntityMixin):
    produceId = Column(String)
    vendorId = Column(String)
    vendorName = Column(String) #Spectracs
    modelName=Column(String) #InVision
    codeName = Column(String)  #GreenGold
    spectrometerSensorCodeName=Column(String) #Exakta

    spectrometerProfileId = Column(Integer, ForeignKey("spectrometer_profile.id"))
    spectrometerSensorId = Column(Integer, ForeignKey("spectrometer_sensor.id"))

    spectrometerProfile = relationship("SpectrometerProfile", back_populates="spectrometer")
    spectrometerSensor = relationship("SpectrometerSensor", back_populates="spectrometers")


