from sqlalchemy import Column, ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import relationship

from chromos.spectracs.model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin


class MeasurementProfile(DbBaseEntity, DbBaseEntityMixin):

    spectrometerProfileId = Column(String, ForeignKey("spectrometer_profile.id"))
    spectrometerProfile = relationship("SpectrometerProfile")


