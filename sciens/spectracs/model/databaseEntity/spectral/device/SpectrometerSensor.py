from sqlalchemy import Column, ForeignKey, Boolean
from sqlalchemy import String
from sqlalchemy.orm import relationship

from sciens.spectracs.model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin


class SpectrometerSensor(DbBaseEntity, DbBaseEntityMixin):

    vendorId = Column(String)
    vendorName = Column(String)
    sellerName = Column(String)
    modelId = Column(String)
    description = Column(String)
    codeName=Column(String)
    isVirtual=Column(Boolean)

    spectrometerSensorChipId = Column(String, ForeignKey("spectrometer_sensor_chip.id"))
    spectrometerSensorChip = relationship("SpectrometerSensorChip")



