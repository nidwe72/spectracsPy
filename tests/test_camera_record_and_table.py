"""CS6, CS6.5, CS7 (SPEC_camera_settings.md §4, §7): the per-leg camera record, the ONE table builder, the PDF section
and the re-opened run.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python -m pytest tests/test_camera_record_and_table.py -q
"""
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from sciens.spectracs.logic.camera.CameraSettingsTable import cameraRecordsOf, cameraSettingsTable
from sciens.spectracs.logic.persistence.database.spectral.PersistSpectralWorkflowLogicModule import \
    PersistSpectralWorkflowLogicModule
from sciens.spectracs.logic.spectral.report.WorkflowReportBuilder import WorkflowReportBuilder
from sciens.spectracs.logic.spectral.workflow.SpectralWorkflowEngine import SpectralWorkflowEngine
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
from sciens.spectracs.model.spectral.plugin.view.ViewModelFactory import ViewModelFactory
from sciens.spectracs.plugin_sdk import ReportView
from sciens.spectracs.plugin_sdk.roles import REFERENCE, SAMPLE
from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin
from sciens.spectracs.view.spectral.workflow.render.WorkflowPhaseRenderer import WorkflowPhaseRenderer

APP = QApplication.instance() or QApplication([])
ACQUISITION = SpectralWorkflowPhaseType.ACQUISITION
USER_ID = "test-user-camera-record"

STATE = {"AUTO_EXPOSURE": "MANUAL", "EXPOSURE": 90, "WHITE_BALANCE_AUTO": False, "WHITE_BALANCE_KELVIN": 6500,
         "GAIN": 0, "BACKLIGHT": 0, "GAMMA": 100}


def _open():
    return CameraOpenRecord(
        profile="MEASUREMENT", camera={"name": "HD USB Camera", "vendorId": "32e4", "modelId": "8830"},
        host={"os": "Linux", "backend": "V4L2", "pixelFormat": "YUYV", "conversion": "own"},
        deviceDefaults={"AUTO_EXPOSURE": "AUTO", "EXPOSURE": 78, "WHITE_BALANCE_AUTO": True,
                        "WHITE_BALANCE_KELVIN": 4600, "GAIN": 0, "BACKLIGHT": 1, "GAMMA": 100},
        requested=dict(STATE), applied=dict(STATE), heldBackFrames=5,
        sources={"EXPOSURE": "plugin", "WHITE_BALANCE_KELVIN": "plugin", "BACKLIGHT": "profile", "GAMMA": "device",
                 "AUTO_EXPOSURE": "profile", "WHITE_BALANCE_AUTO": "profile", "GAIN": "profile"})


def _record(role, atStart=None, atEnd=None, source="plugin", openRecord=None):
    leg = CameraLegSnapshot(role=role, atStart=dict(atStart or STATE), atEnd=dict(atEnd or atStart or STATE),
                            requestedExposure=90, exposureSource=source,
                            exposureNative={"start": {"value": 90, "unit": "v4l2_100us"}})
    return CameraSettingsRecordView(openRecord or _open(), leg, showsTab=True)


def _step(role, label, items=(), spectrum=False):
    step = SpectralWorkflowStep()
    step.setRole(role)
    step.setLabel(label)
    result = EvaluationResult()
    for item in items:
        result.addItem(item)
    step.setEvaluationResult(result)
    if spectrum:
        values = Spectrum()
        values.setValuesByNanometers({500.0: 10.0, 600.0: 20.0})
        container = SpectraContainer()
        container.addToSpectra(values, role)
        step.setContainer(container)
    return step


def _workflow(steps):
    workflow = SpectralWorkflow()
    workflow.userId = USER_ID
    workflow.username = "cameraRecordUser"
    workflow.pluginCodeRef = "dev.DevSpectralPlugin"
    phase = SpectralWorkflowPhase()
    phase.setType(ACQUISITION)
    workflow.addToPhases(phase)
    for step in steps:
        phase.addToSteps(step)
    return workflow


# --- CS6: the record ------------------------------------------------------------------------------------------

def test_the_record_round_trips_through_the_view_model_factory():
    view = _record(REFERENCE)
    wire = json.loads(json.dumps(view.toJson()))
    back = ViewModelFactory.fromJson(wire)
    assert isinstance(back, CameraSettingsRecordView)
    assert back.toJson() == view.toJson()
    assert back.isShownInReport is False                         # a record, not a drawing


def test_the_record_survives_the_real_database():
    workflow = _workflow([_step(REFERENCE, "Reference", [_record(REFERENCE)], spectrum=True)])
    persist = PersistSpectralWorkflowLogicModule()
    persist.save(workflow)
    try:
        loaded = persist.findById(workflow.id)
        records = cameraRecordsOf(loaded.getPhase(ACQUISITION).getSteps().values())
        assert len(records) == 1 and records[0].leg.atStart["BACKLIGHT"] == 0
        assert records[0].openRecord.deviceDefaults["BACKLIGHT"] == 1 and records[0].showsTab
    finally:
        persist.delete(workflow.id, userId=USER_ID)


def test_attach_replaces_by_type_and_detach_drops():
    engine = SpectralWorkflowEngine(DevSpectralPlugin())
    step = _step(REFERENCE, "Reference")
    engine.attachCameraRecord(step, _record(REFERENCE))
    engine.attachCameraRecord(step, _record(REFERENCE, source="auto-exposure"))
    assert [record.leg.exposureSource for record in cameraRecordsOf([step])] == ["auto-exposure"]
    engine.detachCameraRecord(step)
    assert cameraRecordsOf([step]) == []


def test_the_header_exposure_is_derived_from_the_legs():
    workflow = _workflow([_step(REFERENCE, "Reference", [_record(REFERENCE)])])
    workflow.exposureApplied = 104                                # the old field loses to the record
    header = workflow.toReportJson()["header"]
    assert header["exposureApplied"] == 90                        # d2r_all_runs.py reads the REQUEST, unchanged
    assert header["cameraExposure"][0]["source"] == "plugin"
    assert SpectralWorkflow().toReportJson()["header"]["cameraExposure"] is None


# --- CS6.5: the one table -------------------------------------------------------------------------------------

def _rows(table):
    return {row["control"]: row for row in table.rows}


def test_agreeing_legs_read_as_one_applied_column():
    table = cameraSettingsTable([_record(REFERENCE), _record(SAMPLE, source="locked-from-reference")])
    keys = [column["key"] for column in table.columns]
    assert keys == ["control", "device", "requested", "applied", "source"]
    assert "reference = sample ✓" in table.title and "HD USB Camera 32e4:8830" in table.title
    rows = _rows(table)
    assert rows["Exposure"]["applied"] == "90 (9.0 ms)"
    assert rows["Exposure"]["source"] == "plugin / locked-from-reference"
    assert rows["Backlight compensation"]["device"] == "1 (on)"
    assert rows["Backlight compensation"]["applied"] == "0 (off)"
    assert rows["White balance"]["applied"] == "6500 K"
    assert "MEASUREMENT profile · held back 5 frames after open" in table.caption


def test_a_difference_splits_the_column_and_is_marked():
    sample = dict(STATE, GAMMA=120)
    table = cameraSettingsTable([_record(REFERENCE), _record(SAMPLE, atStart=sample)])
    assert "⛔ reference ≠ sample" in table.title
    rows = _rows(table)
    assert (rows["Gamma"]["leg:REFERENCE"], rows["Gamma"]["leg:SAMPLE"]) == ("100", "120")
    assert rows["Gamma"]["check"] == "⛔ ref ≠ sample" and rows["Gain"]["check"] == ""


def test_drift_within_a_leg_is_shown():
    table = cameraSettingsTable([_record(SAMPLE, atStart=STATE, atEnd=dict(STATE, WHITE_BALANCE_KELVIN=6400))])
    assert _rows(table)["White balance"]["leg:SAMPLE"] == "6500 K → 6400 K"


def test_an_auto_loop_left_on_is_badged():
    opening = _open()
    opening.autoLoopsOn = ["WHITE_BALANCE_AUTO"]
    table = cameraSettingsTable([_record(REFERENCE, openRecord=opening)])
    assert "⛔ auto loop on" in _rows(table)["White balance auto"]["source"]
    assert "⛔ auto loop on — not a frozen instrument state" in table.caption


def test_a_virtual_run_is_one_line_and_no_records_no_table():
    virtual = CameraSettingsRecordView(CameraOpenRecord.virtualRun(), CameraLegSnapshot(role=REFERENCE))
    table = cameraSettingsTable([virtual])
    assert table.textRows() == [["virtual — no camera controls"]]
    assert cameraSettingsTable([]) is None


def test_windows_states_the_whole_log2_step():
    record = _record(REFERENCE)
    record.leg.exposureNative = {"start": {"value": -7, "unit": "log2_s"}}
    applied = _rows(cameraSettingsTable([record]))["Exposure"]["applied"]
    assert applied == "90 → applied -7 (7.8 ms, nearest whole log₂ step)"


# --- CS7: the PDF ---------------------------------------------------------------------------------------------

def _texts(figures):
    return [text.get_text() for figure in figures for text in figure.texts]


def test_the_report_carries_one_camera_section_after_acquisition():
    workflow = _workflow([_step(REFERENCE, "Reference", [_record(REFERENCE)]),
                          _step(SAMPLE, "Sample", [_record(SAMPLE)])])
    workflow.setSectionedPhases({ACQUISITION})
    figures = WorkflowReportBuilder(workflow, ReportView(title="Test report")).build().figures()
    texts = _texts(figures)
    assert texts.count("Camera settings") == 1
    assert texts.index("ACQUISITION") < texts.index("Camera settings")
    assert any("reference = sample ✓" in text for text in texts)


def test_a_run_without_records_has_no_camera_section():
    workflow = _workflow([_step(REFERENCE, "Reference")])
    texts = _texts(WorkflowReportBuilder(workflow, ReportView(title="Test report")).build().figures())
    assert "Camera settings" not in texts


# --- E1: the re-opened run ------------------------------------------------------------------------------------

def test_a_record_never_reaches_the_passive_renderer():
    step = _step(REFERENCE, "Reference", [_record(REFERENCE)], spectrum=True)
    assert WorkflowPhaseRenderer().stepViewModels(step) == []
    # ⛔ E1: had it passed, the re-opened reference tab would have been an EMPTY widget instead of its plot
    assert WorkflowPhaseRenderer().renderStep(step) is None
