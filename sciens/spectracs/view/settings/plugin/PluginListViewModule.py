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

    # R2: reusable SELECT mode (SPEC §11) — the same list doubles as a plugin picker launched from the
    # SpectrometerSetup editor. When a callback is armed the nav bar shows Back/Select (Add/Edit hidden),
    # a chosen row is handed back to the caller, and navigation returns to the launching screen.
    addButton: QPushButton = None
    editButton: QPushButton = None
    selectButton: QPushButton = None
    _selectCallback = None
    _returnTarget = None

    def _getPageTitle(self):
        return "Settings > Plugins"

    def enterSelectMode(self, onSelect, returnTarget):
        self._selectCallback = onSelect
        self._returnTarget = returnTarget
        self.__applyMode()
        self.refresh()

    def exitSelectMode(self):
        self._selectCallback = None
        self._returnTarget = None
        self.__applyMode()

    def __applyMode(self):
        selecting = self._selectCallback is not None
        if self.addButton is not None:
            self.addButton.setVisible(not selecting)
        if self.editButton is not None:
            self.editButton.setVisible(not selecting)
        if self.selectButton is not None:
            self.selectButton.setVisible(selecting)

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

        self.addButton = QPushButton()
        self.addButton.setText("Add")
        layout.addWidget(self.addButton, 0, 1, 1, 1)
        self.addButton.clicked.connect(self.onClickedAddButton)

        self.editButton = QPushButton()
        self.editButton.setText("Edit")
        layout.addWidget(self.editButton, 0, 2, 1, 1)
        self.editButton.clicked.connect(self.onClickedEditButton)

        self.selectButton = QPushButton()
        self.selectButton.setText("Select")
        layout.addWidget(self.selectButton, 0, 3, 1, 1)
        self.selectButton.clicked.connect(self.onClickedSelectButton)

        self.__applyMode()  # start in normal (CRUD) mode: Select hidden
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
        if self._selectCallback is not None:
            self.onClickedSelectButton()
        else:
            self.onClickedEditButton()

    def onClickedSelectButton(self):
        plugin = self.__getSelectedPlugin()
        if plugin is None:
            return
        callback = self._selectCallback
        returnTarget = self._returnTarget
        self.exitSelectMode()
        if callback is not None:
            callback(plugin)
        navigationSignal = NavigationSignal(None)
        navigationSignal.setTarget(returnTarget or "SettingsViewModule")
        self.__emitNavigation(navigationSignal)

    def __openEditor(self, dto):
        from sciens.spectracs.view.settings.plugin.PluginViewModule import PluginViewModule
        navigationSignal = NavigationSignal(None)
        navigationSignal.setTarget("PluginViewModule")
        targetViewModule = ApplicationContextLogicModule().getNavigationHandler().getViewModule(navigationSignal)
        if isinstance(targetViewModule, PluginViewModule):
            targetViewModule.loadView(dto)
            self.__emitNavigation(navigationSignal)

    def onClickedBackButton(self):
        # In select mode, Back returns to the launching screen and disarms the picker.
        returnTarget = self._returnTarget
        if self._selectCallback is not None:
            self.exitSelectMode()
        navigationSignal = NavigationSignal(None)
        navigationSignal.setTarget(returnTarget or "SettingsViewModule")
        self.__emitNavigation(navigationSignal)

    def __emitNavigation(self, navigationSignal: NavigationSignal):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(navigationSignal)
