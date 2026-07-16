from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from sciens.spectracs.logic.application.style.LogoRenderer import renderLogoPixmap
from sciens.spectracs.view.application.widgets.TypewriterLabel import TypewriterLabel
from sciens.spectracs.view.main.MainStatusBarViewModule import MainStatusBarViewModule


class DocCoverViewModule(QFrame):
    """Doc-mode-only title card, shown as a PAGE in the MainViewModule stack (SPEC_doc_automation §18.1).

    Its job is to keep the measurements-overview (Home) out of the recording: the Director makes this page
    current (`cover` UDP command → setCurrentWidget) at the start of each use case and during the post-login
    camera handoff, so Home is never navigated to / never filmed. Being a stack page — not a floating overlay
    — means switching TO it fires the prior view's hideEvent, which is exactly what releases /dev/video0.

    Renders the Spectracs wordmark centred above a breadcrumb `Documentation › <use case>` (finer-grained per
    Edwin). Never constructed outside doc-mode; it carries no app logic. The logo uses the shared LogoRenderer
    (C1a) so it matches the header wordmark exactly.
    """

    LOGO_HEIGHT = 90
    AGENDA_MAX_WIDTH = 720   # keep the point list a readable column, not full-window (rubber-duck CR-B.5)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setObjectName("docCoverViewModule")
        self.setStyleSheet(
            "#docCoverViewModule { background: #2B2B2B; }"
            "#docCoverViewModule #docCoverBreadcrumb { color: #E8E8E8; font-size: 22px;"
            " letter-spacing: 1px; }"
            "#docCoverViewModule #docCoverAgenda { color: #E8E8E8; font-size: 18px; }")

        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

        layout.addStretch(1)

        self.__logoLabel = QLabel()
        self.__logoLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.__logoLabel.setPixmap(renderLogoPixmap(MainStatusBarViewModule.logo_png, self.LOGO_HEIGHT))
        layout.addWidget(self.__logoLabel)

        self.__breadcrumb = QLabel("Documentation")
        self.__breadcrumb.setObjectName("docCoverBreadcrumb")
        self.__breadcrumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.__breadcrumb)

        # Agenda zone (§18.7 CR-B): the overview points, typed in char-by-char. A max-width, left-aligned
        # bullet block centred as a whole; hidden until points are set (so card #1 shows logo + breadcrumb only).
        self.__agenda = TypewriterLabel()
        self.__agenda.setObjectName("docCoverAgenda")
        self.__agenda.setMaximumWidth(self.AGENDA_MAX_WIDTH)
        self.__agenda.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.__agenda.setVisible(False)
        layout.addWidget(self.__agenda, alignment=Qt.AlignmentFlag.AlignHCenter)

        layout.addStretch(1)

    def setLabel(self, useCase):
        """Set the breadcrumb: `Documentation › <use case>`, or just `Documentation` when no use case."""
        useCase = (useCase or "").strip()
        self.__breadcrumb.setText("Documentation › %s" % useCase if useCase else "Documentation")

    def setPoints(self, points, wpm=None):
        """Type the overview points in (bulleted, char-by-char). Falsy `points` CLEARS the agenda and hides
        the zone — so a card shown without points (card #1) never flashes a prior run's agenda (CR-B.4)."""
        if not points:
            self.__agenda.clear()
            self.__agenda.setVisible(False)
            return
        lines = "\n".join("•  %s" % str(point).strip() for point in points)
        self.__agenda.setVisible(True)
        self.__agenda.type(lines, wpm)
