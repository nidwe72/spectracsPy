
class BaseGraphicsItem:

    itemName:str=None

    def __hash__(self) -> int:
        result= super().__hash__()
        return result






