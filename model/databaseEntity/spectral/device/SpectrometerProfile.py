from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship
from sqlalchemy import Boolean

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin


class SpectrometerProfile(DbBaseEntity, DbBaseEntityMixin):

    serial = Column(String)

    isDefault=Column('isDefault',Boolean,default=False)

    spectrometerId = Column(Integer, ForeignKey("spectrometer.id"))
    spectrometer = relationship("Spectrometer")

    spectrometerCalibrationProfileId = Column(Integer, ForeignKey("spectrometer_calibration_profile.id"))
    spectrometerCalibrationProfile = relationship("SpectrometerCalibrationProfile")

    applicationConfig_id = Column(Integer, ForeignKey("application_config.id"))
    applicationConfig = relationship("ApplicationConfig", back_populates="spectrometerProfiles")























