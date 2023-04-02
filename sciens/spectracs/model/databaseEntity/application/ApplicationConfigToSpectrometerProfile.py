from sqlalchemy import ForeignKey, Column, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sciens.spectracs.model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin

class ApplicationConfigToSpectrometerProfile(DbBaseEntity,DbBaseEntityMixin):

    application_config_id: Mapped[str] = mapped_column(ForeignKey("application_config.id"), primary_key=True)

    spectrometer_profile_id: Mapped[str] = mapped_column(
        ForeignKey("spectrometer_profile.id"), primary_key=True
    )

    isDefault=Column('isDefault',Boolean,default=False)

    spectrometerProfile: Mapped["SpectrometerProfile"] = relationship()


