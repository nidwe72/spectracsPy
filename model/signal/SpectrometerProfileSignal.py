from typing import TypeVar, Generic

from model.databaseEntity.DbEntityChangedSignal import DbEntityChangedSignal
from model.databaseEntity.spectral.device import SpectrometerProfile


class SpectrometerProfileSignal(DbEntityChangedSignal[SpectrometerProfile]):
    pass