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
        self.assertEqual(chevron, ["Acquisition", "Processing", "Evaluation", "Publishing"])
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
