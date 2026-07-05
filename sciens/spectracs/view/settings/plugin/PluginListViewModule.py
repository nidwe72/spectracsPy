from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import QAbstractItemView, QGridLayout, QGroupBox, QLabel, QPushButton, QTableView

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.appliction.style.Metrics import Metrics
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.model.databaseEntity.application.user.UserRoleType import UserRoleType
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget
from sciens.spectracs.view.application.widgets.table.TableLayoutUtil import applyTableLayout


class PluginsTableModel(QAbstractTableModel):
    HEADERS = ['Title', 'Code reference', 'Version']

    def __init__(self, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.__plugins = []

    def setPlugins(self, plugins):
        self.beginResetModel()
        self.__plugins = plugins or []
        self.endResetModel()

    def getPluginAt(self, row: int):
        if 0 <= row < len(self.__plugins):
            return self.__plugins[row]
        return None

    def rowCount(self, parent=QModelIndex()):
        return len(self.__plugins)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        plugin = self.__plugins[index.row()]
        column = index.column()
        if column == 0:
            return plugin.get('title')
        if column == 1:
            return plugin.get('codeRef')
        if column == 2:
            return plugin.get('version')
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[section]
        return None


class PluginListViewModule(PageWidget):
    """Master Plugin catalog (SPEC_connection_and_calibration_ux.md §4.1.a)."""

    tableView: QTableView = None
    pluginsTableModel: PluginsTableModel = None
    bannerLabel: QLabel = None

    def _getPageTitle(self):
        return "Settings > Plugins"

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()

        if self.bannerLabel is None:
            self.bannerLabel = QLabel("")
            self.bannerLabel.setVisible(False)
        result['banner'] = self.bannerLabel

        if self.tableView is None:
            self.tableView = QTableView()
        self.tableView.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableView.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableView.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.pluginsTableModel = PluginsTableModel()
        self.tableView.setModel(self.pluginsTableModel)
        applyTableLayout(self.tableView)
        self.tableView.verticalHeader().setVisible(False)
        self.tableView.doubleClicked.connect(self.onDoubleClickedRow)
        result['table'] = self.tableView

        self.refresh()
        return result

    def showEvent(self, event):
        super().showEvent(event)
        if self.pluginsTableModel is not None:
            self.refresh()

    def refresh(self):
        if not CurrentUserSession().hasRole(UserRoleType.MASTER_USER.value):
            self.__showBanner("Not authorized.")
            self.pluginsTableModel.setPlugins([])
            return
        plugins = SpectracsPyServerClient().listPlugins()
        if plugins is None:
            self.__showBanner("Server unavailable — cannot load plugins.")
            self.pluginsTableModel.setPlugins([])
        else:
            self.bannerLabel.setVisible(False)
            self.pluginsTableModel.setPlugins(plugins)

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

    def __getSelectedPlugin(self):
        index = self.tableView.currentIndex()
        if index is not None and index.isValid():
            return self.pluginsTableModel.getPluginAt(index.row())
        return None

    def onClickedAddButton(self):
        self.__openEditor(None)

    def onClickedEditButton(self):
        plugin = self.__getSelectedPlugin()
        if plugin is not None:
            self.__openEditor(plugin)

    def onDoubleClickedRow(self, index):
        self.onClickedEditButton()

    def __openEditor(self, dto):
        from sciens.spectracs.view.settings.plugin.PluginViewModule import PluginViewModule
        navigationSignal = NavigationSignal(None)
        navigationSignal.setTarget("PluginViewModule")
        targetViewModule = ApplicationContextLogicModule().getNavigationHandler().getViewModule(navigationSignal)
        if isinstance(targetViewModule, PluginViewModule):
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
