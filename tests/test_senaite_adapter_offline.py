"""
L2-L5 — the SENAITE adapter orchestration, offline (a fake in-memory transport, no Docker). Verifies the
idempotent bottom-up ensure-or-create ordering, that master data is reused across submits, and that the
sample + attachment are created. SPEC_lims_integration.md §5. (Live behaviour verified separately against
the 6090 Docker.)

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python -m pytest tests/test_senaite_adapter_offline.py -q
"""
import unittest

from sciens.spectracs.logic.lims.adapters.senaite.SenaiteLimsGateway import SenaiteLimsGateway
from sciens.spectracs.logic.lims.dto.LimsSubmission import (
    LimsAnalysis, LimsCustomer, LimsInstrument, LimsReport, LimsSample, LimsSampleType, LimsSubmission)
from sciens.spectracs.logic.lims.dto.LimsTarget import LimsTarget


class FakeSenaite(SenaiteLimsGateway):
    """In-memory SENAITE: a stateful store so ensure-or-create behaves (search sees what create made)."""

    def __init__(self):
        self._base = "http://fake"
        self._user = "u"
        self._password = "p"
        self.store = {}            # portal_type -> [items]
        self.creates = []          # portal_types created, in order
        self._counter = 0

    def _request(self, method, path, params=None, body=None):
        if path == "/users/current":
            return {"items": [{"authenticated": True, "username": "u"}]}
        if path == "/search":
            return {"items": list(self.store.get((params or {}).get("portal_type"), []))}
        if path == "/create":
            self._counter += 1
            pt = body["portal_type"]
            self.creates.append(pt)
            title = body.get("title")
            if not title and pt == "Contact":               # SENAITE derives it from the name
                title = ("%s %s" % (body.get("Firstname", ""), body.get("Surname", ""))).strip()
            if not title and pt == "AnalysisRequest":
                title = "OIL-%04d" % self._counter
            item = {"uid": "uid-%d" % self._counter, "id": "%s-%d" % (pt.lower(), self._counter),
                    "title": title, "path": "/senaite/x/%s-%d" % (pt.lower(), self._counter),
                    "url": "http://fake/%s" % title}
            self.store.setdefault(pt, []).append(item)
            return {"items": [item]}
        if path == "/update":
            return {}
        return {}


def _submission():
    return LimsSubmission(
        customer=LimsCustomer("edwin", "Edwin Roth", "Edwin", "Roth", "e@x.example"),
        instrument=LimsInstrument("SN-1", "ELP-CFL", "ELP", "Handheld", "ELP Store"),
        sampleType=LimsSampleType("Pumpkin Oil", "OIL"),
        analyses=[LimsAnalysis("Spectracs Measurement", "SpectracsMeasurement", "Spectroscopy")],
        sample=LimsSample("2026-07-11T14:22:05", "run-1"),
        report=LimsReport(b"%PDF-1.7 x", "OIL-report.pdf"),
        target=LimsTarget("senaite", "SENAITE"))


class SenaiteAdapterOfflineTest(unittest.TestCase):

    def test_submit_creates_full_graph_bottom_up(self):
        gw = FakeSenaite()
        ref = gw.submit(_submission())
        self.assertTrue(ref.sampleId.startswith("OIL-"))
        # bottom-up order: instrument prereqs -> instrument -> sampletype -> service -> client -> contact -> AR -> attach
        self.assertEqual(gw.creates, [
            "InstrumentType", "Manufacturer", "Supplier", "Instrument", "SampleType",
            "AnalysisService", "Client", "Contact", "AnalysisRequest", "Attachment"])

    def test_datesampled_is_date_only(self):
        gw = FakeSenaite()
        captured = {}
        original = gw._create
        def spy(body):
            if body.get("portal_type") == "AnalysisRequest":
                captured["DateSampled"] = body.get("DateSampled")
            return original(body)
        gw._create = spy
        gw.submit(_submission())
        self.assertEqual(captured["DateSampled"], "2026-07-11")   # no time component

    def test_second_submit_reuses_master_data(self):
        gw = FakeSenaite()
        gw.submit(_submission())
        gw.creates = []
        gw.submit(_submission())
        # master data + client/contact already exist -> only a new sample + its attachment are created
        self.assertEqual(gw.creates, ["AnalysisRequest", "Attachment"])

    def test_check_connection(self):
        self.assertTrue(FakeSenaite().checkConnection().ok)


if __name__ == "__main__":
    unittest.main()
