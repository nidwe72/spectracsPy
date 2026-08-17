"""A re-opened run navigates the way it was MEASURED — D4/G3 (SPEC_settled_measurement.md §27.14a).

⛔⛔ THE BUG THIS CLOSES. `NavigationPolicy` was built by `plugin.policy()` and lived only in the live host:
it was persisted nowhere, and `_policy()` handed back `WorkflowPolicy.default()` for any VIEW-mode run. ⇒ a
saved measurement showed ONE "Acquisition" chevron where the run itself had shown `Reference › Sample`. The
structure the plugin declared never reached the record.

⭐ Now the workflow carries it (`sectionedPhases`), and the chevron reads it from there — the same source
the PDF's section headings and a plugin-free LIMS addon read.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python -m pytest tests/test_reopened_run_keeps_its_chevron.py -q
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.persistence.database.spectral.PersistSpectralWorkflowLogicModule import PersistSpectralWorkflowLogicModule
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.model.spectral.SpectralWorkflow import SpectralWorkflow
from sciens.spectracs.model.spectral.SpectralWorkflowPhase import SpectralWorkflowPhase
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.model.spectral.SpectralWorkflowStep import SpectralWorkflowStep
from sciens.spectracs.model.spectral.plugin.view.EvaluationResult import EvaluationResult
from sciens.spectracs.model.spectral.plugin.view.LabelView import LabelView
from sciens.spectracs.plugin_sdk.roles import REFERENCE, SAMPLE
from sciens.spectracs.view.spectral.workflow.WizardViewModule import WizardViewModule

ACQUISITION = SpectralWorkflowPhaseType.ACQUISITION
PLUGIN_CODE_REF = "sciens.spectracs.plugins.pumpkin.PumpkinOilPlugin.PumpkinOilPlugin"
USER_ID = "test-user-reopened-chevron"


class _StubMainContainer:
    class _MainView:
        def setCurrentIndex(self, index):
            pass

    def __init__(self):
        self.mainViewModule = _StubMainContainer._MainView()

    def setWindowTitle(self, title):
        pass


class ReopenedRunKeepsItsChevronTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        CurrentUserSession().login({"ok": True, "userId": USER_ID, "username": "chevronTestUser",
                                    "roles": ["END_USER"], "pluginCodeRef": PLUGIN_CODE_REF,
                                    "pluginId": "p", "spectrometerDevice": "Virtuax"})
        ApplicationContextLogicModule().getNavigationHandler().mainContainerViewModule = _StubMainContainer()
        cls.persist = PersistSpectralWorkflowLogicModule()

    def setUp(self):
        self.workflowId = None

    def tearDown(self):
        if self.workflowId is not None:
            self.persist.delete(self.workflowId, userId=USER_ID)

    def __savedRun(self, sectionedPhases):
        workflow = SpectralWorkflow()
        workflow.userId = USER_ID
        workflow.username = "chevronTestUser"
        workflow.pluginCodeRef = PLUGIN_CODE_REF
        phase = SpectralWorkflowPhase()
        phase.setType(ACQUISITION)
        workflow.addToPhases(phase)
        for role, label in ((REFERENCE, "Reference"), (SAMPLE, "Sample")):
            step = SpectralWorkflowStep()
            step.setRole(role)
            step.setLabel(label)
            result = EvaluationResult()
            result.addItem(LabelView("measured"))     # any renderable content -> the step earns a tab
            step.setEvaluationResult(result)
            phase.addToSteps(step)
        workflow.setSectionedPhases(sectionedPhases)
        self.persist.save(workflow)
        self.workflowId = workflow.id
        return workflow.id

    def __chevronOfReopened(self, workflowId):
        wizard = WizardViewModule()
        wizard.initialize()
        wizard.setViewWorkflow(workflowId)
        wizard.show()
        self.app.processEvents()
        return [stop.label for stop in wizard._plan]

    def test_a_sectioned_acquisition_still_reads_reference_then_sample(self):
        labels = self.__chevronOfReopened(self.__savedRun({ACQUISITION}))
        self.assertEqual(["Reference", "Sample"], labels[:2],
                         "the re-opened run lost the step chevrons it was measured with")

    def test_without_the_declaration_it_is_one_acquisition_chevron(self):
        # ⭐ Every run saved before D4 reads exactly this way — the pre-D4 behaviour, kept for them.
        labels = self.__chevronOfReopened(self.__savedRun(frozenset()))
        self.assertEqual("Acquisition", labels[0])
        self.assertNotIn("Reference", labels)


if __name__ == "__main__":
    unittest.main()
