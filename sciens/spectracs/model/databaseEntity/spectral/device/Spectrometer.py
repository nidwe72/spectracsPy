from sqlalchemy import Column, ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import relationship

from sciens.spectracs.model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin


class Spectrometer(DbBaseEntity, DbBaseEntityMixin):

    modelName=Column(String) #InVision

    spectrometerSensorId = Column(String, ForeignKey("spectrometer_sensor.id"))
    spectrometerSensor = relationship("SpectrometerSensor")

    spectrometerVendorId = Column(String, ForeignKey("spectrometer_vendor.id"))
    spectrometerVendor = relationship("SpectrometerVendor")

    spectrometerStyleId = Column(String, ForeignKey("spectrometer_style.id"))
    spectrometerStyle = relationship("SpectrometerStyle")



