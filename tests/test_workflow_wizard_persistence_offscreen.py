"""
P5/P7 offscreen — drives the real WizardViewModule through the whole persistence loop: NEW run (measure ->
fill metadata -> Save persists), VIEW mode (loads the saved run, metadata editable -> Save changes), then
delete. Complements the headless persist test with the actual widget + engine + navigation wiring.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python -m pytest tests/test_workflow_wizard_persistence_offscreen.py -q
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QMessageBox

from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.persistence.database.spectral.PersistSpectralWorkflowLogicModule import PersistSpectralWorkflowLogicModule
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.model.application.setting.virtualSpectrometer.VirtualCaptureRole import VirtualCaptureRole
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.view.spectral.workflow.WizardViewModule import WizardViewModule

PLUGIN_CODE_REF = "sciens.spectracs.logic.spectral.plugin.pumpkin.PumpkinOilPlugin.PumpkinOilPlugin"
USER_ID = "test-wizard-persistence"


class _StubMainContainer:
    class _MainView:
        def setCurrentIndex(self, index):
            pass
    def __init__(self):
        self.mainViewModule = _StubMainContainer._MainView()
    def setWindowTitle(self, title):
        pass


class WizardPersistenceOffscreenTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        folder = os.path.join(os.path.dirname(__file__), "..", "..", "spectracs-references",
                              "pumpkin_oil", "virtual_captures", "pumpkinoil_perfect_v1")
        settings = ApplicationContextLogicModule().getApplicationSettings().getVirtualSpectrometerSettings()
        for role, name in [(VirtualCaptureRole.CALIBRATION, "calibration.png"),
                           (VirtualCaptureRole.REFERENCE, "reference.png"),
                           (VirtualCaptureRole.SAMPLE, "sample.png")]:
            settings.setImage(role, QImage(os.path.join(folder, name)))
        ApplicationContextLogicModule().getApplicationSettings().setSpectrometerProfile(None)
        CurrentUserSession().login({"ok": True, "userId": USER_ID, "username": "pumpkinTestUser",
                                    "roles": ["END_USER"], "pluginCodeRef": PLUGIN_CODE_REF,
                                    "pluginId": "p", "spectrometerDevice": "Virtuax"})
        # make Home navigation a no-op (no real main container in the test)
        ApplicationContextLogicModule().getNavigationHandler().mainContainerViewModule = _StubMainContainer()
        cls.persist = PersistSpectralWorkflowLogicModule()

    def __wizard(self):
        wizard = WizardViewModule()
        wizard.initialize()
        return wizard

    def __private(self, wizard, name):
        return getattr(wizard, "_WizardViewModule__" + name)

    def test_new_run_saves_then_view_edits_then_delete(self):
        # 1) NEW run: measure both acquisition steps, advance to the terminal, fill metadata, Save
        wizard = self.__wizard()
        wizard.resetToNewMode()
        wizard.show()
        self.app.processEvents()
        engine = self.__private(wizard, "engine")
        for step in engine.getWorkflow().getPhase(SpectralWorkflowPhaseType.ACQUISITION).getSteps().values():
            engine.captureAcquisitionStep(step)
        for _ in range(10):  # advance through PROCESSING/EVALUATION to the terminal METADATA phase
            if self.__private(wizard, "nextButton").text() == "Save":
                break
            wizard.onClickedNext()
            self.app.processEvents()
        self.assertEqual(self.__private(wizard, "nextButton").text(), "Save")
        # the terminal phase is METADATA (its own phase, not an EVALUATION tab)
        self.assertEqual(self.__private(wizard, "shownPhases")[self.__private(wizard, "cursor")],
                         SpectralWorkflowPhaseType.METADATA)
        self.__private(wizard, "metadataWidgets")["title"][0].setText("Batch Alpha")
        wizard.onClickedNext()  # Save -> persists + Home

        runs = [w for w in self.persist.listForUser(USER_ID)]
        saved = next((w for w in runs if self.__title(w) == "Batch Alpha"), None)
        self.assertIsNotNone(saved, "the run was not persisted with its metadata")
        workflowId = saved.id

        # 2) VIEW mode: open the saved run; it renders read-only tabs; the metadata form rides the terminal
        viewWizard = self.__wizard()
        viewWizard.setViewWorkflow(workflowId)
        viewWizard.show()
        self.app.processEvents()
        self.assertGreater(self.__private(viewWizard, "tabWidget").count(), 0)
        shownPhases = self.__private(viewWizard, "shownPhases")
        while self.__private(viewWizard, "cursor") < len(shownPhases) - 1:  # advance to the terminal phase
            viewWizard.onClickedNext()
        self.app.processEvents()
        self.assertEqual(self.__private(viewWizard, "metadataWidgets")["title"][0].text(), "Batch Alpha")
        self.assertEqual(self.__private(viewWizard, "nextButton").text(), "Save changes")

        # edit the metadata and Save changes
        self.__private(viewWizard, "metadataWidgets")["title"][0].setText("Batch Beta")
        viewWizard.onClickedNext()  # Save changes -> updateMetadata + Home
        self.assertEqual(self.__title(self.persist.findById(workflowId)), "Batch Beta")

        # 3) delete (confirm dialog auto-accepted)
        original = QMessageBox.question
        QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
        try:
            deleteWizard = self.__wizard()
            deleteWizard.setViewWorkflow(workflowId)
            deleteWizard.show()
            self.app.processEvents()
            deleteWizard.onClickedDelete()  # Delete
        finally:
            QMessageBox.question = original
        self.assertIsNone(self.persist.findById(workflowId))

    def __title(self, workflow):
        fields = [f for f in workflow.getMetadataFields() if f.name == "title"]
        return fields[0].value if fields else None


if __name__ == "__main__":
    unittest.main()
