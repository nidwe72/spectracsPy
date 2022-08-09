from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin

class Spectrometer(DbBaseEntity, DbBaseEntityMixin):
    productId = Column(String)
    vendorId = Column(String)
    vendorName = Column(String) #Spectracs
    modelName=Column(String) #InVision
    codeName = Column(String)  #GreenGold
    spectrometerSensorCodeName=Column(String) #Exakta

    spectrometerProfileId = Column(Integer, ForeignKey("spectrometer_profile.id"))
    spectrometerProfile = relationship("SpectrometerProfile", back_populates="spectrometer")

    spectrometerSensorId = Column(Integer, ForeignKey("spectrometer_sensor.id"))
    spectrometerSensor = relationship("SpectrometerSensor", back_populates="spectrometers")

    spectrometerVendorId = Column(Integer, ForeignKey("spectrometer_vendor.id"))
    spectrometerVendor = relationship("SpectrometerVendor", back_populates="spectrometers")

    spectrometerStyleId = Column(Integer, ForeignKey("spectrometer_style.id"))
    #spectrometerStyle = relationship("SpectrometerStyle", back_populates="spectrometers")
    spectrometerStyle = relationship("SpectrometerStyle")


