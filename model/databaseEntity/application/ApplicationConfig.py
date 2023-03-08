from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin


class ApplicationConfig(DbBaseEntity, DbBaseEntityMixin):

    spectrometerProfiles = relationship("SpectrometerProfile", back_populates="applicationConfig")


    def getSpectrometerProfiles(self):
        return self.spectrometerProfiles

    def setSpectrometerProfiles(self,spectrometerProfiles):
        self.spectrometerProfiles=spectrometerProfiles

