from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin
from model.databaseEntity.spectral.device import SpectrometerProfile


class Spectrometer(DbBaseEntity, DbBaseEntityMixin):

    modelName=Column(String) #InVision
    #pectrometerProfileId = Column(Integer, ForeignKey("spectrometer_profile.id"))
    #spectrometerProfile = relationship("SpectrometerProfile", back_populates="spectrometer")
    #spectrometerProfile = relationship("SpectrometerProfile")

    spectrometerSensorId = Column(Integer, ForeignKey("spectrometer_sensor.id"))
    #spectrometerSensor = relationship("SpectrometerSensor", back_populates="spectrometers")
    spectrometerSensor = relationship("SpectrometerSensor")

    spectrometerVendorId = Column(Integer, ForeignKey("spectrometer_vendor.id"))
    #spectrometerVendor = relationship("SpectrometerVendor", back_populates="spectrometers")
    spectrometerVendor = relationship("SpectrometerVendor")

    spectrometerStyleId = Column(Integer, ForeignKey("spectrometer_style.id"))
    #spectrometerStyle = relationship("SpectrometerStyle", back_populates="spectrometers")
    spectrometerStyle = relationship("SpectrometerStyle")



