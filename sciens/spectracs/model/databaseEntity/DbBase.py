

from appdata import AppDataPaths
from sqlalchemy import \
    create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_mixin
from sqlalchemy.orm import declared_attr
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.schema import Column
from sqlalchemy.sql.sqltypes import String


from sciens.base.Singleton import Singleton

import uuid

app_paths = AppDataPaths()
app_paths.setup()

dbFilepath='sqlite:///'+app_paths.app_data_path+'/spectracsPy.db'
engine = create_engine(dbFilepath)

_SessionFactory = sessionmaker(bind=engine,expire_on_commit=False)

DbBaseEntity = declarative_base()

def session_factory()->Session:
    DbBaseEntity.metadata.create_all(engine)
    return SessionProvider().getSession()


def to_underscore(name):
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def get_guid():
    result=uuid.uuid4()
    print('#####get_guid#####')
    print (result)
    return result

@declarative_mixin
class DbBaseEntityMixin:

    @declared_attr
    def __tablename__(cls):
        result=to_underscore(cls.__name__)
        # print (result)
        return result


    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))


class SessionProvider(Singleton):
    session=None

    def getSession(self):
        if self.session is None:
            self.session=_SessionFactory()
        return self.session

