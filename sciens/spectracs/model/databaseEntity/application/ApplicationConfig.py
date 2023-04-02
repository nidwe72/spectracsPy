from typing import List

from sqlalchemy.orm import relationship, Mapped

from sciens.spectracs.model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin
from sciens.spectracs.model.databaseEntity.application.ApplicationConfigToSpectrometerProfile import \
    ApplicationConfigToSpectrometerProfile


class ApplicationConfig(DbBaseEntity, DbBaseEntityMixin):

    spectrometerProfilesMapping: Mapped[List[ApplicationConfigToSpectrometerProfile]] = relationship()

    def getSpectrometerProfilesMapping(self)->Mapped[List[ApplicationConfigToSpectrometerProfile]]:
        return self.spectrometerProfilesMapping

    def setSpectrometerProfilesMapping(self,spectrometerProfilesMapping):
        self.spectrometerProfilesMapping=spectrometerProfilesMapping






