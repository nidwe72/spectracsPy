import threading
from typing import Callable, Iterable, List, Optional

from sciens.spectracs.logic.lamp.LampDevice import LampDevice
from sciens.spectracs.logic.lamp.LampErrors import LampAuthFailed


class PlugLabel:
    # SPEC_shelly_instrument_memory.md §11.3: what a found plug is to this app.
    REGISTERED = "registered"   # ● carries a server-signed copy made for THIS plug's id — the only one ever switched
    KNOWN = "known"             # ◐ no valid copy, but the server knows its id as an instrument serial (online only)
    LOCKED = "locked"           # a password this PC does not know (R19) — never read, never switched
    FOREIGN = "foreign"         # ○ none of the above: a stranger's Shelly, or a fresh plug

    ORDER = (REGISTERED, KNOWN, LOCKED, FOREIGN)
    SYMBOL = {REGISTERED: "●", KNOWN: "◐", LOCKED: "🔒", FOREIGN: "○"}


class PlugCandidate:
    """One found plug with its label. `password` is the one that opened it (None: no password set / not opened);
    `copy` the verified InstrumentCopy of a ● plug."""

    def __init__(self, device: LampDevice, label: str, password: Optional[str] = None, copy=None, reason=None):
        self.device = device
        self.label = label
        self.password = password
        self.copy = copy
        self.reason = reason

    @property
    def isRegistered(self):
        return self.label == PlugLabel.REGISTERED

    @property
    def isDefaultPassword(self):
        """The plug is protected by its default password, the MAC (E11) — the C2 reminder."""
        return self.password is not None and self.password == self.device.mac

    def describe(self):
        text = "%s %s · %s" % (PlugLabel.SYMBOL[self.label], self.device.deviceId or self.device.mac, self.device.host)
        if self.copy is not None and self.copy.bundle:
            text += " · %s" % (self.copy.bundle.get("deviceCodeName") or "")
        return text

    def __repr__(self):
        return "PlugCandidate(%s, %s)" % (self.device, self.label)


class PlugRegistry:
    """Which found plug is ours (SPEC_shelly_instrument_memory.md §11.3, E6, R18/R19/R43). Network I/O ⇒ call it off
    the GUI thread.

    Passwords are tried in the order of R43: none if the plug has no password set; else the one this PC stored for
    the plug's MAC, then the default (the MAC, E11). A plug that opens with neither is LOCKED.
    "Registered" = its copy verifies (server signature, made for this plug's own id) — keys alone prove nothing on
    a plug anyone could write. The verdict is cached per MAC and the copy's sha256 (one KVS.Get to re-check)."""

    _cache = {}                                   # mac -> (sha256, PlugCandidate)
    _lock = threading.Lock()
    _classifyLock = threading.RLock()             # one plug read at a time: the 2nd caller gets the cached verdict

    def __init__(self, store=None, memoryFactory=None, trustedKeys: dict = None,
                 knownSerials: Optional[Callable[[], Iterable[str]]] = None):
        self.store = store
        self.memoryFactory = memoryFactory
        self.trustedKeys = trustedKeys
        self.knownSerials = knownSerials

    # --- passwords (R43) ---
    def passwordsFor(self, device: LampDevice) -> List[Optional[str]]:
        # A plug that had no password when probed may be hardened a moment later (the sync after login does
        # exactly that, L7 A2) ⇒ after "none" still try the stored password and the MAC.
        stored = self.__store().load(mac=device.mac)[1]
        candidates = [password for password in dict.fromkeys((stored, device.mac)) if password]
        return ([None] + candidates) if not device.authRequired else candidates

    # --- classification ---
    def classify(self, device: LampDevice, known: Optional[set] = None) -> PlugCandidate:
        # At login the lamp worker and the plug sync classify the same plug at once (L7 A2, 2026-10-20).
        with PlugRegistry._classifyLock:
            return self.__classify(device, known)

    def __classify(self, device: LampDevice, known: Optional[set] = None) -> PlugCandidate:
        from sciens.spectracs.logic.instrument.InstrumentCopyReader import InstrumentCopyReader, InstrumentCopyRefused
        for password in self.passwordsFor(device):
            memory = self.__memory(device, password)
            try:
                index = memory.index()
            except LampAuthFailed:
                continue
            except Exception as error:
                return PlugCandidate(device, PlugLabel.FOREIGN, password, reason="unreadable: %s" % error)
            sha = (index or {}).get("sha256")
            cached = self.__cached(device, sha)
            if cached is not None:
                return cached
            candidate = None
            try:
                entry = memory.readCopyEntry() if index is not None else None
                if entry is not None:
                    copy = InstrumentCopyReader().read(entry, device.deviceId, self.__trusted())
                    candidate = PlugCandidate(device, PlugLabel.REGISTERED, password, copy=copy)
            except InstrumentCopyRefused as refused:
                candidate = PlugCandidate(device, self.__unregistered(device, known), password, reason=refused.reason)
            except Exception as error:
                candidate = PlugCandidate(device, self.__unregistered(device, known), password,
                                          reason="unreadable copy: %s" % error)
            if candidate is None:
                candidate = PlugCandidate(device, self.__unregistered(device, known), password, reason="no copy")
            self.__remember(device, sha, candidate)
            return candidate
        return PlugCandidate(device, PlugLabel.LOCKED, reason="password unknown")

    def classifyAll(self, devices: Iterable[LampDevice]) -> List[PlugCandidate]:
        """Every device labelled, ours first (§11.3: ● ◐ 🔒 ○). The server's serial list is fetched once (R37)."""
        known = self.__knownSerials()
        candidates = [self.classify(device, known) for device in devices]
        return sorted(candidates, key=lambda c: PlugLabel.ORDER.index(c.label))

    @classmethod
    def forget(cls, mac: Optional[str] = None):
        """Drop the cached verdict (after a write to the plug, or a reset)."""
        with cls._lock:
            if mac is None:
                cls._cache.clear()
            else:
                cls._cache.pop(LampDevice("", "", mac).mac, None)

    # --- helpers ---
    def __unregistered(self, device, known):
        return PlugLabel.KNOWN if known and device.deviceId in known else PlugLabel.FOREIGN

    def __cached(self, device, sha):
        with self._lock:
            entry = self._cache.get(device.mac)
        if entry is None or sha is None or entry[0] != sha or entry[1].device.deviceId != device.deviceId:
            return None
        cached = entry[1]
        return PlugCandidate(device, cached.label, cached.password, cached.copy, cached.reason)

    def __remember(self, device, sha, candidate):
        if sha is None:
            return
        with self._lock:
            self._cache[device.mac] = (sha, candidate)

    def __knownSerials(self):
        if self.knownSerials is not None:
            try:
                return set(self.knownSerials() or ())
            except Exception:
                return set()
        try:
            from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
            if CurrentUserSession().isOffline() or not CurrentUserSession().isLoggedIn():
                return set()
            from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
            return {p.get("serial") for p in (SpectracsPyServerClient().listSpectrometerProfiles() or [])}
        except Exception:
            return set()

    def __memory(self, device, password):
        if self.memoryFactory is not None:
            return self.memoryFactory(device, password)
        from sciens.spectracs.logic.instrumentMemory.PlugInstrumentMemory import PlugInstrumentMemory
        return PlugInstrumentMemory.forDevice(device, password)

    def __store(self):
        if self.store is None:
            from sciens.spectracs.logic.lamp.LampPlugDbStore import LampPlugDbStore
            self.store = LampPlugDbStore()
        return self.store

    def __trusted(self):
        if self.trustedKeys is not None:
            return self.trustedKeys
        from sciens.spectracs.logic.security.TrustedKeys import TRUSTED_COPY_KEYS
        return TRUSTED_COPY_KEYS
