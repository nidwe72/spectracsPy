from PyQt6.QtGui import QColor
from sqlalchemy import Column, Float, ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import relationship

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin


class SpectralLine(DbBaseEntity, DbBaseEntityMixin):

    pixelIndex=Column(Integer)

    color:QColor=None

    spectrometerCalibrationProfile_id = Column(Integer, ForeignKey("spectrometer_calibration_profile.id"))
    spectrometerCalibrationProfile = relationship("SpectrometerCalibrationProfile", back_populates="spectralLines")

    spectralLineMasterDataId = Column(Integer, ForeignKey("spectral_line_master_data.id"))
    spectralLineMasterData = relationship("SpectralLineMasterData")




