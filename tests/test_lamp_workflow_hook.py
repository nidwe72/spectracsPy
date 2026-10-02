"""
P5 of SPEC_lamp_switch.md — the plugin decides on / off on every phase entry (D5), through the shared host
(AbstractPluginExecutionView), against a FakeShellyServer. Reuses the offscreen stub host of
test_plugin_execution_view_offscreen.

Covers: on in ACQUISITION / off on PROCESSING / on again via Back; dedupe by phase (Reference → Sample sends
nothing); the lamp is off BEFORE the PROCESSING hook computes (G7); a plugin without a LampPolicy and a saved
run (VIEW) never switch; release on hide only by the owner (D14/G7); the coach-line rule (§16.2) and the gate.

    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests/test_lamp_workflow_hook.py -q
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from fakes.FakeShellyServer import FakeClock, FakeShellyServer
from test_plugin_execution_view_offscreen import _StubPlugin, _StubView
from sciens.spectracs.logic.lamp.LampDiscovery import LampDiscovery
from sciens.spectracs.logic.lamp.LampPlugStore import LampPlugStore
from sciens.spectracs.logic.lamp.LampService import LampService
from sciens.spectracs.logic.lamp.LampState import LampState
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType as P
from sciens.spectracs.plugin_sdk import LampPolicy, NavigationMode, NavigationPolicy, WorkflowPolicy
from sciens.spectracs.view.spectral.workflow.AcquisitionGuidance import AcquisitionGuidance

SWITCHED = WorkflowPolicy(lamp=LampPolicy.duringAcquisition(maxMeasurementSeconds=1500))
SWITCHED_STEPS = WorkflowPolicy(navigation=NavigationPolicy(NavigationMode.STEP, stepChevronPhases={P.ACQUISITION}),
                                lamp=LampPolicy.duringAcquisition(maxMeasurementSeconds=1500))


class _RecordingPlugin(_StubPlugin):
    """Records the plug's output at the moment the PROCESSING hook computes."""

    def __init__(self, plug, policy):
        super().__init__(policy=policy)
        self.plug = plug
        self.outputDuringProcessing = None

    def processing(self, workflow):
        self.outputDuringProcessing = self.plug.output
        super().processing(workflow)


class LampWorkflowHookTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.clock = FakeClock()
        self.plug = FakeShellyServer(clock=self.clock).__enter__()
        LampService.instance = None
        discovery = LampDiscovery(mdnsBrowse=lambda types, seconds: [self.plug.host], subnetHosts=lambda: [],
                                  probeTimeout=0.5)
        self.service = LampService(clock=self.clock, threaded=False, discovery=discovery,
                                   plugStore=LampPlugStore(), wifiScan=lambda: [])
        self.service.configure(True)
        self.assertEqual(LampState.OFF, self.service.state)

    def tearDown(self):
        self.service.shutdown()
        LampService.instance = None
        self.plug.__exit__(None, None, None)

    def view(self, plugin):
        view = _StubView(plugin)
        view.initialize()
        view._startNewRun()
        return view

    def sets(self):
        return self.plug.callsTo("Switch.Set")

    def test_on_in_acquisition_off_in_processing_on_again_via_back(self):
        view = self.view(_StubPlugin(policy=SWITCHED))
        self.assertTrue(self.plug.output)
        self.assertEqual(LampState.WARMING, self.service.state)
        view.onClickedNext()
        self.assertFalse(self.plug.output)
        view.onClickedBack()
        self.assertTrue(self.plug.output)

    def test_reference_to_sample_is_one_phase(self):
        view = self.view(_StubPlugin(policy=SWITCHED_STEPS))
        self.assertEqual(["Reference", "Sample"], [view._plan[i].label for i in (0, 1)])
        view._canAdvanceFrom = lambda stop: True
        view.onClickedNext()                                   # Reference -> Sample
        self.assertEqual(1, len(self.sets()))

    def test_lamp_is_off_before_processing_computes(self):
        plugin = _RecordingPlugin(self.plug, SWITCHED)
        view = self.view(plugin)
        view.onClickedNext()
        self.assertIs(False, plugin.outputDuringProcessing)

    def test_unswitched_plugin_never_touches_the_lamp(self):
        view = self.view(_StubPlugin())
        view.onClickedNext()
        view.onClickedBack()
        self.assertEqual([], self.sets())

    def test_saved_run_never_switches(self):
        view = self.view(_StubPlugin(policy=SWITCHED))
        view.onClickedNext()
        view.onClickedNext()
        workflow = view._engine.getWorkflow()
        before = len(self.sets())
        viewer = _StubView(_StubPlugin(policy=SWITCHED))
        viewer.initialize()
        viewer._startViewRun(workflow)
        viewer.onClickedBack()
        viewer.onClickedBack()
        self.assertEqual(before, len(self.sets()))

    def test_release_on_hide_only_by_the_owner(self):
        bench = self.view(_StubPlugin(policy=SWITCHED))
        wizard = _StubView(_StubPlugin())
        wizard.initialize()
        wizard._releaseLamp()                                  # not the owner
        self.assertTrue(self.plug.output)
        bench._releaseLamp()
        self.assertFalse(self.plug.output)

    def test_coach_line_and_gate(self):
        view = self.view(_StubPlugin(policy=SWITCHED))
        self.assertFalse(AcquisitionGuidance.lampReady())          # warming
        self.clock.advance(20)
        self.service.tick()
        self.assertTrue(AcquisitionGuidance.lampReady())
        self.assertEqual("Press Capture", AcquisitionGuidance.lampCoach("Press Capture"))
        self.service.toggleManual()                                # off by hand in ACQUISITION
        self.assertFalse(AcquisitionGuidance.lampReady())
        self.assertIn("lamp icon", AcquisitionGuidance.lampCoach("Press Capture"))
        self.service.toggleManual()
        self.clock.advance(1800)
        self.service.tick()                                        # the cap
        self.assertIn("after 30 min", AcquisitionGuidance.lampCoach("Press Capture"))
        view.onClickedNext()                                       # PROCESSING: no lamp line, no gate
        self.assertEqual("x", AcquisitionGuidance.lampCoach("x"))
        self.assertTrue(AcquisitionGuidance.lampReady())

    def test_no_plug_appends_a_note(self):
        self.service._LampService__markOff(LampState.NO_PLUG)
        self.service.switch = None
        self.view(_StubPlugin(policy=SWITCHED))
        self.assertTrue(AcquisitionGuidance.lampReady())
        self.assertEqual("Press Capture  ·  switch the lamp on at the socket, 20 s warm-up",
                         AcquisitionGuidance.lampCoach("Press Capture"))


if __name__ == "__main__":
    unittest.main()
