from sqlalchemy import Column
from sqlalchemy import String

from chromos.spectracs.model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin

class SpectrometerStyle(DbBaseEntity, DbBaseEntityMixin):
    styleId = Column(String)
    styleName = Column(String)
    description = Column(String)

