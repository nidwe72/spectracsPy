from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import Integer

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin


class SpectrometerCalibrationProfile(DbBaseEntity, DbBaseEntityMixin):

    regionOfInterestX = Column(Integer)
    regionOfInterestY = Column(Integer)
    regionOfInterestWidth = Column(Integer)
    regionOfInterestHeight = Column(Integer)

    interpolationCoefficientA = Column(Float)
    interpolationCoefficientB = Column(Float)
    interpolationCoefficientC = Column(Float)


