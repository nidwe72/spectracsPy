from typing import Optional


class Admission:
    """The plug the lamp may switch, or why there is none. `password` is the one that opened it (E11: often the MAC);
    `needsPassword` = the active instrument's plug was found but this PC cannot open it (R19)."""

    def __init__(self, device=None, password=None, needsPassword=False, reason=None, candidate=None):
        self.device = device
        self.password = password
        self.needsPassword = needsPassword
        self.reason = reason
        self.candidate = candidate

    @property
    def isDefaultPassword(self):
        return self.candidate is not None and self.candidate.isDefaultPassword


class LampAdmission:
    """Registered-only switching (SPEC_shelly_instrument_memory.md §11.3, E6): the lamp takes ONLY the plug whose
    device id is the active instrument's serial AND that carries a valid copy made for it. A stranger's Shelly, a
    fresh plug, or the plug of another instrument is never switched — not even as a fallback. Runs on the lamp
    worker thread (it reads the plug)."""

    def __init__(self, registry=None):
        self.registry = registry

    def admit(self, result, serial: Optional[str]) -> Admission:
        if not serial:
            return Admission(reason="no instrument serial")
        device = result.chosen
        if device is None or device.deviceId != serial:
            return Admission(reason="the instrument's plug was not found")
        candidate = self.__registry().classify(device)
        if candidate.isRegistered:
            return Admission(device, candidate.password, candidate=candidate)
        if candidate.label == "locked":
            return Admission(device, needsPassword=True, reason="plug found but locked", candidate=candidate)
        return Admission(reason="the plug holds no valid instrument data (%s)" % (candidate.reason or candidate.label),
                         candidate=candidate)

    def __registry(self):
        if self.registry is None:
            from sciens.spectracs.logic.instrumentMemory.PlugRegistry import PlugRegistry
            self.registry = PlugRegistry()
        return self.registry


class HostOverrideAdmission:
    """SPECTRACS_LAMP_HOST (LampService.HOST_ENV, G10) is an explicit operator choice — the test seam and the rig
    override: the plug at that host is admitted without the registered check (whoever sets the variable picks the
    plug), but still only with a password that opens it."""

    def __init__(self, store):
        self.store = store

    def admit(self, result, serial):
        device = result.chosen or (result.devices[0] if result.devices else None)
        if device is None:
            return Admission(reason="no plug at the override host")
        stored = self.store.load(mac=device.mac)[1]
        if device.authRequired and not stored:
            return Admission(device, device.mac, reason="override host, default password")
        return Admission(device, stored)
