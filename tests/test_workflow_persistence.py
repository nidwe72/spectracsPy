"""
Workflow persistence (Option A) — P1/P2/P3: the model/spectral classes are SQLAlchemy entities; a workflow
graph saves + reloads via PersistSpectralWorkflowLogicModule, with the float-key + view-model JSON round-trip
and the metadata EAV rows. Exercises the real app DB.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python -m pytest tests/test_workflow_persistence.py -q
"""
import unittest

from sciens.spectracs.logic.persistence.database.spectral.PersistSpectralWorkflowLogicModule import PersistSpectralWorkflowLogicModule
from sciens.spectracs.model.spectral.SpectraContainer import SpectraContainer
from sciens.spectracs.model.spectral.SpectralWorkflow import SpectralWorkflow
from sciens.spectracs.model.spectral.SpectralWorkflowMetadata import SpectralWorkflowMetadata
from sciens.spectracs.model.spectral.SpectralWorkflowPhase import SpectralWorkflowPhase
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.model.spectral.SpectralWorkflowStep import SpectralWorkflowStep
from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.model.spectral.evaluation.ColorSwatchView import ColorSwatchView
from sciens.spectracs.model.spectral.evaluation.EvaluationResult import EvaluationResult
from sciens.spectracs.model.spectral.evaluation.VerdictView import VerdictView

USER_ID = "test-user-persistence"


def _buildWorkflow():
    workflow = SpectralWorkflow()
    workflow.username = "pumpkinTestUser"
    workflow.userId = USER_ID
    workflow.pluginCodeRef = "x.Plugin"
    workflow.timestampIso = "2026-07-02T15:04:00"

    processing = SpectralWorkflowPhase()
    processing.setType(SpectralWorkflowPhaseType.PROCESSING)
    workflow.addToPhases(processing)
    absorptionStep = SpectralWorkflowStep()
    absorptionStep.setLabel("Absorption")
    processing.addToSteps(absorptionStep)
    container = SpectraContainer()
    spectrum = Spectrum()
    spectrum.setValuesByNanometers({404.9: 12.0, 406.1: 12.3, 512.7: 5.5})
    container.addToSpectra(spectrum, "ABSORPTION")
    absorptionStep.setContainer(container)

    evaluation = SpectralWorkflowPhase()
    evaluation.setType(SpectralWorkflowPhaseType.EVALUATION)
    workflow.addToPhases(evaluation)
    evaluationStep = SpectralWorkflowStep()
    evaluation.addToSteps(evaluationStep)
    evaluationResult = EvaluationResult()
    evaluationResult.addItem(ColorSwatchView((10, 200, 20), "measured"))
    evaluationResult.addItem(VerdictView("PERFECT-ROASTED", hueDegrees=60.0))
    evaluationStep.setEvaluationResult(evaluationResult)

    titleField = SpectralWorkflowMetadata()
    titleField.name = "title"; titleField.label = "Title"; titleField.type = "TEXT"
    titleField.value = "Batch A"; titleField.showInWorkflowsTable = True
    workflow.addToMetadataFields(titleField)
    return workflow


class WorkflowPersistenceTest(unittest.TestCase):

    def setUp(self):
        self.persist = PersistSpectralWorkflowLogicModule()

    def test_save_reload_update_delete(self):
        workflow = _buildWorkflow()
        self.persist.save(workflow)
        workflowId = workflow.id

        loaded = self.persist.findById(workflowId)
        self.assertIsNotNone(loaded)

        # spectra: float nm keys (the R1 guard) + values intact
        absorption = list(loaded.getPhase(SpectralWorkflowPhaseType.PROCESSING).getSteps().values())[0]
        spectrum = absorption.getContainer().getSpectra()["ABSORPTION"]
        self.assertTrue(all(isinstance(k, float) for k in spectrum.valuesByNanometers.keys()))
        self.assertAlmostEqual(spectrum.valuesByNanometers[404.9], 12.0)

        # evaluation view-models survive (verdict + hueDegrees)
        evaluationStep = list(loaded.getPhase(SpectralWorkflowPhaseType.EVALUATION).getSteps().values())[0]
        verdicts = [i for i in evaluationStep.getEvaluationResult().getItems() if isinstance(i, VerdictView)]
        self.assertEqual(verdicts[0].roastState, "PERFECT-ROASTED")
        self.assertEqual(verdicts[0].hueDegrees, 60.0)

        # metadata
        self.assertEqual(self.__title(loaded), "Batch A")

        # per-user list
        self.assertIn(workflowId, [w.id for w in self.persist.listForUser(USER_ID)])

        # targeted metadata update
        self.persist.updateMetadata(workflowId, {"title": "Batch B"}, userId=USER_ID)
        self.assertEqual(self.__title(self.persist.findById(workflowId)), "Batch B")

        # delete: ownership guard blocks a foreign user, then the owner deletes (cascade)
        self.persist.delete(workflowId, userId="someone-else")
        self.assertIsNotNone(self.persist.findById(workflowId))
        self.persist.delete(workflowId, userId=USER_ID)
        self.assertIsNone(self.persist.findById(workflowId))

    def __title(self, workflow):
        return [f for f in workflow.getMetadataFields() if f.name == "title"][0].value


if __name__ == "__main__":
    unittest.main()
