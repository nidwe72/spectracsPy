from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin

class SpectrometerVendor(DbBaseEntity, DbBaseEntityMixin):

    vendorName = Column(String)
    vendorId = Column(String)



