from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin


class SpectrometerSensor(DbBaseEntity, DbBaseEntityMixin):

    vendorId = Column(String)
    vendorName = Column(String)
    sellerName = Column(String)
    modelId = Column(String)
    name=Column(String)
    description = Column(String)
    codeName=Column(String)

    horizontalDigitalResolution = Column(Integer)
    verticalDigitalResolution = Column(Integer)

    sensorProductName = Column(String)
    sensorVendorName=Column(String)

    spectrometers = relationship("Spectrometer")

    


