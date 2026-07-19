"""
L1-RPC — server-side assembly of a LIMS-neutral submission from the AppUser + spectrometer graph
(the pure `LimsLogicModule.buildSubmission`, no DB, no Docker). Then feed it through the mock adapter.
SPEC_lims_integration.md §3 / L1-RPC.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python -m pytest tests/test_lims_submission_assembly.py -q
"""
import unittest
from types import SimpleNamespace

from sciens.spectracs.logic.lims.LimsLogicModule import LimsLogicModule
from sciens.spectracs.logic.lims.MockLimsGateway import MockLimsGateway


def _appUser():
    return SimpleNamespace(username="edwin", displayName="Edwin Roth", firstName="Edwin",
                           lastName="Roth", email="edwin@example.com", enabled=True,
                           registeredSerial="SN-123")


def _setup(style="Handheld", vendor="ELP", sensor_seller="ELP Store", model="ELP-CFL"):
    spectrometer = SimpleNamespace(
        modelName=model,
        spectrometerVendor=SimpleNamespace(vendorName=vendor) if vendor is not None else None,
        spectrometerStyle=SimpleNamespace(styleName=style) if style is not None else None,
        spectrometerSensor=SimpleNamespace(sellerName=sensor_seller) if sensor_seller is not None else None)
    profile = SimpleNamespace(serial="SN-123", spectrometer=spectrometer)
    return SimpleNamespace(spectrometerProfile=profile)


def _pluginInfo():
    return {
        "target": {"backend": "mock", "configKey": "MOCK"},
        "sampleType": {"name": "Pumpkin Oil", "code": "OIL"},
        "analyses": [{"name": "Spectracs Measurement", "key": "SpectracsMeasurement",
                      "group": "Spectroscopy"}],
        "externalId": "run-42",
        "dateSampledIso": "2026-07-11T14:22:05",
    }


class SubmissionAssemblyTest(unittest.TestCase):

    def setUp(self):
        self.submission = LimsLogicModule().buildSubmission(
            _appUser(), _setup(), _pluginInfo(), b"%PDF-1.7 fake")

    def test_customer_from_app_user(self):
        c = self.submission.customer
        self.assertEqual(c.code, "edwin")               # stable key = username
        self.assertEqual(c.name, "Edwin Roth")
        self.assertEqual((c.contactFirst, c.contactLast, c.email),
                         ("Edwin", "Roth", "edwin@example.com"))

    def test_instrument_from_spectrometer_graph(self):
        i = self.submission.instrument
        self.assertEqual(i.serial, "SN-123")
        self.assertEqual(i.model, "ELP-CFL")
        self.assertEqual(i.manufacturer, "ELP")
        self.assertEqual(i.kind, "Handheld")
        self.assertEqual(i.supplier, "ELP Store")

    def test_kind_falls_back_when_style_missing(self):
        submission = LimsLogicModule().buildSubmission(
            _appUser(), _setup(style=None), _pluginInfo(), b"x")
        self.assertEqual(submission.instrument.kind, "Spectrometer")

    def test_missing_vendor_sensor_default_not_blank(self):
        # Vendor/sensor are a hard invariant (a real spectrometer always has them). If the graph is
        # nonetheless incomplete we substitute a non-empty house label rather than send SENAITE a blank-title
        # Manufacturer/Supplier — a blank field IS the corrupt-data exposure we want to avoid. "Spectracs" is a
        # legitimate manufacturer name (also the hardware maker). SPEC_test_hygiene_debt.md T4.
        submission = LimsLogicModule().buildSubmission(
            _appUser(), _setup(vendor=None, sensor_seller=None), _pluginInfo(), b"x")
        self.assertEqual(submission.instrument.manufacturer, "Spectracs")
        self.assertEqual(submission.instrument.supplier, "Spectracs")

    def test_plugin_slice_and_report(self):
        s = self.submission
        self.assertEqual((s.sampleType.name, s.sampleType.code), ("Pumpkin Oil", "OIL"))
        self.assertEqual(len(s.analyses), 1)
        self.assertEqual(s.analyses[0].key, "SpectracsMeasurement")
        self.assertEqual(s.target.backend, "mock")
        self.assertEqual(s.sample.externalId, "run-42")
        self.assertEqual(s.report.fileName, "OIL-report.pdf")   # default from sampleType code

    def test_end_to_end_through_mock(self):
        ref = MockLimsGateway().submit(self.submission)
        self.assertEqual(ref.sampleId, "OIL-0001")


if __name__ == "__main__":
    unittest.main()
