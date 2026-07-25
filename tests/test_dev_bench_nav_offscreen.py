# M2 (B3) offscreen nav test for the DEV measurement bench. The bench is camera-coupled, so the CapturePanel is
# mocked and a stub plugin is injected via _resolvePlugin — this exercises the bench's OWN navigation + per-stop
# rendering wiring on the base (chevron from the plan, Next through the phases, Back, terminal), without a real
# camera or the heavy DEV pipeline. Live capture / raster / report stay rig-verified (the bench needs a camera).

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton, QWidget

import sciens.spectracs.view.settings.development.DevMeasurementBenchViewModule as benchmod
from sciens.spectracs.view.settings.development.DevMeasurementBenchViewModule import DevMeasurementBenchViewModule
from sciens.spectracs.plugin_sdk.base.SpectralPlugin import SpectralPlugin
from sciens.spectracs.model.spectral.SpectraContainer import SpectraContainer
from sciens.spectracs.model.spectral.SpectralWorkflowStep import SpectralWorkflowStep
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType as P
from sciens.spectracs.plugin_sdk.roles import REFERENCE, SAMPLE


class _StubCapturePanel(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.__button = QPushButton("Capture")
    def startStream(self): pass
    def stopStream(self): pass
    def plotActiveRole(self): pass
    def restoreRoi(self): pass
    def isCameraReady(self): return False   # short-circuit the guidance highlight (rig-verified separately)
    def getCaptureButton(self): return self.__button
    def getRepresentativeFrame(self, role): return None
    def setActiveStep(self, step): self.activeStep = step


def _addStep(phase, label, role=None):
    step = SpectralWorkflowStep()
    step.setLabel(label)
    if role is not None:
        step.setRole(role)
    phase.addToSteps(step)


class _StubPlugin(SpectralPlugin):
    title = "Bench stub"

    def acquisition(self, workflow):
        phase = workflow.getPhase(P.ACQUISITION)
        _addStep(phase, "Reference", REFERENCE)
        _addStep(phase, "Sample", SAMPLE)

    def processing(self, workflow):
        _addStep(workflow.getPhase(P.PROCESSING), "Spectra")

    def evaluation(self, workflow):
        _addStep(workflow.getPhase(P.EVALUATION), "Metrics")

    def publishing(self, workflow):
        _addStep(workflow.getPhase(P.PUBLISHING), "Send to LIMS")


class _TestBench(DevMeasurementBenchViewModule):
    def _resolvePlugin(self):
        return _StubPlugin()

    def _pluginProvenance(self):
        return "stub.codeRef", None

    def _onFinish(self):   # skip real persistence/leave in the offscreen nav test
        self.finished = True


class DevBenchNavOffscreenTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self._origPanel = benchmod.CapturePanel
        benchmod.CapturePanel = _StubCapturePanel

    def tearDown(self):
        benchmod.CapturePanel = self._origPanel

    def _bench(self):
        bench = _TestBench()
        bench.finished = False
        bench.initialize()
        bench._startNewRun()   # bypass __enterRun's calibration/camera gate (mocked away)
        return bench

    def _fillCaptures(self, bench):
        for step in bench._workflow().getPhase(P.ACQUISITION).getSteps().values():
            step.setContainer(SpectraContainer())

    def test_chevron_and_step_through_to_publishing_then_finish(self):
        bench = self._bench()
        chevron = [bench._plan[i].label for i in range(len(bench._plan))]
        self.assertEqual(chevron, ["Acquisition", "Processing", "Evaluation", "Verdict/Publish"])
        self.assertEqual(bench._plan[bench._cursor].phaseType, P.ACQUISITION)
        # Next is gated until both roles are captured
        self.assertFalse(bench._nextButton.isEnabled())
        self._fillCaptures(bench)
        bench._refreshNav()
        self.assertTrue(bench._nextButton.isEnabled())
        bench.onClickedNext()   # -> Processing (stub hook populates on arrival)
        self.assertEqual(bench._plan[bench._cursor].phaseType, P.PROCESSING)
        bench.onClickedNext()   # -> Evaluation
        self.assertEqual(bench._plan[bench._cursor].phaseType, P.EVALUATION)
        bench.onClickedNext()   # -> Publishing (terminal)
        self.assertEqual(bench._plan[bench._cursor].phaseType, P.PUBLISHING)
        self.assertEqual(bench._nextButton.text(), "Save")
        bench.onClickedNext()   # Save -> finish
        self.assertTrue(bench.finished)

    def test_back_from_processing_returns_to_acquisition(self):
        bench = self._bench()
        self._fillCaptures(bench)
        bench._refreshNav()
        bench.onClickedNext()   # Processing
        self.assertEqual(bench._plan[bench._cursor].phaseType, P.PROCESSING)
        bench.onClickedBack()   # back to Acquisition
        self.assertEqual(bench._plan[bench._cursor].phaseType, P.ACQUISITION)

    def test_should_be_flow_step_chevrons_auto_advance_to_metadata(self):
        from sciens.spectracs.plugin_sdk.policy.NavigationMode import NavigationMode
        from sciens.spectracs.plugin_sdk.policy.NavigationPolicy import NavigationPolicy
        from sciens.spectracs.plugin_sdk.policy.WorkflowPolicy import WorkflowPolicy

        fields = [type("F", (), {"name": "title", "label": "Title", "type": "TEXT",
                                 "order": 0, "showInWorkflowsTable": True})()]

        class _ShouldBe(_StubPlugin):
            def policy(self):
                return WorkflowPolicy(NavigationPolicy(NavigationMode.AUTO_ADVANCE,
                                                       stepChevronPhases={P.ACQUISITION}))
            def metadata(self, workflow):
                return fields

        bench = _TestBench()
        bench.finished = False
        bench._resolvePlugin = lambda: _ShouldBe()
        bench.initialize()
        bench._startNewRun()
        chevron = [bench._plan[i].label for i in range(len(bench._plan))]
        self.assertEqual(chevron, ["Reference", "Sample", "Processing", "Evaluation", "Details", "Verdict/Publish"])

        acq = list(bench._workflow().getPhase(P.ACQUISITION).getSteps().values())
        # Reference stop: advances once the REFERENCE is captured (not all)
        self.assertFalse(bench._nextButton.isEnabled())
        acq[0].setContainer(SpectraContainer())
        bench._refreshNav()
        self.assertTrue(bench._nextButton.isEnabled())
        bench.onClickedNext()   # -> Sample
        self.assertEqual(bench._plan[bench._cursor].phaseType, P.ACQUISITION)
        self.assertEqual(bench._plan[bench._cursor].label, "Sample")
        # Sample stop is the boundary: gated on ALL captured
        self.assertFalse(bench._nextButton.isEnabled())
        acq[1].setContainer(SpectraContainer())
        bench._refreshNav()
        self.assertTrue(bench._nextButton.isEnabled())
        bench.onClickedNext()   # boundary -> JUMP to Metadata (index 4)
        self.assertEqual(bench._plan[bench._cursor].phaseType, P.METADATA)
        # the jumped-over computed phases are populated + Back-reachable
        self.assertGreater(len(bench._workflow().getPhase(P.PROCESSING).getSteps()), 0)
        bench.onClickedNext()   # Metadata -> Publishing (terminal)
        self.assertEqual(bench._plan[bench._cursor].phaseType, P.PUBLISHING)

    def test_option_c_revisit_steps_but_recapture_rejumps(self):
        # Option C (§4.4a, J): the first pass jumps (fresh capture); a revisit WITHOUT re-capturing disarms the
        # jump and steps into Processing; a re-capture re-arms it so the next Next jumps again.
        from sciens.spectracs.plugin_sdk.policy.NavigationMode import NavigationMode
        from sciens.spectracs.plugin_sdk.policy.NavigationPolicy import NavigationPolicy
        from sciens.spectracs.plugin_sdk.policy.WorkflowPolicy import WorkflowPolicy

        fields = [type("F", (), {"name": "title", "label": "Title", "type": "TEXT",
                                 "order": 0, "showInWorkflowsTable": True})()]

        class _ShouldBe(_StubPlugin):
            def policy(self):
                return WorkflowPolicy(NavigationPolicy(NavigationMode.AUTO_ADVANCE,
                                                       stepChevronPhases={P.ACQUISITION}))
            def metadata(self, workflow):
                return fields

        bench = _TestBench()
        bench.finished = False
        bench._resolvePlugin = lambda: _ShouldBe()
        bench.initialize()
        bench._startNewRun()
        for step in bench._workflow().getPhase(P.ACQUISITION).getSteps().values():
            step.setContainer(SpectraContainer())
        bench._refreshNav()

        def backToSampleBoundary():
            while not (bench._plan[bench._cursor].phaseType == P.ACQUISITION
                       and bench._plan[bench._cursor].label == "Sample"):
                bench.onClickedBack()

        bench.onClickedNext()   # Reference -> Sample
        self.assertTrue(bench._canJump())
        bench.onClickedNext()   # Sample boundary, FRESH -> JUMP to Metadata
        self.assertEqual(bench._plan[bench._cursor].phaseType, P.METADATA)

        backToSampleBoundary()
        self.assertFalse(bench._canJump())   # PROCESSING already computed -> jump disarmed
        bench.onClickedNext()   # revisit, no re-capture -> STEP into Processing (no jump)
        self.assertEqual(bench._plan[bench._cursor].phaseType, P.PROCESSING)

        backToSampleBoundary()
        bench._onCapture()      # a fresh burst re-invalidates the computed phases + re-arms the jump
        self.assertTrue(bench._canJump())
        bench.onClickedNext()   # fresh again -> JUMP to Metadata
        self.assertEqual(bench._plan[bench._cursor].phaseType, P.METADATA)

    def test_no_publishing_when_plugin_declares_none(self):
        class _NoPub(_StubPlugin):
            def publishing(self, workflow):
                pass
        bench = _TestBench()
        bench.finished = False
        bench._resolvePlugin = lambda: _NoPub()
        bench.initialize()
        bench._startNewRun()
        chevron = [bench._plan[i].label for i in range(len(bench._plan))]
        self.assertEqual(chevron, ["Acquisition", "Processing", "Evaluation"])


if __name__ == "__main__":
    unittest.main()
