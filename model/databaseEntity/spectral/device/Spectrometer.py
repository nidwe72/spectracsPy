from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin
from model.databaseEntity.spectral.device import SpectrometerProfile


class Spectrometer(DbBaseEntity, DbBaseEntityMixin):

    modelName=Column(String) #InVision

    spectrometerSensorId = Column(String, ForeignKey("spectrometer_sensor.id"))
    spectrometerSensor = relationship("SpectrometerSensor")

    spectrometerVendorId = Column(String, ForeignKey("spectrometer_vendor.id"))
    spectrometerVendor = relationship("SpectrometerVendor")

    spectrometerStyleId = Column(String, ForeignKey("spectrometer_style.id"))
    spectrometerStyle = relationship("SpectrometerStyle")



