from appdata import AppDataPaths
from sqlalchemy import \
    create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_mixin
from sqlalchemy.orm import declared_attr
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.schema import Column
from sqlalchemy.sql.sqltypes import Integer

from base.Singleton import Singleton

app_paths = AppDataPaths()
app_paths.setup()

dbFilepath='sqlite:///'+app_paths.app_data_path+'/spectracsPy.db'
engine = create_engine(dbFilepath)
#engine = create_engine(dbFilepath,echo=True)

# use session_factory() to get a new Session
_SessionFactory = sessionmaker(bind=engine,expire_on_commit=False)

DbBaseEntity = declarative_base()

def session_factory()->Session:
    DbBaseEntity.metadata.create_all(engine)
    return SessionProvider().getSession()
    #return _SessionFactory()

def to_underscore(name):
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

@declarative_mixin
class DbBaseEntityMixin:

    @declared_attr
    def __tablename__(cls):
        result=to_underscore(cls.__name__)
        # print (result)
        return result

    # __table_args__ = {"mysql_engine": "InnoDB"}
    # __mapper_args__ = {"always_refresh": True}

    id = Column(Integer, primary_key=True,autoincrement=True)


class SessionProvider(Singleton):
    session=None

    def getSession(self):
        if self.session is None:
            self.session=_SessionFactory()
        return self.session

