from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel


class TypewriterLabel(QLabel):
    """A QLabel that reveals its text CHARACTER-BY-CHARACTER at a words-per-minute cadence — a typewriter.

    Doc-mode narration helper (SPEC_doc_automation §18.7): used by the cover card's agenda so the overview
    points type in ("letter-typing fashion", Edwin). A small shared component — any doc-mode surface can
    reuse it. Deliberately char-granular, NOT the doc-panel's sentence/word chunker (`__buildChunks`), which
    collapses period-less text into a single word-wise chunk.

    Stop-safe: `type()` cancels any running reveal before restarting, and `hideEvent` stops the timer — so a
    re-show or a nav-away never leaves a second timer ticking a hidden label.
    """

    DEFAULT_WPM = 180
    MIN_TICK_MS = 20
    CHARS_PER_WORD = 5   # wpm → chars/min: a word ≈ 5 characters (+ its space)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWordWrap(True)
        self.__full = ""
        self.__shown = 0
        self.__wpm = float(self.DEFAULT_WPM)
        self.__timer = QTimer(self)
        self.__timer.setSingleShot(True)
        self.__timer.timeout.connect(self.__tick)

    def type(self, text, wpm=None):
        """Reveal `text` char-by-char. Falsy `text` clears immediately (stop-on-set)."""
        self.__timer.stop()
        if wpm:
            self.__wpm = float(wpm)
        self.__full = text or ""
        self.__shown = 0
        super().setText("")
        if self.__full:
            self.__tick()

    def clear(self):
        self.__timer.stop()
        self.__full = ""
        self.__shown = 0
        super().setText("")

    def __tick(self):
        if self.__shown >= len(self.__full):
            return
        self.__shown += 1
        super().setText(self.__full[:self.__shown])
        per_char_ms = 60000.0 / max(60.0, self.__wpm) / self.CHARS_PER_WORD
        self.__timer.start(max(self.MIN_TICK_MS, int(per_char_ms)))

    def hideEvent(self, event):
        self.__timer.stop()
        super().hideEvent(event)
