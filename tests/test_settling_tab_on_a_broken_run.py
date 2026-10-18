"""A run with no value still shows its Settling curves (found at the rig 2026-10-18).

A MEASUREMENT_BROKEN run carries rows whose metric is None. pyqtgraph's bounds check raised on them, so the
panel printed "SETTLING tab unavailable" — on exactly the run whose curve explains why there is no value
(SPEC_settled_measurement.md §12.1). The screen renderer now maps None to NaN and breaks the line there.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python -m pytest tests/test_settling_tab_on_a_broken_run.py -q
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTabWidget

from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin
from sciens.spectracs.view.spectral.workflow.render.QtWorkflowRenderer import QtWorkflowRenderer

APP = QApplication.instance() or QApplication([])

BROKEN = {
    "outcome": "MEASUREMENT_BROKEN", "clearingSeconds": None, "evaluatorId": "dev-clearing",
    "evaluatorVersion": "clearing-1.0", "distinctFraction": 0.67,
    "policy": {"windowFrames": 60, "evaluateEveryNFrames": 1, "maxSeconds": 1500.0},
    "answer": None, "notes": [],
    "rows": [{"t": index * 20.0, "qPercent": None, "valley": None, "soret": 0.001, "n": 60, "nAccepted": 40,
              "isDecisionRow": index % 30 == 0} for index in range(61)],
}


def test_a_broken_run_still_renders_its_settling_tabs():
    widget = QtWorkflowRenderer().render([DevSpectralPlugin().settlingView(BROKEN)])
    tabs = widget.findChildren(QTabWidget)
    assert tabs and tabs[0].count() > 0
