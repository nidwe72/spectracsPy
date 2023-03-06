from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin


class ApplicationConfig(DbBaseEntity, DbBaseEntityMixin):


    spectrometerProfileId = Column(Integer, ForeignKey("spectrometer_profile.id"))
    spectrometerProfile = relationship("SpectrometerProfile")
