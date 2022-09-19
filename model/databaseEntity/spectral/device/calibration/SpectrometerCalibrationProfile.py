from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy.orm import relationship

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin


class SpectrometerCalibrationProfile(DbBaseEntity, DbBaseEntityMixin):

    regionOfInterestX1 = Column(Integer)
    regionOfInterestY1 = Column(Integer)

    regionOfInterestX2 = Column(Integer)
    regionOfInterestY2 = Column(Integer)

    interpolationCoefficientA = Column(Float)
    interpolationCoefficientB = Column(Float)
    interpolationCoefficientC = Column(Float)

    spectralLines = relationship("SpectralLine", back_populates="spectrometerCalibrationProfile")


