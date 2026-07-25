# M2 (B1) offscreen test for AbstractPluginExecutionView — the shared navigation host. Drives a stub plugin
# (computed steps added unconditionally, no camera) through the chevron with a stub subclass, verifying the
# STEP flow, the AUTO_ADVANCE jump, per-step chevrons, Back, and terminal/finish.

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel

from sciens.spectracs.plugin_sdk.base.SpectralPlugin import SpectralPlugin
from sciens.spectracs.plugin_sdk.policy.NavigationMode import NavigationMode
from sciens.spectracs.plugin_sdk.policy.NavigationPolicy import NavigationPolicy
from sciens.spectracs.plugin_sdk.policy.WorkflowPolicy import WorkflowPolicy
from sciens.spectracs.model.spectral.SpectralWorkflowStep import SpectralWorkflowStep
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType as P
from sciens.spectracs.plugin_sdk.roles import REFERENCE, SAMPLE
from sciens.spectracs.view.spectral.workflow.AbstractPluginExecutionView import AbstractPluginExecutionView


def _addStep(phase, label, role=None):
    step = SpectralWorkflowStep()
    step.setLabel(label)
    if role is not None:
        step.setRole(role)
    phase.addToSteps(step)


class _StubPlugin(SpectralPlugin):
    # Computed hooks add steps UNCONDITIONALLY (no capture needed) so the nav machinery can be exercised
    # offscreen. `policy` / `metadata` / `publishing` are parameterised per test.
    title = "Stub"

    def __init__(self, policy=None, metadataFields=(), publishing=False):
        self._policy = policy if policy is not None else WorkflowPolicy.default()
        self._metadataFields = list(metadataFields)
        self._publishing = publishing

    def policy(self):
        return self._policy

    def acquisition(self, workflow):
        phase = workflow.getPhase(P.ACQUISITION)
        _addStep(phase, "Reference", REFERENCE)
        _addStep(phase, "Sample", SAMPLE)

    def processing(self, workflow):
        _addStep(workflow.getPhase(P.PROCESSING), "Spectra")

    def evaluation(self, workflow):
        _addStep(workflow.getPhase(P.EVALUATION), "Result")

    def metadata(self, workflow):
        return list(self._metadataFields)

    def publishing(self, workflow):
        if self._publishing:
            _addStep(workflow.getPhase(P.PUBLISHING), "Send to LIMS")


class _StubView(AbstractPluginExecutionView):
    def __init__(self, plugin):
        super().__init__()
        self._stubPlugin = plugin
        self.finished = False
        self.afterNavCount = 0

    def _afterNav(self):
        # stand-in for the hosts' guidance refresh — must fire on every nav refresh (incl. after a capture)
        self.afterNavCount += 1

    def _getPageTitle(self):
        return "Stub"

    def _resolvePlugin(self):
        return self._stubPlugin

    def _renderStop(self, navStop, container):
        container.addTab(QLabel(navStop.label), navStop.label)

    def _leave(self):
        pass

    def _onFinish(self):   # skip real persistence in the stub; the wizard tests cover saving
        self.finished = True


class PluginExecutionViewOffscreenTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _view(self, plugin):
        view = _StubView(plugin)
        view.initialize()
        view._startNewRun()
        return view

    def _chevron(self, view):
        return [view._plan[i].label for i in range(len(view._plan))]

    def test_default_step_flow_acq_proc_eval_then_save(self):
        view = self._view(_StubPlugin())
        self.assertEqual(self._chevron(view), ["Acquisition", "Processing", "Evaluation"])
        self.assertEqual(view._cursor, 0)
        self.assertEqual(view._nextButton.text(), "Next")
        view.onClickedNext()                                  # -> Processing (populated on arrival)
        self.assertEqual(view._cursor, 1)
        view.onClickedNext()                                  # -> Evaluation
        self.assertEqual(view._cursor, 2)
        self.assertEqual(view._nextButton.text(), "Save")     # terminal
        view.onClickedNext()                                  # Save -> finish
        self.assertTrue(view.finished)

    def test_publishing_appears_when_declared(self):
        view = self._view(_StubPlugin(publishing=True))
        self.assertEqual(self._chevron(view), ["Acquisition", "Processing", "Evaluation", "Verdict/Publish"])

    def test_metadata_chevron_when_fields_present(self):
        fields = [type("F", (), {"name": "title", "label": "Title", "type": "TEXT", "order": 0})()]
        view = self._view(_StubPlugin(metadataFields=fields))
        self.assertIn("Details", self._chevron(view))

    def test_auto_advance_with_step_chevrons_jumps_to_metadata(self):
        fields = [type("F", (), {"name": "title", "label": "Title", "type": "TEXT", "order": 0})()]
        policy = WorkflowPolicy(NavigationPolicy(NavigationMode.AUTO_ADVANCE, stepChevronPhases={P.ACQUISITION}))
        view = self._view(_StubPlugin(policy=policy, metadataFields=fields, publishing=True))
        self.assertEqual(self._chevron(view),
                         ["Reference", "Sample", "Processing", "Evaluation", "Details", "Verdict/Publish"])
        self.assertEqual(view._cursor, 0)                     # Reference
        view.onClickedNext()                                  # plain step -> Sample
        self.assertEqual(view._cursor, 1)
        view.onClickedNext()                                  # boundary -> JUMP to Metadata (index 4)
        self.assertEqual(view._cursor, 4)
        # the jumped-over computed phases are populated + Back-reachable
        self.assertGreater(len(view._workflow().getPhase(P.PROCESSING).getSteps()), 0)
        self.assertGreater(len(view._workflow().getPhase(P.EVALUATION).getSteps()), 0)
        view.onClickedBack()                                  # -> Evaluation
        self.assertEqual(view._cursor, 3)
        self.assertEqual(view._plan[view._cursor].phaseType, P.EVALUATION)

    def test_metadata_field_objectnames_are_set(self):
        # E1 (SPEC_director_cut.md): the metadata form fields carry stable objectNames so the doc-mode Director
        # can focus + type into them (title / temperature).
        from PySide6.QtWidgets import QLineEdit
        fields = [type("F", (), {"name": "title", "label": "Title", "type": "TEXT", "order": 0})(),
                  type("F", (), {"name": "temperature", "label": "Temp", "type": "NUMBER", "order": 1})()]
        policy = WorkflowPolicy(NavigationPolicy(NavigationMode.AUTO_ADVANCE, stepChevronPhases={P.ACQUISITION}))
        view = self._view(_StubPlugin(policy=policy, metadataFields=fields, publishing=True))
        view.onClickedNext(); view.onClickedNext()            # jump to Details (the METADATA form renders)
        self.assertEqual(view._plan[view._cursor].phaseType, P.METADATA)
        self.assertIsNotNone(view._tabWidget.findChild(QLineEdit, "PluginExecutionView.metadata.title"))
        self.assertIsNotNone(view._tabWidget.findChild(QLineEdit, "PluginExecutionView.metadata.temperature"))

    def test_refresh_nav_fires_guidance_hook_on_capture(self):
        # Regression: guidance must refresh on _refreshNav (which onCaptured calls), not only on a full render —
        # else the amber cue + coach line go stale after a capture.
        view = self._view(_StubPlugin())
        before = view.afterNavCount
        view._refreshNav()   # what a capture callback triggers
        self.assertEqual(view.afterNavCount, before + 1)

    def test_auto_advance_next_from_metadata_walks_to_publishing_then_saves(self):
        fields = [type("F", (), {"name": "title", "label": "Title", "type": "TEXT", "order": 0})()]
        policy = WorkflowPolicy(NavigationPolicy(NavigationMode.AUTO_ADVANCE, stepChevronPhases={P.ACQUISITION}))
        view = self._view(_StubPlugin(policy=policy, metadataFields=fields, publishing=True))
        view.onClickedNext(); view.onClickedNext()            # jump to Metadata (4)
        self.assertEqual(view._cursor, 4)
        view.onClickedNext()                                  # Metadata -> Publishing (5, terminal)
        self.assertEqual(view._cursor, 5)
        self.assertEqual(view._nextButton.text(), "Save")
        view.onClickedNext()
        self.assertTrue(view.finished)


if __name__ == "__main__":
    unittest.main()
