from sqlalchemy import ForeignKey, Integer, Column,String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin

class ApplicationConfigToSpectrometerProfile(DbBaseEntity,DbBaseEntityMixin):

    application_config_id: Mapped[str] = mapped_column(ForeignKey("application_config.id"), primary_key=True)

    spectrometer_profile_id: Mapped[str] = mapped_column(
        ForeignKey("spectrometer_profile.id"), primary_key=True
    )

    spectrometerProfile: Mapped["SpectrometerProfile"] = relationship()


