from PySide6.QtWidgets import QWidget, QGridLayout

from sciens.spectracs.logic.appliction.style.Metrics import Metrics


class ResponsiveRow(QWidget):
    """R3: lays its children in one horizontal row while there is room, and stacks them vertically
    when the available width is too small (phone). Re-flows on resize. Both OS benefit from the same
    widget — desktop keeps the row, the phone stacks the identical children, with no per-OS branch.

    Used for control rows that otherwise overflow at 412 dp: a graph beside its Edit button, a row of
    action buttons, etc. See docs/SPEC_phone_width_responsiveness.md (R3)."""

    def __init__(self, widgets, spacing=None, parent=None):
        super().__init__(parent)
        self._widgets = list(widgets)
        self._horizontal = None
        self._grid = QGridLayout()
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(Metrics.S if spacing is None else spacing)
        self.setLayout(self._grid)
        self._relayout(True)

    def _naturalWidth(self):
        """Combined preferred width of the children in a single row (stable — from child sizeHints,
        not the current layout — so the horizontal/vertical decision can't oscillate)."""
        total = sum(w.sizeHint().width() for w in self._widgets)
        total += self._grid.spacing() * max(0, len(self._widgets) - 1)
        return total

    def _relayout(self, horizontal):
        if horizontal == self._horizontal:
            return
        self._horizontal = horizontal
        for i, w in enumerate(self._widgets):
            self._grid.removeWidget(w)
            self._grid.setColumnStretch(i, 0)
        for i, w in enumerate(self._widgets):
            if horizontal:
                self._grid.addWidget(w, 0, i, 1, 1)
                self._grid.setColumnStretch(i, 1)  # share the width evenly across the row
            else:
                self._grid.addWidget(w, i, 0, 1, 1)

    def resizeEvent(self, event):
        self._relayout(event.size().width() >= self._naturalWidth())
        super().resizeEvent(event)
