"""CS4 (SPEC_camera_settings.md §6): the plugin's camera override and the Camera-tab switch.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python -m pytest tests/test_plugin_camera_settings.py -q
"""
from sciens.spectracs.logic.camera.CameraSettingsResolver import pluginOverrideOf
from sciens.spectracs.plugin_sdk import CameraSettings, SpectralPlugin
from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin
from sciens.spectracs.plugins.pumpkin.PumpkinOilPlugin import PumpkinOilPlugin

DEFAULTS = CameraSettings({"EXPOSURE": 78, "CONTRAST": 32})


class _OldSignedRow:
    """A v1.x DB row: only the `exposure` attribute, no `cameraSettings` hook at all."""
    exposure = 90


class _Raises(SpectralPlugin):
    exposure = 120

    def cameraSettings(self, deviceDefaults):
        raise RuntimeError("boom")


class _RelativeToTheDevice(SpectralPlugin):
    def cameraSettings(self, deviceDefaults):
        return CameraSettings({"CONTRAST": deviceDefaults.get("CONTRAST") + 4})


def test_the_base_plugin_declares_nothing():
    plugin = SpectralPlugin()
    assert plugin.cameraSettings(DEFAULTS) is None and plugin.showsCameraTab() is False
    assert pluginOverrideOf(plugin, DEFAULTS) == (None, None)


def test_the_dev_plugin_declares_exposure_and_white_balance_and_keeps_its_pin():
    plugin = DevSpectralPlugin()
    assert pluginOverrideOf(plugin, DEFAULTS) == ({"EXPOSURE": 90, "WHITE_BALANCE_KELVIN": 6500}, None)
    assert plugin.exposure == 90                     # E4: an older app without the hook still pins
    assert plugin.showsCameraTab() is True           # Q9: only the dev bench shows the Camera tab
    assert PumpkinOilPlugin().showsCameraTab() is False


def test_an_old_signed_row_still_pins_its_exposure():
    assert pluginOverrideOf(_OldSignedRow(), DEFAULTS) == ({"EXPOSURE": 90}, None)


def test_a_raising_plugin_falls_back_and_says_so():
    override, problem = pluginOverrideOf(_Raises(), DEFAULTS)
    assert override == {"EXPOSURE": 120}             # the attribute still holds
    assert "raised" in problem


def test_an_override_can_be_relative_to_the_firmware():
    assert pluginOverrideOf(_RelativeToTheDevice(), DEFAULTS) == ({"CONTRAST": 36}, None)


def test_nonsense_is_refused_not_fatal():
    class _Nonsense(SpectralPlugin):
        def cameraSettings(self, deviceDefaults):
            return {"FOCUS": 3}
    override, problem = pluginOverrideOf(_Nonsense(), DEFAULTS)
    assert override is None and "not camera settings" in problem
