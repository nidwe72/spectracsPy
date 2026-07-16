from PySide6 import QtCore
from PySide6.QtCore import QAbstractListModel, QModelIndex, QSize, Qt
from PySide6.QtGui import QAbstractTextDocumentLayout, QTextDocument
from PySide6.QtWidgets import QAbstractItemView, QApplication, QGridLayout, QGroupBox, QLabel, QListView, \
    QPushButton, QStyle, QStyledItemDelegate, QStyleOptionViewItem, QWidget

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.application.style.Metrics import Metrics
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.model.databaseEntity.application.user.UserRoleType import UserRoleType
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget


class SpectrometerSetupListViewModule(PageWidget):
    """Master instrument list (SPEC_connection_and_calibration_ux.md §11): one row per authored instrument,
    re-columned Serial / Device / Plugin / User in the legacy rich HTML-row card style. Rows are assembled
    server-side (profiles left-joined with setups for the plugin and with users for the registered user).
    Add / Edit open the unified SpectrometerSetupViewModule."""

    listView: QListView = None
    listModel = None
    bannerLabel: QLabel = None

    def _getPageTitle(self):
        return "Settings > Spectrometer setups"

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        if self.bannerLabel is None:
            self.bannerLabel = QLabel("")
            self.bannerLabel.setVisible(False)
        result['banner'] = self.bannerLabel

        if self.listView is None:
            self.listView = QListView()
        self.listView.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.listView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.listView.setResizeMode(QListView.ResizeMode.Adjust)
        self.listModel = InstrumentListModel()
        self.listView.setModel(self.listModel)
        self.listView.setItemDelegate(InstrumentHtmlDelegate())
        self.listView.doubleClicked.connect(self.onDoubleClickedRow)
        result['list'] = self.listView

        self.refresh()
        return result

    def showEvent(self, event):
        super().showEvent(event)
        if self.listModel is not None:
            self.refresh()

    def refresh(self):
        if not CurrentUserSession().hasRole(UserRoleType.MASTER_USER.value):
            self.__showBanner("Not authorized.")
            self.listModel.setRows([])
            return
        self.bannerLabel.setVisible(False)
        self.listModel.setRows(self.__buildRows())

    def __buildRows(self):
        client = SpectracsPyServerClient()
        profiles = client.listSpectrometerProfiles() or []
        setups = client.listSpectrometerSetups() or []
        plugins = client.listPlugins() or []
        users = client.listUsers() or []

        pluginTitleByRef = {p.get('codeRef'): p.get('title') for p in plugins}
        pluginRefBySerial = {s.get('serial'): s.get('pluginCodeRef') for s in setups}
        userBySerial = {}
        for user in users:
            serial = user.get('registeredSerial')
            if serial:
                userBySerial[serial] = user

        rows = []
        for profile in profiles:
            serial = profile.get('serial')
            pluginCodeRef = pluginRefBySerial.get(serial)
            user = userBySerial.get(serial)
            rows.append({
                'serial': serial,
                'deviceCodeName': profile.get('deviceCodeName'),
                'pluginCodeRef': pluginCodeRef,
                'pluginTitle': pluginTitleByRef.get(pluginCodeRef) if pluginCodeRef else None,
                'userId': user.get('userId') if user else None,
                'username': user.get('username') if user else None,
            })
        return rows

    def __showBanner(self, text):
        self.bannerLabel.setText(text)
        self.bannerLabel.setVisible(True)

    def createNavigationGroupBox(self):
        result = QGroupBox("")
        result.setProperty("plain", True)
        layout = QGridLayout()
        layout.setSpacing(Metrics.S)
        layout.setContentsMargins(0, 0, 0, 0)
        result.setLayout(layout)

        backButton = QPushButton()
        backButton.setText("Back")
        layout.addWidget(backButton, 0, 0, 1, 1)
        backButton.clicked.connect(self.onClickedBackButton)

        addButton = QPushButton()
        addButton.setText("Add")
        layout.addWidget(addButton, 0, 1, 1, 1)
        addButton.clicked.connect(self.onClickedAddButton)

        editButton = QPushButton()
        editButton.setText("Edit")
        layout.addWidget(editButton, 0, 2, 1, 1)
        editButton.clicked.connect(self.onClickedEditButton)

        return result

    def __getSelectedRow(self):
        index = self.listView.currentIndex()
        if index is not None and index.isValid():
            return self.listModel.getRowAt(index.row())
        return None

    def onClickedAddButton(self):
        self.__openEditor(None)

    def onClickedEditButton(self):
        row = self.__getSelectedRow()
        if row is not None:
            self.__openEditor(row)

    def onDoubleClickedRow(self, index):
        self.onClickedEditButton()

    def __openEditor(self, dto):
        from sciens.spectracs.view.settings.spectrometerSetup.SpectrometerSetupViewModule import \
            SpectrometerSetupViewModule
        navigationSignal = NavigationSignal(None)
        navigationSignal.setTarget("SpectrometerSetupViewModule")
        targetViewModule = ApplicationContextLogicModule().getNavigationHandler().getViewModule(navigationSignal)
        if isinstance(targetViewModule, SpectrometerSetupViewModule):
            targetViewModule.loadView(dto)
            self.__emitNavigation(navigationSignal)

    def onClickedBackButton(self):
        navigationSignal = NavigationSignal(None)
        navigationSignal.setTarget("SettingsViewModule")
        self.__emitNavigation(navigationSignal)

    def __emitNavigation(self, navigationSignal: NavigationSignal):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(navigationSignal)


class InstrumentListModel(QAbstractListModel):
    def __init__(self, parent=None):
        QAbstractListModel.__init__(self, parent)
        self.__rows = []

    def setRows(self, rows):
        self.beginResetModel()
        self.__rows = rows or []
        self.endResetModel()

    def getRowAt(self, row: int):
        if 0 <= row < len(self.__rows):
            return self.__rows[row]
        return None

    def rowCount(self, parent=QModelIndex()):
        return len(self.__rows)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self.__rows):
            return None
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return self.__rows[index.row()]
        return None

    def flags(self, index):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable


class InstrumentHtmlDelegate(QStyledItemDelegate):
    """Legacy rich-row card (per-row header + Serial/Device/Plugin/User table), fed dict rows."""

    def paint(self, painter, option, index):
        option.state &= ~QStyle.StateFlag.State_HasFocus
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        style = QApplication.style() if options.widget is None else options.widget.style()

        doc = QTextDocument()
        doc.setTextWidth(option.rect.width())
        doc.setDocumentMargin(1)
        doc.setHtml(self.__markup(index))

        options.text = ""
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, options, painter)

        textRect = style.subElementRect(QStyle.SubElement.SE_ItemViewItemText, options)
        painter.save()
        painter.translate(textRect.topLeft())
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        doc.documentLayout().draw(painter, QAbstractTextDocumentLayout.PaintContext())
        painter.restore()

    def sizeHint(self, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        doc = QTextDocument()
        doc.setDocumentMargin(1)
        width = option.rect.width()
        if width <= 0:
            width = 400
        doc.setTextWidth(width)
        doc.setHtml(self.__markup(index))
        return QSize(width, int(doc.size().height()))

    def __markup(self, index: QModelIndex):
        row = index.data() or {}
        serial = row.get('serial') or '—'
        device = row.get('deviceCodeName') or '—'
        plugin = row.get('pluginTitle') or (row.get('pluginCodeRef') or '').split('.')[-1] or '—'
        user = row.get('username') or '—'
        html = '''
            <style type="text/css">
                table { color: white; border-width: 0px; border-collapse: collapse; }
            </style>
            <body width=100%>
            <table width=100% border=1>
            <tr>
                <td colspan="4" style="font-weight:bold;text-align:center;background-color:#404040;">
                    %serial% &mdash; %device%
                </td>
            </tr>
            <tr>
                <td width=25%>Serial</td>
                <td width=25%>Device</td>
                <td width=25%>Plugin</td>
                <td width=25%>User</td>
            </tr>
            <tr>
                <td width=25%>%serial%</td>
                <td width=25%>%device%</td>
                <td width=25%>%plugin%</td>
                <td width=25%>%user%</td>
            </tr>
            </table>
            </body>
            '''
        html = html.replace('%serial%', serial).replace('%device%', device)
        html = html.replace('%plugin%', plugin).replace('%user%', user)
        return html
