from typing import List

from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import Boolean

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin


class SpectrometerProfile(DbBaseEntity, DbBaseEntityMixin):

    serial = Column(String)

    isDefault=Column('isDefault',Boolean,default=False)

    spectrometerId = Column(String, ForeignKey("spectrometer.id"))
    spectrometer = relationship("Spectrometer")

    spectrometerCalibrationProfileId = Column(String, ForeignKey("spectrometer_calibration_profile.id"))
    spectrometerCalibrationProfile = relationship("SpectrometerCalibrationProfile")

























