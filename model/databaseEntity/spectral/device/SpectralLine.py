from PySide6.QtGui import QColor
from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer
from sqlalchemy.orm import relationship

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin


class SpectralLine(DbBaseEntity, DbBaseEntityMixin):

    pixelIndex=Column(Integer)

    spectrometerCalibrationProfile_id = Column(Integer, ForeignKey("spectrometer_calibration_profile.id"))
    spectrometerCalibrationProfile = relationship("SpectrometerCalibrationProfile", back_populates="spectralLines")

    spectralLineMasterDataId = Column(Integer, ForeignKey("spectral_line_master_data.id"))
    spectralLineMasterData = relationship("SpectralLineMasterData")

    #transient stuff follows
    color:QColor=None

    __prominence:float=None

    __intensity:float=None

    @property
    def prominence(self):
        return self.__prominence

    @prominence.setter
    def prominence(self, prominence):
        self.__prominence=prominence

    @property
    def intensity(self):
        return self.__intensity

    @intensity.setter
    def intensity(self, intensity):
        self.__intensity=intensity




