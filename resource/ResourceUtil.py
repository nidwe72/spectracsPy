import pkgutil

from base.Singleton import Singleton


class ResourceUtil(Singleton):

    def getResourceData(self,filename:str):
        result=pkgutil.get_data(__name__,filename)
        return result
