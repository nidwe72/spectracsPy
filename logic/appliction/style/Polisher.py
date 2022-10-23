from PyQt6.QtCore import QObject, QEvent
from PyQt6.QtWidgets import QWidget

from base.SingletonQObject import SingletonQObject


class Polisher(SingletonQObject):

    def eventFilter(self, objectInstance: QObject, event: QEvent) -> bool:

        if event.type()==QEvent.Type.DynamicPropertyChange:
            if isinstance(objectInstance, QWidget):
                objectInstance.style().unpolish(objectInstance)
                objectInstance.style().polish(objectInstance)

        return super().eventFilter(objectInstance, event)



#     Q_OBJECT
#     Q_DISABLE_COPY(Polisher)
# public:
#     Polisher(QObject* parent = Q_NULLPTR)
#         : QObject(parent)
#     { }
# protected:
#     bool eventFilter(QObject* obj, QEvent* event) Q_DECL_OVERRIDE
#     {
#         if (event->type() == QEvent::DynamicPropertyChange) {
#             QWidget* objWidget = qobject_cast<QWidget*>(obj);
#             if (objWidget) {
#                 objWidget->style()->unpolish(objWidget);
#                 objWidget->style()->polish(objWidget);
#             }
#         }
#         return QObject::eventFilter(obj, event);
#     }
# };
