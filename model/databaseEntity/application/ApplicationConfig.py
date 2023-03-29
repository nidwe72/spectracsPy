import uuid
from typing import List

from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship, Mapped, mapped_column

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin
from model.databaseEntity.application.ApplicationConfigToSpectrometerProfile import \
    ApplicationConfigToSpectrometerProfile


class ApplicationConfig(DbBaseEntity, DbBaseEntityMixin):

    spectrometerProfilesMapping: Mapped[List[ApplicationConfigToSpectrometerProfile]] = relationship()

    def getSpectrometerProfilesMapping(self)->Mapped[List[ApplicationConfigToSpectrometerProfile]]:
        return self.spectrometerProfilesMapping

    def setSpectrometerProfilesMapping(self,spectrometerProfilesMapping):
        self.spectrometerProfilesMapping=spectrometerProfilesMapping






