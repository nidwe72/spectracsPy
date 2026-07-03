from PySide6.QtWidgets import QHeaderView
from PySide6 import QtCore


def applyTableLayout(view):
    """R4: make a table fit the viewport width instead of clipping its right-most column behind the
    frame at 412 dp. Every column shares the width (Stretch) and long cell text elides with an
    ellipsis, so all columns stay visible with no horizontal scroll -- the failure mode on the phone
    was the last column ("Enabled") pushed off the right edge. Shared util so every table behaves the
    same on both OS. See docs/SPEC_phone_width_responsiveness.md (R4)."""
    header = view.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    header.setMinimumSectionSize(40)
    view.setTextElideMode(QtCore.Qt.TextElideMode.ElideRight)
    view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    view.setWordWrap(False)
