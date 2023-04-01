from sqlalchemy import Column
from sqlalchemy import String

from chromos.spectracs.model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin

class SpectrometerSensorChip(DbBaseEntity, DbBaseEntityMixin):

    vendorName = Column(String)
    productName = Column(String)


