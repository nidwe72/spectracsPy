from sqlalchemy import Column, ForeignKey, Boolean
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin


class SpectrometerSensor(DbBaseEntity, DbBaseEntityMixin):

    vendorId = Column(String)
    vendorName = Column(String)
    sellerName = Column(String)
    modelId = Column(String)
    #name=Column(String)
    description = Column(String)
    codeName=Column(String)
    isVirtual=Column(Boolean)

    #spectrometers = relationship("Spectrometer")

    spectrometerSensorChipId = Column(Integer, ForeignKey("spectrometer_sensor_chip.id"))
    #spectrometerSensorChip = relationship("SpectrometerSensorChip", back_populates="spectrometerSensors")

    spectrometerSensorChip = relationship("SpectrometerSensorChip")



