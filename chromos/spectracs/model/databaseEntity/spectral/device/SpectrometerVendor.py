from sqlalchemy import Column
from sqlalchemy import String

from chromos.spectracs.model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin

class SpectrometerVendor(DbBaseEntity, DbBaseEntityMixin):

    vendorName = Column(String)
    vendorId = Column(String)



