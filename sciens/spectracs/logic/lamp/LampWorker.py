from PySide6.QtCore import QObject, Signal, Slot

from sciens.spectracs.logic.lamp.LampErrors import LampAuthFailed, LampUnreachable
from sciens.spectracs.logic.lamp.LampSetupHint import LampSetupHint


class LampWorker(QObject):
    # All lamp network I/O, on LampService's worker QThread (SPEC_lamp_switch.md §7, G2): the GUI thread never
    # waits on HTTP. Commands arrive as queued slots, results leave as signals. The switch to use travels with
    # each command, so the worker holds no state the GUI thread could race with.

    discovered = Signal(object, object)          # (LampDiscoveryResult, [unconfigured setup SSIDs])
    switched = Signal(bool, object)              # (on, error | None)
    statusRead = Signal(str, object, object)     # (purpose, LampStatus | None, error | None)

    def __init__(self, discovery, wifiScan=None):
        super().__init__()
        self.discovery = discovery
        self.wifiScan = wifiScan if wifiScan is not None else LampSetupHint.scanWifi

    @Slot(object)
    def discover(self, stored):
        result = self.discovery.discover(stored)
        knownMacs = [device.mac for device in result.devices]
        try:
            ssids = LampSetupHint.unconfiguredSsids(self.wifiScan(), knownMacs)
        except Exception:                        # the hint is a nicety; never let it fail discovery
            ssids = []
        self.discovered.emit(result, ssids)

    @Slot(object, int)
    def on(self, switch, capSeconds):
        try:
            switch.on(capSeconds)
            self.switched.emit(True, None)
        except LampUnreachable as error:
            self.switched.emit(True, error)

    @Slot(object)
    def indicator(self, switch):
        # best effort: the LED colour is a nicety — a failure here is noticed by the next real call, not here
        try:
            switch.applyIndicator()
        except (LampUnreachable, LampAuthFailed):
            pass

    @Slot(object)
    def off(self, switch):
        try:
            switch.off()
            self.switched.emit(False, None)
        except LampUnreachable as error:
            self.switched.emit(False, error)

    @Slot(object, str)
    def readStatus(self, switch, purpose):
        try:
            self.statusRead.emit(purpose, switch.status(), None)
        except LampUnreachable as error:
            self.statusRead.emit(purpose, None, error)
