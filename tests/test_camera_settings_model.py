"""CS1a + CS1b (SPEC_camera_settings.md §3): the camera vocabulary, the spectral profiles and resolve().

Qt-free and pure — no camera, no ioctl. The ELP numbers are its firmware defaults from §11c.11 of the Windows
spec, so the table these tests pin is the one §3.3 prints.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python -m pytest tests/test_camera_settings_model.py -q
"""
import json

import pytest

from sciens.spectracs.plugin_sdk import CameraControl, CameraSettings
from sciens.spectracs.logic.camera.CameraDevice import CameraDevice, CameraControlRange
from sciens.spectracs.logic.camera.CameraProfile import CameraProfile
from sciens.spectracs.logic.camera.CameraSettingsResolver import CameraSettingsResolver, WRITE_ORDER

C = CameraControl


def elp():
    """The ELP 32e4:8830 as its firmware describes itself (Windows spec §11c.11)."""
    return CameraDevice({
        C.AUTO_EXPOSURE: CameraControlRange("AUTO", choices=["MANUAL", "AUTO"]),
        C.EXPOSURE: CameraControlRange(78, 1, 5000, 1),
        C.WHITE_BALANCE_AUTO: CameraControlRange(True, choices=[False, True]),
        C.WHITE_BALANCE_KELVIN: CameraControlRange(4600, 2800, 6500, 10),
        C.GAIN: CameraControlRange(0, 0, 100, 1),
        C.BACKLIGHT: CameraControlRange(1, 0, 2, 1),
        C.BRIGHTNESS: CameraControlRange(0, -64, 64, 1),
        C.CONTRAST: CameraControlRange(32, 0, 64, 1),
        C.SATURATION: CameraControlRange(75, 0, 128, 1),
        C.HUE: CameraControlRange(0, -40, 40, 1),
        C.GAMMA: CameraControlRange(100, 72, 500, 1),
        C.SHARPNESS: CameraControlRange(3, 0, 6, 1),
        C.POWER_LINE_FREQUENCY: CameraControlRange("50", choices=["DISABLED", "50", "60"]),
        C.DYNAMIC_FRAMERATE: CameraControlRange(False, choices=[False, True]),
    }, name="HD USB Camera")


# --- CS1a: the vocabulary --------------------------------------------------------------------------------------

def test_settings_round_trip_through_plain_json():
    settings = CameraSettings({"EXPOSURE": 90, C.WHITE_BALANCE_AUTO: False, "POWER_LINE_FREQUENCY": "50"})
    wire = json.loads(json.dumps(settings.toJson()))
    assert wire == {"EXPOSURE": 90, "WHITE_BALANCE_AUTO": False, "POWER_LINE_FREQUENCY": "50"}
    assert CameraSettings.fromJson(wire) == settings


def test_a_newer_records_unknown_control_is_dropped_not_fatal():
    assert CameraSettings.fromJson({"EXPOSURE": 90, "FOCUS_ABSOLUTE": 3}).toJson() == {"EXPOSURE": 90}


def test_a_plain_dict_is_as_good_as_the_class():
    assert CameraSettings.of({"GAIN": 0}) == CameraSettings({C.GAIN: 0})
    assert len(CameraSettings.of(None)) == 0
    with pytest.raises(ValueError):
        CameraSettings({"NOT_A_CONTROL": 1})


def test_the_persisted_strings_are_the_member_names():
    # ⛔ add, never rename: every report's record carries these strings
    assert all(control.value == control.name for control in CameraControl)


# --- CS1b: profiles + resolve() --------------------------------------------------------------------------------

def test_measurement_freezes_every_auto_loop_and_sets_every_control():
    resolution = CameraSettingsResolver.resolve(elp(), CameraProfile.MEASUREMENT, exposureSeed=150)
    requested = resolution.requested
    assert requested.get(C.AUTO_EXPOSURE) == "MANUAL"
    assert requested.get(C.WHITE_BALANCE_AUTO) is False
    assert requested.get(C.WHITE_BALANCE_KELVIN) == 6500
    assert requested.get(C.BACKLIGHT) == 0                     # Edwin's backlight question: off for a measurement
    assert requested.get(C.GAMMA) == 100                       # device default, but WRITTEN (it persists in the camera)
    assert len(requested) == len(CameraControl)                 # every control the camera offers
    assert resolution.sources[C.GAMMA] == "device"
    assert resolution.sources[C.BACKLIGHT] == "profile"
    assert resolution.autoLoopsOn == []


def test_calibration_keeps_auto_wb_and_the_backlight_default():
    resolution = CameraSettingsResolver.resolve(elp(), CameraProfile.CALIBRATION)
    assert resolution.requested.get(C.WHITE_BALANCE_AUTO) is True
    assert resolution.requested.get(C.BACKLIGHT) == 1          # D12: calibration now SETS the default, 1
    assert resolution.exposure() == 150                         # the legacy open value, then the AE sweep
    assert C.WHITE_BALANCE_KELVIN in resolution.inactive        # unwritable under auto WB: neither written nor compared
    assert not resolution.requested.has(C.WHITE_BALANCE_KELVIN)


def test_idle_is_measurement_minus_the_plugin():
    idle = CameraSettingsResolver.resolve(elp(), CameraProfile.IDLE, pluginOverride={"GAMMA": 120}, exposureSeed=150)
    measurement = CameraSettingsResolver.resolve(elp(), CameraProfile.MEASUREMENT, exposureSeed=150)
    assert idle.requested == measurement.requested              # the override never reaches IDLE
    assert idle.requested.get(C.GAMMA) == 100


def test_the_plugin_wins_over_profile_and_device():
    resolution = CameraSettingsResolver.resolve(
        elp(), CameraProfile.MEASUREMENT, pluginOverride={"EXPOSURE": 90, "WHITE_BALANCE_KELVIN": 6500},
        exposureSeed=150)
    assert resolution.exposure() == 90
    assert resolution.exposureSource() == "plugin"
    assert resolution.sources[C.WHITE_BALANCE_KELVIN] == "plugin"   # Q7: declared explicitly ⇒ the record says so


def test_exposure_seed_precedence():
    assert CameraSettingsResolver.resolve(elp(), CameraProfile.MEASUREMENT).exposure() == 78     # device default
    seeded = CameraSettingsResolver.resolve(elp(), CameraProfile.MEASUREMENT, exposureSeed=120)
    assert (seeded.exposure(), seeded.exposureSource()) == (120, "profile")


def test_clamp_and_snap_are_said_never_silent():
    resolution = CameraSettingsResolver.resolve(
        elp(), CameraProfile.MEASUREMENT, pluginOverride={"WHITE_BALANCE_KELVIN": 7000, "EXPOSURE": 9000})
    assert resolution.requested.get(C.WHITE_BALANCE_KELVIN) == 6500
    assert resolution.adjusted[C.WHITE_BALANCE_KELVIN] == "requested 7000 → 6500 (clamped)"
    assert resolution.exposure() == 5000
    snapped = CameraSettingsResolver.resolve(elp(), CameraProfile.MEASUREMENT,
                                             pluginOverride={"WHITE_BALANCE_KELVIN": 4607})
    assert snapped.requested.get(C.WHITE_BALANCE_KELVIN) == 4610       # step 10 (D6e: else Q4 refuses on quantisation)
    assert "(snapped)" in snapped.adjusted[C.WHITE_BALANCE_KELVIN]


def test_a_backend_quantiser_beats_the_linear_step():
    # Windows exposure: whole log2 seconds, v4l2 = 10000 * 2^k (§3.3a) — 90 lands on 78
    import math
    quantise = lambda v4l2: int(round(10000 * 2 ** round(math.log2(v4l2 / 10000.0))))
    device = CameraDevice({C.EXPOSURE: CameraControlRange(78, 1, 5000, 1, quantise=quantise)})
    resolution = CameraSettingsResolver.resolve(device, CameraProfile.MEASUREMENT, pluginOverride={"EXPOSURE": 90})
    assert resolution.exposure() == 78
    assert resolution.adjusted[C.EXPOSURE] == "requested 90 → 78 (snapped)"


def test_a_control_the_camera_does_not_offer_is_skipped():
    device = CameraDevice({C.EXPOSURE: CameraControlRange(78, 1, 5000, 1)})
    resolution = CameraSettingsResolver.resolve(device, CameraProfile.MEASUREMENT)
    assert C.WHITE_BALANCE_KELVIN in resolution.skipped and C.BACKLIGHT in resolution.skipped
    assert resolution.requested.toJson() == {"EXPOSURE": 78}
    empty = CameraSettingsResolver.resolve(CameraDevice(), CameraProfile.MEASUREMENT, exposureSeed=90)
    assert len(empty.requested) == 0 and C.EXPOSURE in empty.skipped


def test_rejected_entries_and_menu_values_not_offered():
    resolution = CameraSettingsResolver.resolve(
        elp(), CameraProfile.MEASUREMENT,
        pluginOverride={"FOCUS": 3, "GAIN": "loud", "POWER_LINE_FREQUENCY": "AUTO"})
    assert any(note.startswith("FOCUS") for note in resolution.rejected)
    assert any(note.startswith("GAIN") for note in resolution.rejected)
    assert resolution.requested.get(C.GAIN) == 0
    assert resolution.requested.get(C.POWER_LINE_FREQUENCY) == "50"          # the ELP offers no AUTO
    assert "not offered" in resolution.adjusted[C.POWER_LINE_FREQUENCY]


def test_an_auto_loop_switched_on_by_the_plugin_is_accepted_and_badged():
    resolution = CameraSettingsResolver.resolve(elp(), CameraProfile.MEASUREMENT,
                                                pluginOverride={"WHITE_BALANCE_AUTO": True})
    assert resolution.requested.get(C.WHITE_BALANCE_AUTO) is True
    assert resolution.autoLoopsOn == [C.WHITE_BALANCE_AUTO]
    assert C.WHITE_BALANCE_KELVIN in resolution.inactive


def test_writes_go_manual_before_their_values():
    writes = [control for control, _ in CameraSettingsResolver.resolve(elp(), CameraProfile.MEASUREMENT).writes()]
    assert writes.index(C.AUTO_EXPOSURE) < writes.index(C.EXPOSURE)
    assert writes.index(C.WHITE_BALANCE_AUTO) < writes.index(C.WHITE_BALANCE_KELVIN)
    assert writes == [control for control in WRITE_ORDER if control in writes]


def test_mismatches_compare_only_what_was_requested():
    resolution = CameraSettingsResolver.resolve(elp(), CameraProfile.MEASUREMENT, exposureSeed=90)
    applied = resolution.requested.merged({"GAMMA": 120})
    assert resolution.mismatches(resolution.requested) == []
    assert resolution.mismatches(applied) == [(C.GAMMA, 100, 120)]
    unreadable = CameraSettings({control: value for control, value in resolution.requested.items()
                                 if control is not C.GAIN})
    assert resolution.mismatches(unreadable) == [(C.GAIN, 0, None)]       # a camera that will not say is not proof


def test_the_resolution_serialises_with_plain_strings():
    wire = json.loads(json.dumps(CameraSettingsResolver.resolve(
        elp(), CameraProfile.MEASUREMENT, pluginOverride={"EXPOSURE": 90}).toJson()))
    assert wire["profile"] == "MEASUREMENT"
    assert wire["sources"]["EXPOSURE"] == "plugin"
    assert wire["requested"]["BACKLIGHT"] == 0
