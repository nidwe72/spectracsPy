"""
CaptureDiagnosticsLogger (SPEC_capability_proof.md §7.0.1) — the env-gated per-frame capture log used by the
reference gray-outlier investigation. Proves the plumbing so the rig JSON (diagnoseCapture.py) is trustworthy:
every captured frame is recorded and the C1 dim-frame rejection mask flags the injected dim frames.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server" \
        ./venv/bin/python -m pytest tests/test_capture_diagnostics_logger.py -q
"""
import json
import os

from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.logic.spectral.acquisition.CaptureDiagnosticsLogger import CaptureDiagnosticsLogger

NM = [440.0, 500.0, 560.0, 620.0]


def _spectrumWithFrames(brightFrames, dimFrames):
    spectrum = Spectrum()
    for _ in range(brightFrames):
        spectrum.addToCapturedValuesByNanometers({nm: 100.0 for nm in NM})
    for _ in range(dimFrames):
        spectrum.addToCapturedValuesByNanometers({nm: 30.0 for nm in NM})   # coherently dim = the AE-ramp outlier
    return spectrum


def test_disabled_by_default_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.delenv(CaptureDiagnosticsLogger.ENV_DIR, raising=False)
    path = CaptureDiagnosticsLogger().log("REFERENCE", _spectrumWithFrames(6, 0))
    assert path is None
    assert not list(tmp_path.iterdir())


def test_logs_every_frame_and_flags_the_dim_ones(tmp_path, monkeypatch):
    monkeypatch.setenv(CaptureDiagnosticsLogger.ENV_DIR, str(tmp_path))
    spectrum = _spectrumWithFrames(brightFrames=8, dimFrames=2)   # 10 frames, 2 coherently dim

    path = CaptureDiagnosticsLogger().log("REFERENCE", spectrum, extra={"run": 1})

    assert path is not None and os.path.isfile(path)
    record = json.load(open(path))
    assert record["role"] == "REFERENCE"
    assert record["frameCount"] == 10
    assert len(record["frames"]) == 10 and len(record["kept"]) == 10
    # the two dim frames (the last two) are rejected; the eight bright ones kept
    assert record["rejectedCount"] == 2
    assert record["kept"][:8] == [True] * 8
    assert record["kept"][8:] == [False, False]
    # brightness recorded per frame; the reduced mean excludes the dim frames (~100, not dragged toward 30)
    assert record["frameBrightness"][0] == 100.0 and record["frameBrightness"][-1] == 30.0
    assert abs(record["reducedMean"]["560.0"] - 100.0) < 1.0
    assert record["extra"] == {"run": 1}


def test_no_captured_frames_is_a_safe_noop(tmp_path, monkeypatch):
    monkeypatch.setenv(CaptureDiagnosticsLogger.ENV_DIR, str(tmp_path))
    assert CaptureDiagnosticsLogger().log("SAMPLE", Spectrum()) is None
    assert CaptureDiagnosticsLogger().log("SAMPLE", None) is None
