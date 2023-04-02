from sqlalchemy import select, inspect
from sqlalchemy.orm import class_mapper

from sqlalchemy.sql.selectable import Select

from sciens.spectracs.model.databaseEntity.DbBase import DbBaseEntity, session_factory


class SqlUtil:

    @staticmethod
    def createSelect(baseEntity: DbBaseEntity)->Select:
        selectStatement = select(baseEntity.__class__)
        changedAttributes = SqlUtil.__getChangedAttributes(baseEntity)

        for changedAttribute in changedAttributes:
            someBaseEntityMemberName = changedAttribute.key
            baseEntityAttribute = getattr(baseEntity.__class__, someBaseEntityMemberName)
            selectStatement = selectStatement.where(
                baseEntityAttribute == getattr(baseEntity, someBaseEntityMemberName))
            continue

        type(selectStatement)
        return selectStatement

    @staticmethod
    def executeSelect(baseEntity: DbBaseEntity,selectStatement):
        session = session_factory()
        primaryKeys = [key.name for key in inspect(baseEntity.__class__).primary_key]
        primaryKey=next(iter(primaryKeys), None)
        resultList=session.execute(selectStatement).all()

        resultList=[next(iter(resultListEntry._asdict().values()),None) for resultListEntry in resultList]
        result = {getattr(resultListEntry,primaryKey): resultListEntry for resultListEntry in resultList}
        return result


    @staticmethod
    def __getChangedAttributes(entity):
        result=[]
        inspr = inspect(entity)
        attrs = class_mapper(entity.__class__).column_attrs  # exclude relationships
        for attr in attrs:
            hist = getattr(inspr.attrs, attr.key).history
            if hist.has_changes():
                result.append(attr)
        return result

