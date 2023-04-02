from sqlalchemy import Column, Float
from sqlalchemy import String

from sciens.spectracs.model.databaseEntity.DbBase import DbBaseEntity, DbBaseEntityMixin


class SpectralLineMasterData(DbBaseEntity, DbBaseEntityMixin):
    name = Column(String)
    colorName = Column(String)
    mainColorName = Column(String)
    nanometer = Column(Float)


    intensity:int=0
    description:str=''
    light='CFL'




