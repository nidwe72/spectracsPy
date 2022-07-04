from typing import List
from PyQt6.QtCore import QAbstractListModel, QModelIndex, QVariant, Qt, QSize
from PyQt6.QtGui import QTextDocument, QAbstractTextDocumentLayout, QPalette
from PyQt6.QtWidgets import QGroupBox, QGridLayout, QPushButton, QListView, QItemDelegate, QStyledItemDelegate, \
    QStyleOptionViewItem, QApplication, QWidget

from PyQt6.QtWidgets import QStyle


from controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from model.application.navigation.NavigationSignal import NavigationSignal
from model.databaseEntity.spectral.device.SpectrometerProfile import SpectrometerProfile
from view.application.widgets.page.PageWidget import PageWidget


class SpectrometerProfileListViewModule(PageWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    listView:QListView=None

    def createNavigationGroupBox(self):
        result = QGroupBox("")

        layout = QGridLayout()
        result.setLayout(layout)

        backButton = QPushButton()
        backButton.setText("Back")
        layout.addWidget(backButton, 0, 0, 1, 1)
        backButton.clicked.connect(self.onClickedBackButton)

        addSpectrometerProfileButton = QPushButton()
        addSpectrometerProfileButton.setText("Add spectrometer")
        layout.addWidget(addSpectrometerProfileButton, 0, 1, 1, 1)
        addSpectrometerProfileButton.clicked.connect(self.onClickedAddSpectrometerProfileButton)

        return result

    def onClickedBackButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SettingsViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def onClickedAddSpectrometerProfileButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SpectrometerProfileViewModule")
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def getMainContainerWidgets(self):
        result= super().getMainContainerWidgets()
        if self.listView==None:
            self.listView=QListView()

        self.spectrometerProfilesListModel=SpectrometerProfilesListModel()

        spectrometerProfile=SpectrometerProfile()
        spectrometerProfile.serial='1234'
        self.spectrometerProfilesListModel.addSpectrometerProfile(spectrometerProfile)

        spectrometerProfile2=SpectrometerProfile()
        spectrometerProfile2.serial='1234'
        self.spectrometerProfilesListModel.addSpectrometerProfile(spectrometerProfile2)


        self.listView.setModel(self.spectrometerProfilesListModel)

        self.delegate=HTMLDelegate()

        self.listView.setItemDelegate(self.delegate)

        result['lisView']=self.listView
        return result

class HTMLDelegate(QStyledItemDelegate):
    """QStyledItemDelegate implementation. Draws HTML
    http://stackoverflow.com/questions/1956542/how-to-make-item-view-render-rich-html-text-in-qt/1956781#1956781
    """

    def __init__(self, parent=None):
        if isinstance(parent, QWidget):
            self._font = parent.font()
        else:
            self._font = None

        QStyledItemDelegate.__init__(self, parent)

    def paint(self, painter, option, index):
        """QStyledItemDelegate.paint implementation
        """



        option.state &= ~QStyle.StateFlag.State_HasFocus  # never draw focus rect

        option.state |= QStyle.StateFlag.State_Active  # draw fuzzy-open completion as focused, even if focus is on the line edit

        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        style = QApplication.style() if options.widget is None else options.widget.style()

        doc = QTextDocument()

        doc.setTextWidth(option.rect.width());

        if self._font is not None:
            doc.setDefaultFont(self._font)

        doc.setDocumentMargin(1)
        #doc.setHtml(options.text)

        html = \
            '''            
            <style type="text/css">                
                body {
	                color: black;
	                background: blue;
                }                
                table {
                    color: white;
                    border-width: 0px;
                    border-collapse: collapse;                    
                }               
            </style>            
            <body width=100% border=1>
            <table width=100% border=1>
            <tr>
                <td width=33%>Spectral profile</td>
                <td width=34%>axggshjs:jhsah</td>
                <td width=33% >hkashh</td>
            </tr>
            </table>
            </body>
            '''


        doc.setHtml(html)
        #doc.setHtml("<Hello><br/><center>world</center><br/>foo")


        #  bad long (multiline) strings processing doc.setTextWidth(options.rect.width())

        options.text = ""

        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, options, painter)

        ctx = QAbstractTextDocumentLayout.PaintContext()

        # Highlighting text if item is selected

        #if option.state & QStyle.StateFlag.State_Selected:
        #    ctx.palette.setColor(QPalette.Text,
        #      option.palette.color(QPalette.Active, QPalette.Text))

        textRect = style.subElementRect(QStyle.SubElement.SE_ItemViewItemText, options)
        painter.save()
        painter.translate(textRect.topLeft())
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        doc.documentLayout().draw(painter, ctx)

        painter.restore()

    def sizeHint(self, option, index):
        """QStyledItemDelegate.sizeHint implementation
        """
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        doc = QTextDocument()
        if self._font is not None:
            doc.setDefaultFont(self._font)
        doc.setDocumentMargin(1)
        #  bad long (multiline) strings processing doc.setTextWidth(options.rect.width())

        html = \
            '''            
            <style type="text/css">                
                body {
                    color: black;
                    background: blue;
                }                
                table {
                    color: white;
                    border-width: 0px;
                    border-collapse: collapse;                    
                }               
            </style>            
            <body width=100% border=1>
            <table width=100% border=1>
            <tr>
                <td width=33%>Spectral profile</td>
                <td width=34%>axggshjs:jhsah</td>
                <td width=33% >hkashh</td>
            </tr>
            </table>
            </body>
            '''

        #doc.setHtml(options.text)
        doc.setHtml(html)



        #result=QSize(doc.idealWidth(), doc.size().height())
        result = QSize(doc.idealWidth(), doc.size().height())
        return result

class SpectrometerProfilesListModel(QAbstractListModel):
    __spectrometerProfiles:List[SpectrometerProfile]=[]

    def __init__(self, parent=None):
        self.__spectrometerProfiles=[]
        QAbstractListModel.__init__(self, parent)

    def addSpectrometerProfile(self,spectrometerProfile:SpectrometerProfile):
        self.__spectrometerProfiles.append(SpectrometerProfile)

    def rowCount(self, parent=QModelIndex()):
        return len(self.__spectrometerProfiles)

    def data(self, index, role):
        if not index.isValid():
            return QVariant()

        if index.row() >= len(self.__spectrometerProfiles):
            return QVariant()

        if role == Qt.ItemDataRole.DisplayRole:
            return self.__spectrometerProfiles[index.row()]
        else:
            return QVariant()





