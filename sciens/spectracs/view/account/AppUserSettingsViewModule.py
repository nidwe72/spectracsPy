from datetime import datetime

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QTabWidget, QWidget, QGridLayout, QHBoxLayout, QPushButton, QLabel, \
    QTableView, QAbstractItemView

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.application.style.Metrics import Metrics
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.model.application.navigation.NavigationSignal import NavigationSignal
from sciens.spectracs.view.application.widgets.InWindowDialog import InWindowDialog
from sciens.spectracs.view.application.widgets.page.PageWidget import PageWidget
from sciens.spectracs.view.application.widgets.table.TableLayoutUtil import applyTableLayout


def formatAmount(amountMinor, currency) -> str:
    """de_AT display: integer minor units -> '1,00 €' (comma decimal, trailing symbol). Storage
    stays integer minor units; this is display only (OQ4). Falls back to the currency code for
    non-EUR."""
    if amountMinor is None:
        return ""
    text = "%d,%02d" % (abs(int(amountMinor)) // 100, abs(int(amountMinor)) % 100)
    if int(amountMinor) < 0:
        text = "-" + text
    if currency == "EUR":
        return "%s €" % text
    return "%s %s" % (text, currency or "")


def formatDate(isoString) -> str:
    # de_AT: dd.MM.yyyy HH:MM. The DTO carries createdAt as an ISO string.
    if not isoString:
        return ""
    try:
        moment = datetime.fromisoformat(isoString)
        return moment.strftime("%d.%m.%Y %H:%M")
    except (ValueError, TypeError):
        return str(isoString)


class AppUserSettingsViewModule(PageWidget):
    """Per-user account screen (SPEC_paypal_payment.md §4.3), reached from the header account menu.
    A QTabWidget: read-only Profile + a Payment tab (Pay button + poll-capture handshake + the
    user's transactions). One shared screen for both roles; the Payment tab is written from the
    end-user's perspective. Desktop only in M1 (the account menu is skipped on Android)."""

    tabWidget: QTabWidget = None
    # profile tab value labels
    profileUsernameValue: QLabel = None
    profileRolesValue: QLabel = None
    profileSerialValue: QLabel = None
    profileUserIdValue: QLabel = None
    # payment tab widgets
    paymentBanner: QLabel = None
    payButton: QPushButton = None
    transactionsTableView: QTableView = None
    transactionsModel = None

    def _getPageTitle(self):
        return "Account settings"

    def getMainContainerWidgets(self):
        result = super().getMainContainerWidgets()
        if self.tabWidget is None:
            self.tabWidget = QTabWidget()
            self.tabWidget.addTab(self.__buildProfileTab(), "Profile")
            self.tabWidget.addTab(self.__buildPaymentTab(), "Payment")
        result['tabs'] = self.tabWidget
        return result

    def createNavigationGroupBox(self):
        result = super().createNavigationGroupBox()
        layout = result.layout()
        backButton = QPushButton("Back")
        layout.addWidget(backButton, 0, 0, 1, 1)
        backButton.clicked.connect(self.onClickedBack)
        return result

    def showEvent(self, event):
        # Session-dependent, so re-read every time the page is navigated to (the build-time pass runs
        # at startup while logged out).
        super().showEvent(event)
        self.__refresh()

    # --- profile tab --------------------------------------------------------
    def __buildProfileTab(self) -> QWidget:
        self.profileUsernameValue = QLabel("")
        self.profileRolesValue = QLabel("")
        self.profileSerialValue = QLabel("")
        self.profileUserIdValue = QLabel("")
        form = self.createForm([
            ("Username", self.profileUsernameValue),
            ("Roles", self.profileRolesValue),
            ("Registered serial", self.profileSerialValue),
            ("User id", self.profileUserIdValue),
        ])
        hint = self.createMessageLabel("Read-only. User administration is under Settings > Users.")

        container = QWidget()
        layout = QGridLayout(container)
        layout.setContentsMargins(0, Metrics.S, 0, 0)
        layout.setSpacing(Metrics.S)
        layout.addWidget(form, 0, 0, 1, 1)
        layout.addWidget(hint, 1, 0, 1, 1)
        layout.setRowStretch(2, 1)
        return container

    # --- payment tab --------------------------------------------------------
    def __buildPaymentTab(self) -> QWidget:
        container = QWidget()
        layout = QGridLayout(container)
        layout.setContentsMargins(0, Metrics.S, 0, 0)
        layout.setSpacing(Metrics.S)

        heading = QLabel("Billing — Spectracs SaaS (sandbox)")
        heading.setProperty("style-bold", True)
        heading.setStyleSheet("font-weight: bold;")
        layout.addWidget(heading, 0, 0, 1, 1)

        subtitle = self.createMessageLabel(
            "Plan: monthly rental — no active subscription yet. This is a one-off sandbox test payment.")
        layout.addWidget(subtitle, 1, 0, 1, 1)

        self.paymentBanner = QLabel("")
        self.paymentBanner.setWordWrap(True)
        self.paymentBanner.setVisible(False)
        layout.addWidget(self.paymentBanner, 2, 0, 1, 1)

        payRow = QWidget()
        payRowLayout = QHBoxLayout(payRow)
        payRowLayout.setContentsMargins(0, 0, 0, 0)
        self.payButton = QPushButton("Pay 1,00 € (sandbox)")
        self.payButton.clicked.connect(self.onClickedPay)
        payRowLayout.addWidget(self.payButton)
        payRowLayout.addStretch(1)
        layout.addWidget(payRow, 3, 0, 1, 1)

        transactionsHeaderRow = QWidget()
        headerLayout = QHBoxLayout(transactionsHeaderRow)
        headerLayout.setContentsMargins(0, 0, 0, 0)
        transactionsLabel = QLabel("Transactions")
        transactionsLabel.setProperty("style-bold", True)
        transactionsLabel.setStyleSheet("font-weight: bold;")
        headerLayout.addWidget(transactionsLabel)
        headerLayout.addStretch(1)
        refreshButton = QPushButton("Refresh")
        refreshButton.setProperty("buttonType", "secondary")
        refreshButton.clicked.connect(self.__refreshTransactions)
        headerLayout.addWidget(refreshButton)
        layout.addWidget(transactionsHeaderRow, 4, 0, 1, 1)

        self.transactionsTableView = QTableView()
        self.transactionsTableView.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.transactionsTableView.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.transactionsTableView.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.transactionsModel = TransactionsTableModel()
        self.transactionsTableView.setModel(self.transactionsModel)
        applyTableLayout(self.transactionsTableView)
        self.transactionsTableView.verticalHeader().setVisible(False)
        layout.addWidget(self.transactionsTableView, 5, 0, 1, 1)
        layout.setRowStretch(5, 1)

        return container

    # --- behaviour ----------------------------------------------------------
    def onClickedPay(self):
        userId = CurrentUserSession().userId
        if userId is None:
            InWindowDialog.notify(self, "Not logged in", "Please log in before making a payment.")
            return

        self.payButton.setEnabled(False)
        try:
            created = SpectracsPyServerClient().createPayment(userId)
        finally:
            self.payButton.setEnabled(True)

        if not created.get("ok"):
            InWindowDialog.notify(self, "Payment", created.get("message") or "Could not start the payment.")
            return

        orderId = created.get("orderId")
        approvalUrl = created.get("approvalUrl")
        if approvalUrl:
            QDesktopServices.openUrl(QUrl(approvalUrl))

        approved = InWindowDialog.choose(
            self, "Complete your payment",
            "A PayPal approval page opened in your browser. Log in as the sandbox buyer and approve "
            "the 1,00 € payment.\n\nWhen you have approved it there, click below.",
            [("Cancel", False, "secondary"), ("I've approved — capture", True, None)])
        if not approved:
            self.__refreshTransactions()
            return

        self.payButton.setEnabled(False)
        try:
            captured = SpectracsPyServerClient().capturePayment(userId, orderId)
        finally:
            self.payButton.setEnabled(True)

        status = captured.get("status")
        if captured.get("ok") and status == "CAPTURED":
            InWindowDialog.notify(self, "Payment complete", "Your payment was captured. Thank you!")
        elif captured.get("message") == "not approved yet":
            InWindowDialog.notify(
                self, "Not approved yet",
                "The payment has not been approved yet. Approve it in the browser, then click "
                "Pay again to retry.")
        else:
            InWindowDialog.notify(self, "Payment not completed",
                                  captured.get("message") or ("Status: %s" % status))
        self.__refreshTransactions()

    def onClickedBack(self):
        signal = NavigationSignal(None)
        signal.setTarget("Home")
        self.__emitNavigation(signal)

    def __refresh(self):
        session = CurrentUserSession()
        if self.profileUsernameValue is not None:
            self.profileUsernameValue.setText(session.username or "—")
            self.profileRolesValue.setText(", ".join(session.roles) if session.roles else "—")
            self.profileSerialValue.setText(session.registeredSerial or "—")
            self.profileUserIdValue.setText(session.userId or "—")
        self.__refreshTransactions()

    def __refreshTransactions(self):
        if self.transactionsModel is None:
            return
        userId = CurrentUserSession().userId
        if userId is None:
            self.__showBanner("Log in to make a payment and see your transactions.")
            self.transactionsModel.setTransactions([])
            self.payButton.setEnabled(False)
            return
        self.payButton.setEnabled(True)
        transactions = SpectracsPyServerClient().listTransactions(userId)
        self.paymentBanner.setVisible(False)
        self.transactionsModel.setTransactions(transactions or [])

    def __showBanner(self, text: str):
        self.paymentBanner.setText(text)
        self.paymentBanner.setVisible(True)

    def __emitNavigation(self, navigationSignal: NavigationSignal):
        ApplicationContextLogicModule().getApplicationSignalsProvider().navigationSignal.connect(
            ApplicationContextLogicModule().getNavigationHandler().handleNavigationSignal)
        ApplicationContextLogicModule().getApplicationSignalsProvider().emitNavigationSignal(navigationSignal)


class TransactionsTableModel(QAbstractTableModel):
    HEADERS = ['Date', 'Amount', 'Status', 'PayPal order id']

    def __init__(self, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.__transactions = []

    def setTransactions(self, transactions):
        self.beginResetModel()
        self.__transactions = transactions or []
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self.__transactions)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        transaction = self.__transactions[index.row()]
        column = index.column()
        if column == 0:
            return formatDate(transaction.get('createdAt'))
        if column == 1:
            return formatAmount(transaction.get('amountMinor'), transaction.get('currency'))
        if column == 2:
            return transaction.get('status')
        if column == 3:
            return transaction.get('providerOrderId')
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.HEADERS[section]
        return None
