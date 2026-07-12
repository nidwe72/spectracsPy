from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel


class DocHintPanelViewModule(QFrame):
    """Right-side documentation hint panel, shown only in --doc-mode (SPEC_doc_automation §2.2).

    A pure display surface: an external Director script pushes narration text over UDP
    (DocModeUdpService.set_hint) and it renders here beside the running app so a screencast can
    explain each step. It carries no app logic and is never constructed outside doc-mode."""

    WIDTH = 320  # reads well at 1080p without dominating the app; see spec §2.2

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setObjectName("docHintPanel")
        self.setFixedWidth(self.WIDTH)
        self.setStyleSheet(
            "#docHintPanel { background: #2B2B2B; border-left: 1px solid #5A5A5A; }"
            "#docHintPanel QLabel { color: #E8E8E8; }"
            "#docHintPanel #docHintPanelTitle { color: #9AA0A6; font-size: 12px; font-weight: bold; }"
            "#docHintPanel #docHintPanelLabel { font-size: 18px; }")

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        self.setLayout(layout)

        title = QLabel("DOCUMENTATION")
        title.setObjectName("docHintPanelTitle")
        layout.addWidget(title)

        self.__label = QLabel("Waiting for Director…")
        self.__label.setObjectName("docHintPanelLabel")
        self.__label.setWordWrap(True)
        self.__label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.__label)
        layout.addStretch(1)

    def setHint(self, text):
        self.__label.setText(text)
