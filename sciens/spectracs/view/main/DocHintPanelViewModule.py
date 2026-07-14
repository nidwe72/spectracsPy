import re

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel


class DocHintPanelViewModule(QFrame):
    """Right-side documentation panel, shown only in --doc-mode (SPEC_doc_automation §2.2, §16.4).

    Three stacked zones mapping to the screencast heading hierarchy:
      1. use-case  (H1, persistent),
      2. phase outline  (current = ▸ bold, done = ✓, upcoming = dim),
      3. caption  (the current step, or a metric description) revealed progressively — sentence by
         sentence, dropping to word-by-word for long sentences — at DOC_WPM cadence.

    A pure display surface: an external Director pushes `doc` / `set_hint` datagrams over UDP
    (DocModeUdpService) and it renders here beside the running app. It carries no app logic and is never
    constructed outside doc-mode. This is the SECOND narration layer — the app's own status-bar coach line
    (AcquisitionGuidance) is the first; both show at once by design (SPEC §16.0 / §17)."""

    WIDTH = 320  # reads well at 1080p without dominating the app; see spec §2.2
    DEFAULT_WPM = 180
    WORD_WISE_THRESHOLD = 12   # sentences longer than this reveal word-by-word (§16.4)
    MIN_TICK_MS = 40

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setObjectName("docHintPanel")
        self.setFixedWidth(self.WIDTH)
        self.setStyleSheet(
            "#docHintPanel { background: #2B2B2B; border-left: 1px solid #5A5A5A; }"
            "#docHintPanel QLabel { color: #E8E8E8; }"
            "#docHintPanel #docHintPanelTitle { color: #9AA0A6; font-size: 11px; font-weight: bold;"
            " letter-spacing: 1px; }"
            "#docHintPanel #docHintPanelUseCase { font-size: 22px; font-weight: bold; }"
            "#docHintPanel #docHintPanelOutline { font-size: 15px; }"
            "#docHintPanel #docHintPanelCaption { font-size: 17px; }")

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        self.setLayout(layout)

        title = QLabel("DOCUMENTATION")
        title.setObjectName("docHintPanelTitle")
        layout.addWidget(title)

        self.__useCaseLabel = self.__zone("docHintPanelUseCase", "")
        layout.addWidget(self.__useCaseLabel)
        layout.addWidget(self.__separator())

        self.__outlineLabel = self.__zone("docHintPanelOutline", "")
        self.__outlineLabel.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.__outlineLabel)
        layout.addWidget(self.__separator())

        self.__captionLabel = self.__zone("docHintPanelCaption", "Waiting for Director…")
        layout.addWidget(self.__captionLabel)
        layout.addStretch(1)

        # progressive-reveal state (§16.4)
        self.__wpm = self.DEFAULT_WPM
        self.__outline = []
        self.__currentPhaseIndex = None
        self.__chunks = []
        self.__chunkIndex = 0
        self.__shown = ""
        self.__revealTimer = QTimer(self)
        self.__revealTimer.setSingleShot(True)
        self.__revealTimer.timeout.connect(self.__onRevealTick)

    # --- construction helpers ---

    def __zone(self, objectName, text):
        label = QLabel(text)
        label.setObjectName(objectName)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        return label

    def __separator(self):
        line = QLabel("──────────────")
        line.setStyleSheet("color: #444444;")
        return line

    # --- public API (driven by DocModeUdpService) ---

    def applyDoc(self, use_case=None, outline=None, phase=None, caption=None, reveal=None, wpm=None):
        """Update only the zones present in a `doc` datagram (§16.4 / §16.11)."""
        if wpm is not None:
            try:
                self.__wpm = float(wpm)
            except (TypeError, ValueError):
                pass
        if use_case is not None:
            self.__useCaseLabel.setText(use_case)
        if outline is not None:
            self.__outline = [str(item) for item in outline]
            self.__currentPhaseIndex = None
            self.__renderOutline()
        if phase is not None:
            self.__setCurrentPhase(phase)
        if caption is not None:
            self.setCaption(caption, reveal=self.__wantsReveal(reveal))

    def setHint(self, text):
        """Back-compat alias for M1 scenarios and the `set_hint` command: set the caption (§16.11)."""
        self.setCaption(text or "", reveal=True)

    def setCaption(self, text, reveal=True):
        self.__revealTimer.stop()
        text = text or ""
        if not reveal or not text:
            self.__captionLabel.setText(text)
            return
        self.__chunks = self.__buildChunks(text)
        self.__chunkIndex = 0
        self.__shown = ""
        self.__captionLabel.setText("")
        self.__onRevealTick()

    # --- outline rendering ---

    def __setCurrentPhase(self, phase):
        target = str(phase).strip().lower()
        self.__currentPhaseIndex = None
        for index, label in enumerate(self.__outline):
            if label.strip().lower() == target:
                self.__currentPhaseIndex = index
                break
        self.__renderOutline()

    def __renderOutline(self):
        lines = []
        for index, label in enumerate(self.__outline):
            if self.__currentPhaseIndex is not None and index < self.__currentPhaseIndex:
                lines.append('<span style="color:#7CB342;">&#10003; %s</span>' % label)       # done
            elif self.__currentPhaseIndex is not None and index == self.__currentPhaseIndex:
                lines.append('<span style="color:#F5F5F5; font-weight:bold;">&#9656; %s</span>' % label)  # current
            else:
                lines.append('<span style="color:#6B7075;">%s</span>' % label)                 # upcoming
        self.__outlineLabel.setText("<br>".join(lines))

    # --- progressive reveal (§16.4) ---

    def __wantsReveal(self, reveal):
        if reveal is None:
            return True
        if isinstance(reveal, str):
            return reveal.lower() not in ("false", "none", "off", "0")
        return bool(reveal)

    def __buildChunks(self, text):
        # Split into sentences; a short sentence reveals whole, a long one word-by-word (Edwin's ask #3).
        chunks = []
        for sentence in re.findall(r"[^.!?]+[.!?]?\s*", text):
            if not sentence.strip():
                continue
            words = sentence.split(" ")
            if len([word for word in words if word.strip()]) > self.WORD_WISE_THRESHOLD:
                for index, word in enumerate(words):
                    chunks.append(word if index == len(words) - 1 else word + " ")
            else:
                chunks.append(sentence)
        return chunks or [text]

    def __onRevealTick(self):
        if self.__chunkIndex >= len(self.__chunks):
            return
        chunk = self.__chunks[self.__chunkIndex]
        self.__shown += chunk
        self.__captionLabel.setText(self.__shown)
        self.__chunkIndex += 1
        words = max(1, len([word for word in chunk.split(" ") if word.strip()]))
        per_word_ms = 60000.0 / max(60.0, self.__wpm)
        self.__revealTimer.start(max(self.MIN_TICK_MS, int(words * per_word_ms)))
