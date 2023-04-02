from sqlalchemy import Column, ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import relationship

from sciens.spectracs.model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin


class SpectrometerProfile(DbBaseEntity, DbBaseEntityMixin):

    serial = Column(String)

    spectrometerId = Column(String, ForeignKey("spectrometer.id"))
    spectrometer = relationship("Spectrometer")

    spectrometerCalibrationProfileId = Column(String, ForeignKey("spectrometer_calibration_profile.id"))
    spectrometerCalibrationProfile = relationship("SpectrometerCalibrationProfile")

























