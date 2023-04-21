from typing import Dict
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem

from spectracs.view.application.widgets.graphicsScene.BaseGraphicsItem import BaseGraphicsItem


class BaseGraphicsScene(QGraphicsScene):

    __graphicItems:Dict[BaseGraphicsItem,BaseGraphicsItem]={}

    def addItem(self, item: QGraphicsItem) -> None:
        super().addItem(item)
        self.__graphicItems[item]=item

    def removeItem(self, item: QGraphicsItem) -> None:
        currentItem=self.__graphicItems.get(item)
        if currentItem is not None:
            super().removeItem(item)
            self.__graphicItems.pop(item)

    def getItem(self,item: QGraphicsItem)->QGraphicsItem:
        result=self.__graphicItems[item]
        return result


