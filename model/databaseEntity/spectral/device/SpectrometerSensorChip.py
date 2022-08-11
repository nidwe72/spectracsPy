from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin

class SpectrometerSensorChip(DbBaseEntity, DbBaseEntityMixin):

    vendorName = Column(String)
    productName = Column(String)

    #spectrometerSensors = relationship("SpectrometerSensor")
