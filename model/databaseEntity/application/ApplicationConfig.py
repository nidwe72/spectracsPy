import uuid
from typing import List

from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship, Mapped, mapped_column

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin
from model.databaseEntity.application.ApplicationConfigToSpectrometerProfile import \
    ApplicationConfigToSpectrometerProfile


class ApplicationConfig(DbBaseEntity, DbBaseEntityMixin):

    # spectrometerProfiles = relationship("SpectrometerProfile", back_populates="applicationConfig")

    # def getSpectrometerProfiles(self):
    #     return self.spectrometerProfiles
    #
    # def setSpectrometerProfiles(self,spectrometerProfiles):
    #     self.spectrometerProfiles=spectrometerProfiles

    #id: Mapped[int] = mapped_column(primary_key=True,default=lambda: str(uuid.uuid4()))

    spectrometerProfiles: Mapped[List[ApplicationConfigToSpectrometerProfile]] = relationship()

