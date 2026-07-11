"""
L1 — the LIMS abstraction seam (LIMS-agnostic, no Docker). Exercises the neutral submission model,
the LimsGateway/LimsGatewayFactory, and MockLimsGateway end-to-end. SPEC_lims_integration.md §3/§4, L1.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python -m pytest tests/test_lims_gateway_mock.py -q
"""
import unittest

from sciens.spectracs.logic.lims.LimsError import LimsError
from sciens.spectracs.logic.lims.LimsGateway import LimsGateway
from sciens.spectracs.logic.lims.LimsGatewayFactory import LimsGatewayFactory
from sciens.spectracs.logic.lims.MockLimsGateway import MockLimsGateway
from sciens.spectracs.logic.lims.dto.LimsSampleRef import LimsSampleRef
from sciens.spectracs.logic.lims.dto.LimsSubmission import (
    LimsAnalysis, LimsCustomer, LimsInstrument, LimsReport, LimsSample, LimsSampleType,
    LimsSubmission)
from sciens.spectracs.logic.lims.dto.LimsTarget import LimsTarget


def _submission(target=None):
    return LimsSubmission(
        customer=LimsCustomer("acme", "Acme Oil", "Jane", "Roe", "jane@acme.example"),
        instrument=LimsInstrument("SN-123", "Spectracs V1", "Spectracs", "Spectrometer", "Spectracs"),
        sampleType=LimsSampleType("Pumpkin Oil", "OIL"),
        analyses=[LimsAnalysis("Spectracs Measurement", "SpectracsMeasurement", "Spectroscopy")],
        sample=LimsSample("2026-07-11T14:22:05", externalId="run-42"),
        report=LimsReport(b"%PDF-1.7 fake", "OIL-report.pdf"),
        target=target or LimsTarget("mock", "MOCK"))


class LimsSeamTest(unittest.TestCase):

    def test_mock_is_a_gateway(self):
        self.assertIsInstance(MockLimsGateway(), LimsGateway)

    def test_factory_resolves_mock_backend(self):
        gateway = LimsGatewayFactory.create(LimsTarget("mock", "MOCK"))
        self.assertIsInstance(gateway, MockLimsGateway)

    def test_factory_unknown_backend_raises(self):
        with self.assertRaises(LimsError):
            LimsGatewayFactory.create(LimsTarget("nope", "X"))

    def test_check_connection_ok(self):
        health = MockLimsGateway().checkConnection()
        self.assertTrue(health.ok)

    def test_submit_returns_ref_from_sample_type_code(self):
        gateway = MockLimsGateway()
        ref = gateway.submit(_submission())
        self.assertIsInstance(ref, LimsSampleRef)
        self.assertEqual(ref.sampleId, "OIL-0001")

    def test_submit_records_and_increments(self):
        gateway = MockLimsGateway()
        first = gateway.submit(_submission())
        second = gateway.submit(_submission())
        self.assertEqual(first.sampleId, "OIL-0001")
        self.assertEqual(second.sampleId, "OIL-0002")
        self.assertEqual(len(gateway.submissions), 2)
        self.assertIs(gateway.lastSubmission, gateway.submissions[-1])

    def test_submission_todict_omits_pdf_bytes(self):
        data = _submission().toDict()
        self.assertEqual(data["report"], {"fileName": "OIL-report.pdf", "bytes": 13})
        self.assertEqual(data["analyses"][0]["key"], "SpectracsMeasurement")
        self.assertNotIn("pdfBytes", data["report"])

    def test_register_custom_backend(self):
        LimsGatewayFactory.register("mock2", lambda configKey: MockLimsGateway(configKey))
        try:
            gateway = LimsGatewayFactory.create(LimsTarget("mock2", "CFG"))
            self.assertIsInstance(gateway, MockLimsGateway)
            self.assertEqual(gateway.configKey, "CFG")
        finally:
            LimsGatewayFactory._registry.pop("mock2", None)


if __name__ == "__main__":
    unittest.main()
