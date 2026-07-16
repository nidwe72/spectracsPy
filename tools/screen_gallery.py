#!/usr/bin/env python3
"""Offscreen screen-gallery harness for the Spectracs desktop app.

Boots the real `MainViewModule` stack headlessly (QT_QPA_PLATFORM=offscreen),
switches to each top-level screen, grabs it to a PNG, and writes a second
annotated PNG that classifies every QGroupBox panel:

    red    = untitled box        (nav rows / region holders -> border should go)
    orange = single-child frame  (title duplicates one control -> demote)
    green  = legitimate group    (titled, 2+ children -> border kept)

No clicking, no GUI automation, no server required (master-data sync no-ops).
Re-run before/after any UI change for a visual-regression diff.

Usage:
    ./venv/bin/python tools/screen_gallery.py [OUT_DIR]

OUT_DIR defaults to ./.gallery (git-ignored). A JSON classification summary is
printed to stdout.

See docs/SPEC_visual_harmonization.md (Workstream C, §9.5).
"""
import json
import os
import sys

# Run headless by default so this works over SSH / in CI.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# `sciens` is a PEP-420 namespace package split across sibling repos; put their
# roots on the path so the tool runs without a pre-set PYTHONPATH.
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _rel in (".", "../spectracsPy-model", "../spectracsPy-base", "../spectracsPy-server"):
    _p = os.path.normpath(os.path.join(_REPO, _rel))
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PySide6 import QtWidgets, QtGui
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtWidgets import QGroupBox, QPushButton, QLineEdit, QComboBox

from sciens.spectracs.logic.application.style.ApplicationStyleLogicModule import ApplicationStyleLogicModule
from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.view.main.MainContainerViewModule import MainContainerViewModule

# Top-level screens in MainViewModule stack order (see NavigationHandlerLogicModule).
SCREEN_NAMES = [
    "S0-Home", "S1-SpectralJob", "S2-SpectralJobImport", "S3-Settings",
    "S4-ProfileList", "S5-Profile", "S6-CalibrationProfile",
    "S7-VirtualSpectrometer", "S8-Connection",
]

RED = QtGui.QColor(225, 70, 70)
ORANGE = QtGui.QColor(235, 165, 40)
GREEN = QtGui.QColor(70, 205, 110)


def _classify(group_box):
    """Return (tag, color) for a QGroupBox using the §9.2 buckets."""
    title = group_box.title()
    n_children = (
        len([w for w in group_box.findChildren(QPushButton) if w.isVisible()])
        + len([w for w in group_box.findChildren(QLineEdit) if w.isVisible()])
        + len([w for w in group_box.findChildren(QComboBox) if w.isVisible()])
    )
    if title == "":
        return "UNTITLED", RED, n_children
    if n_children <= 1:
        return "SINGLE-child-frame", ORANGE, n_children
    return "GROUP-ok", GREEN, n_children


def _badge(painter, rect, num, color, tag):
    pen = QtGui.QPen(color)
    pen.setWidth(3)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawRect(rect)
    painter.fillRect(QRect(rect.left(), rect.top(), 185, 18), color)
    painter.setPen(QtGui.QPen(QtGui.QColor(20, 20, 20)))
    font = QtGui.QFont()
    font.setBold(True)
    font.setPointSize(9)
    painter.setFont(font)
    painter.drawText(rect.left() + 4, rect.top() + 14, "#%d %s" % (num, tag))


def build_gallery(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setStyleSheet(ApplicationStyleLogicModule().getApplicationStyleSheet())

    main_container = MainContainerViewModule()
    ApplicationContextLogicModule().getNavigationHandler().mainContainerViewModule = main_container
    main_container.resize(1100, 820)
    main_container.show()
    stack = main_container.mainViewModule

    summary = {}
    for index in range(stack.count()):
        stack.setCurrentIndex(index)
        app.processEvents()
        name = SCREEN_NAMES[index] if index < len(SCREEN_NAMES) else "S%d" % index

        pixmap = main_container.grab()
        pixmap.save(os.path.join(out_dir, name + ".png"))

        annotated = main_container.grab()
        painter = QtGui.QPainter(annotated)
        rows = []
        num = 1
        for group_box in main_container.findChildren(QGroupBox):
            if not group_box.isVisible() or group_box.width() < 10:
                continue
            top_left = group_box.mapTo(main_container, QPoint(0, 0))
            rect = QRect(top_left, group_box.size())
            if rect.top() < 0 or rect.left() < 0:
                continue
            tag, color, n_children = _classify(group_box)
            _badge(painter, rect, num, color, tag)
            rows.append({"num": num, "title": group_box.title() or "(untitled)",
                         "class": tag, "children": n_children})
            num += 1
        painter.end()
        annotated.save(os.path.join(out_dir, name + ".annot.png"))
        summary[name] = rows
    return summary


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(_REPO, ".gallery")
    summary = build_gallery(out_dir)
    # Write the classification to a file (the app prints sync noise to stdout,
    # so stdout is not a reliable JSON channel).
    summary_path = os.path.join(out_dir, "summary.json")
    with open(summary_path, "w") as handle:
        json.dump(summary, handle, indent=1)
    print("\nwrote %d screens + %s to: %s"
          % (len(summary), os.path.basename(summary_path), out_dir), file=sys.stderr)


if __name__ == "__main__":
    main()
