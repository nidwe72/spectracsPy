from typing import Dict
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsItem

from view.application.widgets.graphicsScene.BaseGraphicsItem import BaseGraphicsItem


class BaseGraphicsScene(QGraphicsScene):

    __graphicItems:Dict[BaseGraphicsItem,BaseGraphicsItem]={}

    def addItem(self, item: QGraphicsItem) -> None:
        super().addItem(item)
        self.__graphicItems[item]=item

    def removeItem(self, item: QGraphicsItem) -> None:
        super().removeItem(item)

    def getItem(self,item: QGraphicsItem)->QGraphicsItem:
        result=self.__graphicItems[item]
        return result


