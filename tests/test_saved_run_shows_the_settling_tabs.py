"""A RE-OPENED run still shows its settling tabs — SPEC_settled_measurement.md §27.13d (D3).

⭐⭐ THE GUARANTEE, AND WHY IT NEEDED PINNING. The settling views are invisible during a live capture and
visible in a saved one, and BOTH halves come from the same mechanism: `SpectralWorkflowStep._view` is
`@reconstructor`-transient, so a step loaded from the DB carries no `CaptureView` — `renderStep()` then
falls past the capture branch into the passive visitor, which reads the `EvaluationResult`.

⛔ THAT WAS AN ACCIDENT UNTIL THIS TEST. Nothing asserted it and nothing explained it, so "persist the view
descriptor" — a plausible future change — would have silently removed the settling tabs from every
re-opened measurement, with no test going red.

⚠ IT DRIVES THE RENDERER, NOT A HOST (§27.18/Z5): the guarantee lives in `renderStep`, and D4/G3 will
change how the wizard lays a re-opened acquisition out. A test written against the wizard would need
rewriting three phases later for a behaviour it was never about.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python -m pytest tests/test_saved_run_shows_the_settling_tabs.py -q
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTabWidget

from sciens.spectracs.logic.persistence.database.spectral.PersistSpectralWorkflowLogicModule import PersistSpectralWorkflowLogicModule
from sciens.spectracs.model.spectral.SpectralWorkflow import SpectralWorkflow
from sciens.spectracs.model.spectral.SpectralWorkflowPhase import SpectralWorkflowPhase
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.model.spectral.SpectralWorkflowStep import SpectralWorkflowStep
from sciens.spectracs.model.spectral.plugin.view.CaptureView import CaptureView
from sciens.spectracs.model.spectral.plugin.view.EvaluationResult import EvaluationResult
from sciens.spectracs.model.spectral.plugin.view.TabGroupView import TabGroupView
from sciens.spectracs.plugin_sdk.roles import SAMPLE
from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin
from sciens.spectracs.view.spectral.workflow.render.WorkflowPhaseRenderer import WorkflowPhaseRenderer

USER_ID = "test-user-settling-reload"

RECORD = {
    "outcome": "SETTLED_AFTER_CLEARING", "clearingSeconds": 1195.9,
    "evaluatorId": "dev-clearing", "evaluatorVersion": "clearing-1.0", "distinctFraction": 0.82,
    "policy": {"windowFrames": 50, "evaluateEveryNFrames": 1, "maxSeconds": 1500.0},
    "answer": {"valueKey": "qPercent", "value": 13.27, "t": 999.3,
               "readAs": "VERTEX", "branch": "was-clearing"},
    "notes": [],
    "rows": [{"t": index * 60.0, "qPercent": 13.3 - 0.1 * index, "valley": 0.9 / (index + 1),
              "soret": 0.9, "n": 50, "nAccepted": 41, "isDecisionRow": True} for index in range(12)],
}


class SavedRunShowsTheSettlingTabsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.persist = PersistSpectralWorkflowLogicModule()
        self.workflowId = None

    def tearDown(self):
        if self.workflowId is not None:
            self.persist.delete(self.workflowId, userId=USER_ID)

    @staticmethod
    def __workflowWithASettledSample():
        workflow = SpectralWorkflow()
        workflow.userId = USER_ID
        workflow.username = "settlingReloadUser"
        workflow.pluginCodeRef = "dev.DevSpectralPlugin"
        acquisition = SpectralWorkflowPhase()
        acquisition.setType(SpectralWorkflowPhaseType.ACQUISITION)
        workflow.addToPhases(acquisition)
        step = SpectralWorkflowStep()
        step.setRole(SAMPLE)
        step.setLabel("Sample")
        step.setView(CaptureView(prompt="Insert the sample", captureLabel="Capture sample"))
        result = EvaluationResult()
        view = DevSpectralPlugin().settlingView(RECORD)
        view.isMonitorView = True                       # what __attachMonitorViews does (§27.12)
        result.addItem(view)
        step.setEvaluationResult(result)
        acquisition.addToSteps(step)
        return workflow, step

    @staticmethod
    def __sampleStep(workflow):
        steps = workflow.getPhase(SpectralWorkflowPhaseType.ACQUISITION).getSteps().values()
        return next(step for step in steps if step.getRole() == SAMPLE)

    @staticmethod
    def __tabLabels(widget):
        tabs = widget.findChildren(QTabWidget)
        return [tabs[0].tabText(index) for index in range(tabs[0].count())] if tabs else []

    def test_live_the_step_renders_as_the_capture_panel(self):
        # The other half of the asymmetry: while `_view` holds a CaptureView the EvaluationResult is never
        # read, which is what keeps the settling views out of the UI during a run — by construction.
        _workflow, step = self.__workflowWithASettledSample()
        renderer = WorkflowPhaseRenderer(captureHandler=lambda s, v: "CAPTURE-PANEL")
        self.assertEqual("CAPTURE-PANEL", renderer.renderStep(step))

    def test_reloaded_the_same_step_renders_the_settling_tabs(self):
        workflow, _step = self.__workflowWithASettledSample()
        self.persist.save(workflow)
        self.workflowId = workflow.id

        loaded = self.persist.findById(self.workflowId)
        step = self.__sampleStep(loaded)

        # ⭐ THE MECHANISM: no CaptureView survives the reload, so renderStep takes the passive path.
        self.assertIsNone(step.getView(), "the step's _view is meant to be transient — see renderStep()")

        widget = WorkflowPhaseRenderer().renderStep(step)
        self.assertIsNotNone(widget, "a re-opened settled run rendered NOTHING for its Sample step")
        self.assertEqual(["Overview", "Q%", "Turbidity", "Rate", "Health", "Decisions"],
                         self.__tabLabels(widget))

    def test_the_monitor_tag_survives_the_real_database(self):
        # D2 end to end (§27.13c): the tag is what makes a re-measure REPLACE rather than accumulate, and
        # before this it was a bare attribute that no column carried.
        workflow, _step = self.__workflowWithASettledSample()
        self.persist.save(workflow)
        self.workflowId = workflow.id

        step = self.__sampleStep(self.persist.findById(self.workflowId))
        groups = [item for item in step.getEvaluationResult().getItems() if isinstance(item, TabGroupView)]
        self.assertEqual(1, len(groups))
        self.assertTrue(groups[0].isMonitorView)


if __name__ == "__main__":
    unittest.main()
