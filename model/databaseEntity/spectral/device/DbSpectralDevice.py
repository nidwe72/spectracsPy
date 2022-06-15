from sqlalchemy import Column
from sqlalchemy import Integer

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin


class DbSpectralDevice(DbBaseEntity,DbBaseEntityMixin):

    horizontalDigitalResolution = Column(Integer)
    verticalDigitalResolution = Column(Integer)







