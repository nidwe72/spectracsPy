"""D4 — the section structure is part of the RECORD (SPEC_settled_measurement.md §27.14a, G1).

⭐ The plugin declares which phases are sectioned by step; the WORKFLOW carries it. Everything downstream —
the chevron, a re-opened run, the PDF's headings, a LIMS addon with no plugin loaded — then reads the
structure from the record instead of from a live plugin.

Covers the three carriers: the DB column, `toReportJson()`, and `report_reconstruct` reading it back.

Run from the spectracsPy repo root:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python -m pytest tests/test_sectioned_phases.py -q
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "diagnostics"))

from sciens.spectracs.logic.persistence.database.spectral.PersistSpectralWorkflowLogicModule import PersistSpectralWorkflowLogicModule
from sciens.spectracs.model.spectral.SpectralWorkflow import SpectralWorkflow
from sciens.spectracs.model.spectral.SpectralWorkflowPhase import SpectralWorkflowPhase
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType

USER_ID = "test-user-sectioned-phases"
ACQUISITION = SpectralWorkflowPhaseType.ACQUISITION
PROCESSING = SpectralWorkflowPhaseType.PROCESSING


def _workflow():
    workflow = SpectralWorkflow()
    workflow.userId = USER_ID
    workflow.username = "sectionUser"
    phase = SpectralWorkflowPhase()
    phase.setType(ACQUISITION)
    workflow.addToPhases(phase)
    return workflow


class SectionedPhasesTest(unittest.TestCase):

    def setUp(self):
        self.persist = PersistSpectralWorkflowLogicModule()
        self.workflowId = None

    def tearDown(self):
        if self.workflowId is not None:
            self.persist.delete(self.workflowId, userId=USER_ID)

    def test_a_run_made_before_D4_reads_as_no_sub_sections(self):
        # ⭐ §27.16/N5 — NULL is not a missing value to guess at, it IS the pre-D4 behaviour.
        self.assertEqual(frozenset(), _workflow().getSectionedPhases())

    def test_it_survives_the_real_database(self):
        workflow = _workflow()
        workflow.setSectionedPhases({ACQUISITION})
        self.persist.save(workflow)
        self.workflowId = workflow.id
        self.assertEqual(frozenset({ACQUISITION}),
                         self.persist.findById(self.workflowId).getSectionedPhases())

    def test_the_stored_order_is_STABLE_not_the_frozensets(self):
        # ⛔ §27.16/N4: a frozenset's iteration order is a hash detail. If it reached the column, two
        # identical runs would differ byte for byte — and "same input, same record" would quietly die.
        first, second = _workflow(), _workflow()
        first.setSectionedPhases(frozenset({ACQUISITION, PROCESSING}))
        second.setSectionedPhases(frozenset({PROCESSING, ACQUISITION}))
        self.assertEqual(first.sectionedPhasesJson, second.sectionedPhasesJson)
        self.assertEqual('["ACQUISITION", "PROCESSING"]', first.sectionedPhasesJson)

    def test_an_empty_declaration_stores_NULL_rather_than_an_empty_list(self):
        workflow = _workflow()
        workflow.setSectionedPhases(frozenset())
        self.assertIsNone(workflow.sectionedPhasesJson)

    def test_it_travels_in_the_report_json_and_comes_back(self):
        # ⭐ §27.16/N3 — the carrier that matters for a LIMS addon and for regenerating an archived report:
        # no DB, no plugin, just the document.
        from report_reconstruct import workflowFromReportJson
        workflow = _workflow()
        workflow.setSectionedPhases({ACQUISITION})
        report = workflow.toReportJson()
        self.assertEqual(["ACQUISITION"], report["sectionedPhases"])
        self.assertEqual(frozenset({ACQUISITION}), workflowFromReportJson(report).getSectionedPhases())

    def test_a_pre_D4_report_reconstructs_without_sub_sections(self):
        from report_reconstruct import workflowFromReportJson
        legacy = _workflow().toReportJson()
        del legacy["sectionedPhases"]                       # what all 124 archived reports look like
        self.assertEqual(frozenset(), workflowFromReportJson(legacy).getSectionedPhases())


if __name__ == "__main__":
    unittest.main()
