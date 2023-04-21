from PySide6 import QtCore
from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, QSize, QItemSelectionModel, QItemSelection
from PySide6.QtGui import QTextDocument, QAbstractTextDocumentLayout
from PySide6.QtWidgets import QGroupBox, QGridLayout, QPushButton, QListView, QStyledItemDelegate, \
    QStyleOptionViewItem, QApplication, QWidget, QAbstractItemView, QTextEdit

from PySide6.QtWidgets import QStyle


from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.model.util.SpectrometerProfileUtil import SpectrometerProfileUtil
from sciens.spectracs.logic.model.util.SpectrometerUtil import SpectrometerUtil
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.model.databaseEntity.DbEntityCrudOperation import DbEntityCrudOperation
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerProfile import SpectrometerProfile
from sciens.spectracs.model.signal.SpectrometerProfileSignal import SpectrometerProfileSignal
from spectracs.view.application.widgets.page.PageWidget import PageWidget
from spectracs.view.settings.spectral.spectrometer.acquisition.device.SpectrometerProfileViewModule import \
    SpectrometerProfileViewModule


class SpectrometerProfileListViewModule(PageWidget):

    listView:QListView=None
    spectrometerProfilesListModel=None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        ApplicationContextLogicModule().getApplicationSignalsProvider().spectrometerProfileSignal.connect(
            self.handleSpectrometerProfileSignal)

    def handleSpectrometerProfileSignal(self,spectrometerProfileSignal:SpectrometerProfileSignal):
        operation = spectrometerProfileSignal.operation
        if operation== DbEntityCrudOperation.UPDATE:
            self.spectrometerProfilesListModel.layoutChanged.emit()
        elif operation== DbEntityCrudOperation.CREATE:
            self.spectrometerProfilesListModel.addSpectrometerProfile(spectrometerProfileSignal.entity)
            self.spectrometerProfilesListModel.layoutChanged.emit()

    def createMainContainer(self):
        result=super().createMainContainer()
        result.setTitle("Settings > Spectrometer profiles")
        return result

    def createNavigationGroupBox(self):
        result = QGroupBox("")

        layout = QGridLayout()
        result.setLayout(layout)

        backButton = QPushButton()
        backButton.setText("Back")
        layout.addWidget(backButton, 0, 0, 1, 1)
        backButton.clicked.connect(self.onClickedBackButton)

        editSpectrometerProfileButton = QPushButton()
        editSpectrometerProfileButton.setText("Edit")
        layout.addWidget(editSpectrometerProfileButton, 0, 1, 1, 1)
        editSpectrometerProfileButton.clicked.connect(self.onClickedEditSpectrometerProfileButton)

        addSpectrometerProfileButton = QPushButton()
        addSpectrometerProfileButton.setText("Add")
        layout.addWidget(addSpectrometerProfileButton, 0, 2, 1, 1)
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
        targetViewModule = ApplicationContextLogicModule().getNavigationHandler().getViewModule(someNavigationSignal)

        spectrometerProfile=SpectrometerProfile()
        SpectrometerProfileUtil().initializeSpectrometerProfile(spectrometerProfile)
        targetViewModule.loadView(spectrometerProfile)

    def onClickedEditSpectrometerProfileButton(self):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        someNavigationSignal = NavigationSignal(None)
        someNavigationSignal.setTarget("SpectrometerProfileViewModule")

        spectrometerProfile:SpectrometerProfile=None
        targetViewModule=ApplicationContextLogicModule().getNavigationHandler().getViewModule(someNavigationSignal)
        if isinstance(targetViewModule,SpectrometerProfileViewModule):
            currentIndex=self.listView.currentIndex()
            if isinstance(currentIndex,QModelIndex):
                spectrometerProfile=currentIndex.data()
                if isinstance(spectrometerProfile,SpectrometerProfile):
                    SpectrometerProfileUtil().initializeSpectrometerProfile(spectrometerProfile)
                    targetViewModule.loadView(spectrometerProfile)

        if isinstance(spectrometerProfile,SpectrometerProfile):
            ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(someNavigationSignal)

    def getMainContainerWidgets(self):
        result= super().getMainContainerWidgets()
        if self.listView is None:
            self.listView=QListView()

        #self.listView.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)
        self.listView.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.spectrometerProfilesListModel=SpectrometerProfilesListModel()

        spectrometers = SpectrometerUtil().getSpectrometers()

        spectrometerProfiles = SpectrometerProfileUtil().getSpectrometerProfiles()

        for spectrometerProfileId,spectrometerProfile in spectrometerProfiles.items():
            self.spectrometerProfilesListModel.addSpectrometerProfile(spectrometerProfile)


        self.listView.setModel(self.spectrometerProfilesListModel)

        self.delegate=HTMLDelegate()

        self.listView.setItemDelegate(self.delegate)

        result['lisView']=self.listView
        return result

class SelectionModel(QItemSelectionModel):

    def select(self, index: QModelIndex, command: 'QItemSelectionModel.SelectionFlag') -> None:
        commandToUse=QItemSelectionModel.SelectionFlag.ClearAndSelect

        if isinstance(index,QItemSelection):
            indices=index.indexes()
            super().select(index, command)

class HTMLDelegate(QStyledItemDelegate):
    """QStyledItemDelegate implementation. Draws HTML
    http://stackoverflow.com/questions/1956542/how-to-make-item-view-render-rich-html-text-in-qt/1956781#1956781
    """

    def editorEvent(self, event: QtCore.QEvent, model: QtCore.QAbstractItemModel, option: 'QStyleOptionViewItem',
                    index: QtCore.QModelIndex) -> bool:
        return super().editorEvent(event, model, option, index)

    def eventFilter(self, object: QtCore.QObject, event: QtCore.QEvent) -> bool:
        return super().eventFilter(object, event)

    def __init__(self, parent=None):
        if isinstance(parent, QWidget):
            self._font = parent.font()
        else:
            self._font = None

        QStyledItemDelegate.__init__(self, parent)

    def paint(self, painter, option, index):

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

        html=self.getMarkup(index)

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

    def getMarkup(self,index:QModelIndex):
        spectrometerProfile:SpectrometerProfile = index.data()

        serial = spectrometerProfile.serial

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
                <td colspan="5" style="font-weight:bold;text-align: center;background-color:#404040;">
                    %vendorName%
                    %modelName%                    
                    %codeName%
                    %styleName%                                         
                    (%serial%)
                </td>
            </tr>
            <tr>
                <td width=20%>Vendor</td>
                <td width=20%>Model</td>
                <td width=20%>Sensor</td>
                <td width=20%>Style</td>                                
                <td width=20%>Serial</td>
            </tr>                        
            <tr>
                <td width=20%>%vendorName%</td>
                <td width=20%>%modelName%</td>                
                <td width=20%>%codeName%</td>
                <td width=20%>%styleName%</td>                
                <td width=20%>%serial%</td>
            </tr>
            </table>
            </body>
            '''


        html = html.replace('%serial%', serial)
        html = html.replace('%vendorName%', spectrometerProfile.spectrometer.spectrometerVendor.vendorName)
        html = html.replace('%modelName%', spectrometerProfile.spectrometer.modelName)
        html = html.replace('%codeName%', spectrometerProfile.spectrometer.spectrometerSensor.codeName)
        html = html.replace('%styleName%', spectrometerProfile.spectrometer.spectrometerStyle.styleName)


        return html

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

        html =self.getMarkup(index)
        doc.setHtml(html)



        #result=QSize(doc.idealWidth(), doc.size().height())
        result = QSize(doc.idealWidth(), doc.size().height())
        return result

    def createEditor(self, parent: QWidget, option: 'QStyleOptionViewItem', index: QtCore.QModelIndex) -> QWidget:
        #result=super().createEditor(parent, option, index)

        result=QWidget(parent)

        layout=QGridLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.setHorizontalSpacing(0)
        layout.setVerticalSpacing(0)
        result.setLayout(layout)

        textEdit=QTextEdit()
        textEdit.setContentsMargins(0,0,0,0)

        html = \
            '''
            <style type="text/css">

                body{
                    background-color:gray;
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


        textDocument=QTextDocument()
        textDocument.setHtml(html)
        textDocument.setDocumentMargin(0)
        textEdit.setDocument(textDocument)

        layout.addWidget(textEdit, 0, 0, 1, 1)

        button=QPushButton(parent)
        button.setText("Edit")
        layout.addWidget(button,0,1,1,1)

        return result


class SpectrometerProfilesListModel(QAbstractListModel):
    #__spectrometerProfiles:List[SpectrometerProfile]=[]
    __spectrometerProfiles = []

    def __init__(self, parent=None):
        self.__spectrometerProfiles=[]
        QAbstractListModel.__init__(self, parent)

    def addSpectrometerProfile(self,spectrometerProfile:SpectrometerProfile):
        self.__spectrometerProfiles.append(spectrometerProfile)
        return

    def rowCount(self, parent=QModelIndex()):
        return len(self.__spectrometerProfiles)

    def data(self, index, role):
        if not index.isValid():
            return None
            #return QVariant()

        if index.row() >= len(self.__spectrometerProfiles):
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            result=self.__spectrometerProfiles[index.row()]
            return result
        elif role ==Qt.ItemDataRole.EditRole:
            return self.__spectrometerProfiles[index.row()]
        else:
            #return QVariant()
            return None

    def flags(self, index):
        flags = super(self.__class__, self).flags(index)
        flags |= Qt.ItemFlag.ItemIsEditable
        #flags |= Qt.ItemFlag.ItemIsSelectable
        flags |= Qt.ItemFlag.ItemIsEnabled
        #flags |= Qt.ItemFlag.ItemIsDragEnabled
        #flags |= Qt.ItemFlag.ItemIsDropEnabled

        # Always editable with ReadOnlyDelegate:
        flags =  Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable|Qt.ItemFlag.ItemIsSelectable
        return flags





