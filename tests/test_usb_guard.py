"""W0.1 (SPEC_windows_build.md R3, U4–U6): asking the USB bus never crashes a caller.

On Windows pyusb has no libusb backend and `usb.core.find` raises NoBackendError. `isSensorConnected` (called by
the spectrometer-setup screen for every spectrometer) must report "absent" instead, remember the missing backend
so it stops asking, and still fail loudly on a malformed VID/PID. The poll thread reports absent once and stops.
"""
import sys

import pytest
import usb.core

import sciens.spectracs.logic.model.util.spectrometerSensor.ApplicationSpectrometerUtil as utilModule
from sciens.spectracs.logic.connection.ConnectionPollThread import ConnectionPollThread
from sciens.spectracs.logic.model.util.spectrometerSensor.ApplicationSpectrometerUtil import ApplicationSpectrometerUtil
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerSensor import SpectrometerSensor


def _sensor(vendorId="0c99", modelId="0001"):
    sensor = SpectrometerSensor()
    sensor.vendorId = vendorId
    sensor.modelId = modelId
    return sensor


@pytest.fixture(autouse=True)
def _resetBackendFlag(monkeypatch):
    monkeypatch.setattr(utilModule, "_usbBackendMissing", False)


def _raiser(exception):
    def find(**kwargs):
        raise exception
    return find


def test_no_backend_reads_absent_and_stops_asking(monkeypatch):
    calls = []

    def find(**kwargs):
        calls.append(kwargs)
        raise usb.core.NoBackendError("No backend available")

    monkeypatch.setattr(usb.core, "find", find)
    util = ApplicationSpectrometerUtil()
    assert util.isSensorConnected(_sensor()) is False
    assert util.isSensorConnected(_sensor()) is False
    assert len(calls) == 1


def test_any_other_usb_error_reads_absent(monkeypatch):
    monkeypatch.setattr(usb.core, "find", _raiser(OSError("access denied")))
    assert ApplicationSpectrometerUtil().isSensorConnected(_sensor()) is False
    assert utilModule._usbBackendMissing is False


def test_missing_pyusb_reads_absent(monkeypatch):
    monkeypatch.setitem(sys.modules, "usb", None)
    monkeypatch.setitem(sys.modules, "usb.core", None)
    assert ApplicationSpectrometerUtil().isSensorConnected(_sensor()) is False


def test_found_and_not_found(monkeypatch):
    seen = {}

    def find(idVendor, idProduct):
        seen["ids"] = (idVendor, idProduct)
        return object()

    monkeypatch.setattr(usb.core, "find", find)
    assert ApplicationSpectrometerUtil().isSensorConnected(_sensor("32e4", "8830")) is True
    assert seen["ids"] == (0x32e4, 0x8830)

    monkeypatch.setattr(usb.core, "find", lambda **kwargs: None)
    assert ApplicationSpectrometerUtil().isSensorConnected(_sensor()) is False


def test_malformed_vendor_id_stays_loud(monkeypatch):
    monkeypatch.setattr(usb.core, "find", lambda **kwargs: None)
    with pytest.raises(ValueError):
        ApplicationSpectrometerUtil().isSensorConnected(_sensor(vendorId="zz"))


def test_poll_thread_reports_absent_once_and_stops_without_backend(monkeypatch):
    calls = []

    def find(**kwargs):
        calls.append(kwargs)
        raise usb.core.NoBackendError("No backend available")

    monkeypatch.setattr(usb.core, "find", find)
    thread = ConnectionPollThread("0c99", "0001", intervalSeconds=0.1)
    emitted = []
    thread.presenceChanged.connect(emitted.append)
    thread.run()  # synchronously, on this thread: must return on its own
    assert emitted == [False]
    assert len(calls) == 1
