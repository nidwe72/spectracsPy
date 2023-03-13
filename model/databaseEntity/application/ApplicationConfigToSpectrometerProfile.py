from sqlalchemy import ForeignKey, Integer, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin

class ApplicationConfigToSpectrometerProfile(DbBaseEntity):

    __tablename__ = "application_config_to_spectrometer_profile"

    id = Column(Integer, primary_key=True, autoincrement=False)

    application_config_id: Mapped[int] = mapped_column(ForeignKey("application_config.id"), primary_key=True)

    spectrometer_profile_id: Mapped[int] = mapped_column(
        ForeignKey("spectrometer_profile.id"), primary_key=True
    )

    spectrometerProfile: Mapped["SpectrometerProfile"] = relationship()


