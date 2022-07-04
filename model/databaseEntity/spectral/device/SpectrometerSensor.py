from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin


class SpectrometerSensor(DbBaseEntity, DbBaseEntityMixin):
    vendorId = Column(String)
    modelId = Column(String)
    name=Column(String)
    description = Column(String)

    horizontalDigitalResolution = Column(Integer)
    verticalDigitalResolution = Column(Integer)

    spectrometerProfiles = relationship("SpectrometerProfile")

    


