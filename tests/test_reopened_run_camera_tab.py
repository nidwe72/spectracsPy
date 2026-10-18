"""CS6.5 / Q10 (SPEC_camera_settings.md §4): a RE-OPENED run lays each acquisition step out as the live panel does —
Spectrum | Camera | Settling — and the camera record never empties the reference tab (E1).

Edwin, 2026-10-18: "the camera table should be always a sub-tab".

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python -m pytest tests/test_reopened_run_camera_tab.py -q
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTabWidget

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.persistence.database.spectral.PersistSpectralWorkflowLogicModule import \
    PersistSpectralWorkflowLogicModule
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.model.spectral.SpectralWorkflow import SpectralWorkflow
from sciens.spectracs.model.spectral.SpectralWorkflowPhase import SpectralWorkflowPhase
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.model.spectral.SpectralWorkflowStep import SpectralWorkflowStep
from sciens.spectracs.model.spectral.SpectraContainer import SpectraContainer
from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.model.spectral.camera.CameraLegSnapshot import CameraLegSnapshot
from sciens.spectracs.model.spectral.camera.CameraOpenRecord import CameraOpenRecord
from sciens.spectracs.model.spectral.plugin.view.CameraSettingsRecordView import CameraSettingsRecordView
from sciens.spectracs.model.spectral.plugin.view.EvaluationResult import EvaluationResult
from sciens.spectracs.plugin_sdk.roles import REFERENCE, SAMPLE
from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin
from sciens.spectracs.view.spectral.workflow.SpectrumPlotWidget import SpectrumPlotWidget
from sciens.spectracs.view.spectral.workflow.WizardViewModule import WizardViewModule

USER_ID = "test-user-reopened-camera-tab"
STATE = {"EXPOSURE": 90, "WHITE_BALANCE_KELVIN": 6500, "BACKLIGHT": 0}
SETTLING = {
    "outcome": "SETTLED_AFTER_CLEARING", "clearingSeconds": 600.0, "evaluatorId": "dev-clearing",
    "evaluatorVersion": "clearing-1.0", "distinctFraction": 0.8,
    "policy": {"windowFrames": 50, "evaluateEveryNFrames": 1, "maxSeconds": 1500.0},
    "answer": {"valueKey": "qPercent", "value": 13.0, "t": 500.0, "readAs": "VERTEX", "branch": "was-clearing"},
    "notes": [], "rows": [{"t": index * 60.0, "qPercent": 13.3 - 0.1 * index, "valley": 0.5, "soret": 0.9, "n": 50,
                           "nAccepted": 41, "isDecisionRow": True} for index in range(6)],
}


class _StubMainContainer:
    class _MainView:
        def setCurrentIndex(self, index):
            pass

    def __init__(self):
        self.mainViewModule = _StubMainContainer._MainView()

    def setWindowTitle(self, title):
        pass


def _step(role, label, showsTab, settled=False):
    step = SpectralWorkflowStep()
    step.setRole(role)
    step.setLabel(label)
    spectrum = Spectrum()
    spectrum.setValuesByNanometers({500.0: 10.0, 600.0: 20.0})
    container = SpectraContainer()
    container.addToSpectra(spectrum, role)
    step.setContainer(container)
    result = EvaluationResult()
    result.addItem(CameraSettingsRecordView(
        CameraOpenRecord(profile="MEASUREMENT", requested=dict(STATE), deviceDefaults={"BACKLIGHT": 1}),
        CameraLegSnapshot(role=role, atStart=dict(STATE), atEnd=dict(STATE), requestedExposure=90,
                          exposureSource="plugin"), showsTab=showsTab))
    if settled:
        view = DevSpectralPlugin().settlingView(SETTLING)
        view.isMonitorView = True
        result.addItem(view)
    step.setEvaluationResult(result)
    return step


class ReopenedRunCameraTabTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        CurrentUserSession().login({"ok": True, "userId": USER_ID, "username": "cameraTabUser",
                                    "roles": ["MASTER"], "pluginCodeRef": "dev.DevSpectralPlugin",
                                    "pluginId": "p", "spectrometerDevice": "Virtuax"})
        ApplicationContextLogicModule().getNavigationHandler().mainContainerViewModule = _StubMainContainer()
        cls.persist = PersistSpectralWorkflowLogicModule()

    def setUp(self):
        self.workflowId = None

    def tearDown(self):
        if self.workflowId is not None:
            self.persist.delete(self.workflowId, userId=USER_ID)

    def __reopen(self, showsTab):
        workflow = SpectralWorkflow()
        workflow.userId = USER_ID
        workflow.username = "cameraTabUser"
        workflow.pluginCodeRef = "dev.DevSpectralPlugin"
        acquisition = SpectralWorkflowPhase()
        acquisition.setType(SpectralWorkflowPhaseType.ACQUISITION)
        workflow.addToPhases(acquisition)
        acquisition.addToSteps(_step(REFERENCE, "Reference", showsTab))
        acquisition.addToSteps(_step(SAMPLE, "Sample", showsTab, settled=True))
        self.persist.save(workflow)
        self.workflowId = workflow.id
        wizard = WizardViewModule()
        self.wizard = wizard                      # kept alive: the step widgets are its children
        wizard.initialize()
        wizard.setViewWorkflow(self.workflowId)
        wizard.show()
        self.app.processEvents()
        tabs = wizard._tabWidget
        return {tabs.tabText(index): tabs.widget(index) for index in range(tabs.count())}

    @staticmethod
    def __labels(widget):
        return [widget.tabText(index) for index in range(widget.count())] if isinstance(widget, QTabWidget) else None

    def test_the_bench_run_reopens_with_its_camera_sub_tab(self):
        steps = self.__reopen(showsTab=True)
        self.assertEqual(["Spectrum", "Camera"], self.__labels(steps["Reference"]))
        self.assertEqual(["Spectrum", "Camera", "Settling"], self.__labels(steps["Sample"]))
        # ⛔ E1: the reference keeps its plot — the record did not empty the tab
        self.assertIsInstance(steps["Reference"].widget(0), SpectrumPlotWidget)

    def test_another_plugins_run_reopens_as_before(self):
        steps = self.__reopen(showsTab=False)
        self.assertIsInstance(steps["Reference"], SpectrumPlotWidget)     # the bare plot, exactly as before
        self.assertEqual(["Spectrum", "Settling"], self.__labels(steps["Sample"]))


if __name__ == "__main__":
    unittest.main()
