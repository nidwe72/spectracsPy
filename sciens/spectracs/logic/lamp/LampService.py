import logging
import os
import time

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from sciens.base.SingletonQObject import SingletonQObject
from sciens.spectracs.logic.lamp.LampDiscovery import LampDiscovery
from sciens.spectracs.logic.lamp.LampDriverRegistry import LampDriverRegistry
from sciens.spectracs.logic.lamp.LampErrors import LampAuthFailed, LampUnreachable
from sciens.spectracs.logic.lamp.LampPlugStore import LampPlugStore
from sciens.spectracs.logic.lamp.LampState import LampState
from sciens.spectracs.logic.lamp.LampWorker import LampWorker

LOG = logging.getLogger(__name__)


class LampService(QObject, metaclass=SingletonQObject):
    """The app's one lamp (SPEC_lamp_switch.md §7, §16.2). Lives on the GUI thread and owns the clocks; every
    network call goes to a LampWorker on its own QThread (G2).

    Who drives it:
      - the header (MainStatusBarViewModule) on session change: configure(applicable) — real device logged in
        => discover the plug; virtual / logged out => NOT_APPLICABLE, lamp off (G4)
      - the workflow host on every phase entry: applyPhase(owner, lampPolicy, phase) — the plugin decides (D5);
        cancel / home / hide: releaseWorkflow(owner) (D14), off only if that owner switched it on (G7)
      - the header icon: toggleManual() — host default cap/warm-up (G3), ignored while a capture runs (U6)
      - CapturePanel: setCaptureRunning(); readyForCapture() is its gate (D2)
      - spectracsMain exit hooks: shutdown() — synchronous off, idempotent (§7.1, D15)

    The cap is enforced by the PLUG (toggle_after, D4); this clock only mirrors it to stop a running capture
    before dark frames reach the evaluation (§4.3) and to show the remaining time.
    """

    stateChanged = Signal(str)
    warmUpTick = Signal(int, int)               # (remaining s, total s)
    lampWentOff = Signal(str)                   # "cap" | "external" — a running capture must stop
    hintChanged = Signal()                      # noPower / needsPassword / setupSsids / plug changed
    testResult = Signal(str)                    # Settings → Lamp [Test]: the inline report (§16 U12)

    _cmdDiscover = Signal(object)
    _cmdOn = Signal(object, int)
    _cmdOff = Signal(object)
    _cmdStatus = Signal(object, str)
    _cmdIndicator = Signal(object)

    _abandonedThreads = []                      # see shutdown()

    HOST_CAP_SECONDS = 1800                     # G3: manual toggle without a workflow
    HOST_WARM_UP_SECONDS = 20
    POLL_MS = 10000                             # external changes (§7)
    POWER_CHECK_MS = 3000                       # apower reads 0 W for ~1 s after on (§15.3)
    NO_POWER_WATTS = 2.0
    SHUTDOWN_TIMEOUT_SECONDS = 1.0              # × 2 tries (§14.2)
    WORKER_JOIN_MS = 2500                       # > one in-flight call on the normal 2 s timeout (a poll when the
                                                # plug is gone); a shorter join destroyed the running QThread
    TEST_ON_MS = 2500                           # [Test]: on for ~2 s, power read at 2.5 s (meter latency §15.3)
    HOST_ENV = "SPECTRACS_LAMP_HOST"            # test seam + rig override: skip discovery, use this host (G10)

    def __init__(self, clock=None, threaded=True, discovery=None, plugStore=None, wifiScan=None):
        super().__init__()
        self.clock = clock if clock is not None else time.monotonic
        self.plugStore = plugStore if plugStore is not None else LampService.__defaultStore()
        self.state = LampState.NOT_APPLICABLE
        self.switch = None
        self.device = None
        self.otherDevices = []
        self.setupSsids = []
        self.needsPassword = False
        self.noPower = False
        self.onAt = None                         # when the lamp went on (warm-up clock)
        self.capStartedAt = None                 # when the plug's timer was last armed; None = unknown
        self.capSeconds = None
        self.warmUpSeconds = self.HOST_WARM_UP_SECONDS
        self.owner = None                        # the workflow view that runs a switched plugin
        self.wantsOn = False                     # that workflow's current phase wants the lamp (ACQUISITION)
        self.ownerPolicy = None                  # that workflow's LampPolicy — to switch on when the plug returns
        self.lastOnBy = None                     # who issued the last on (G7 owner token)
        self.pendingOn = None                    # an on that arrived while SEARCHING
        self.captureRunning = False
        self.stateBeforeUnreachable = None
        self.lastOffReason = None                # "cap" / "external" until the next on — the coach line keeps it
        self.testing = False                     # a [Test] pulse is running: its on/off are not the workflow's
        self.isShutDown = False

        self.tickTimer = QTimer(self)
        self.tickTimer.setInterval(1000)
        self.tickTimer.timeout.connect(self.tick)
        self.pollTimer = QTimer(self)
        self.pollTimer.setInterval(self.POLL_MS)
        self.pollTimer.timeout.connect(self.poll)

        host = os.environ.get(self.HOST_ENV)
        if discovery is None:
            discovery = LampDiscovery(mdnsBrowse=lambda types, seconds: [host], subnetHosts=lambda: []) if host \
                else LampDiscovery()
        self.worker = LampWorker(discovery, wifiScan=wifiScan if wifiScan is not None
                                 else ((lambda: []) if host else None))
        self.thread = None
        if threaded:
            self.thread = QThread()
            self.thread.setObjectName("LampWorker")
            self.worker.moveToThread(self.thread)
            self.thread.start()
        self._cmdDiscover.connect(self.worker.discover)
        self._cmdOn.connect(self.worker.on)
        self._cmdOff.connect(self.worker.off)
        self._cmdStatus.connect(self.worker.readStatus)
        self._cmdIndicator.connect(self.worker.indicator)
        self.worker.discovered.connect(self.__onDiscovered)
        self.worker.switched.connect(self.__onSwitched)
        self.worker.statusRead.connect(self.__onStatus)

    @staticmethod
    def __defaultStore():
        try:
            from sciens.spectracs.logic.lamp.LampPlugDbStore import LampPlugDbStore
            return LampPlugDbStore()
        except ImportError:
            return LampPlugStore()

    # --- session (header) --------------------------------------------------------------------------------
    def configure(self, applicable):
        """Real device logged in => find the plug; virtual / logged out => lamp off, NOT_APPLICABLE (G4)."""
        if not applicable:
            if self.switch is not None and self.state in (LampState.WARMING, LampState.ON, LampState.UNREACHABLE):
                self._cmdOff.emit(self.switch)
            self.__reset()
            self.__setState(LampState.NOT_APPLICABLE)
            return
        if self.state == LampState.NOT_APPLICABLE:
            self.discover()

    def discover(self):
        """(Re)run discovery — at login and from Settings → Lamp "Search again"."""
        if self.isShutDown:
            return
        self.__setState(LampState.SEARCHING)
        stored, _ = self.plugStore.load()
        self._cmdDiscover.emit(stored)

    def setPassword(self, password):
        """Settings → Lamp [Save]: store, then rediscover so the switch is rebuilt with it."""
        self.plugStore.savePassword(password)
        self.discover()

    def __onDiscovered(self, result, setupSsids):
        if self.state != LampState.SEARCHING:          # logged out / shut down while searching
            return
        self.device = result.chosen
        self.otherDevices = result.others()
        self.setupSsids = list(setupSsids)
        self.needsPassword = False
        if self.device is None:
            self.switch = None
            self.__setState(LampState.NO_PLUG)
        else:
            self.plugStore.saveDevice(self.device)
            _, password = self.plugStore.load()
            if self.device.authRequired and not password:
                self.switch = None
                self.needsPassword = True
                self.__setState(LampState.NO_PLUG)
            else:
                self.switch = LampDriverRegistry.byName(self.device.driverName).create(self.device, password)
                self.__setState(LampState.OFF)
                self._cmdIndicator.emit(self.switch)           # LED ring: dim grey when off, not red
                self._cmdStatus.emit(self.switch, "sync")      # the plug may already be on
        self.hintChanged.emit()
        pending, self.pendingOn = self.pendingOn, None
        if pending is not None and self.switch is not None:
            self.switchOn(*pending)
        else:
            self.__resumeForOwner()

    # --- workflow (host) ---------------------------------------------------------------------------------
    def applyPhase(self, owner, lampPolicy, phaseType):
        """Called on every phase entry (D5). Plugins that are not `switched` never touch the lamp."""
        if lampPolicy is None or not lampPolicy.isSwitched():
            if self.owner is owner:
                self.owner = None
                self.ownerPolicy = None
                self.wantsOn = False
            return
        self.owner = owner
        self.ownerPolicy = lampPolicy
        self.wantsOn = lampPolicy.isOnDuring(phaseType)
        self.hintChanged.emit()                  # the icon turns amber / plain with the phase
        if self.wantsOn:
            self.__switchOnForOwner()
        else:
            self.switchOff()

    def __switchOnForOwner(self):
        policy = self.ownerPolicy
        self.switchOn(policy.getCapSeconds(), policy.getWarmUpSeconds(), policy.getMaxMeasurementSeconds(),
                      self.owner)

    def __resumeForOwner(self):
        # The plug came back (re-plugged / found by "Search again") while the workflow still wants the lamp: the
        # phase-entry on was lost to NO_PLUG / UNREACHABLE, so issue it now — the warm-up starts afresh. A lamp the
        # cap or the plug's own button switched off is NOT this case: those leave via __markOff(reason=...).
        if self.wantsOn and self.owner is not None and self.ownerPolicy is not None \
                and self.switch is not None and self.state == LampState.OFF:
            self.__switchOnForOwner()

    def releaseWorkflow(self, owner):
        """Cancel / home / view hidden (D14): off — but only if this view switched it on (G7)."""
        if self.owner is owner:
            self.owner = None
            self.ownerPolicy = None
            self.wantsOn = False
            self.hintChanged.emit()
        if self.lastOnBy is owner and self.state in (LampState.WARMING, LampState.ON, LampState.SEARCHING):
            self.switchOff()
        if self.pendingOn is not None and self.pendingOn[3] is owner:
            self.pendingOn = None

    def setCaptureRunning(self, running):
        self.captureRunning = bool(running)

    def readyForCapture(self):
        """The CapturePanel gate (§16.2): closed only while a switched workflow is active and the lamp is
        searching, off or warming. No plug / unreachable / not applicable => open (the user switches by hand)."""
        if self.owner is None or not self.wantsOn:
            return True
        return self.state not in (LampState.SEARCHING, LampState.OFF, LampState.WARMING)

    def hasKnownPlug(self):
        """The icon shows only on desks that have (had) a plug (§16 U7)."""
        return self.device is not None or self.plugStore.load()[0] is not None

    # --- switching ---------------------------------------------------------------------------------------
    def switchOn(self, capSeconds, warmUpSeconds, minRemainingSeconds=0, by=None):
        if self.isShutDown or self.state == LampState.NOT_APPLICABLE:
            return
        self.lastOnBy = by
        if self.state == LampState.SEARCHING:
            self.pendingOn = (capSeconds, warmUpSeconds, minRemainingSeconds, by)
            return
        if self.switch is None:
            return
        if self.state in (LampState.WARMING, LampState.ON):
            remaining = self.capRemainingSeconds()
            if remaining is None or remaining < minRemainingSeconds:       # Q1: re-arm a nearly spent cap
                self.capSeconds = capSeconds
                self._cmdOn.emit(self.switch, int(capSeconds))
            return
        self.capSeconds = capSeconds
        self.warmUpSeconds = warmUpSeconds
        self._cmdOn.emit(self.switch, int(capSeconds))

    def switchOff(self):
        self.pendingOn = None
        if self.switch is None or self.isShutDown:
            return
        self._cmdOff.emit(self.switch)

    def testPulse(self):
        """Settings → Lamp [Test]: on ~2 s, read the power, off — reported via testResult. The plug's own cap
        (10 s) switches it off even if the app dies in between."""
        if self.switch is None or self.captureRunning or self.state in (LampState.WARMING, LampState.ON):
            self.testResult.emit("Not now — the lamp is in use." if self.switch is not None
                                 else "No lamp plug to test.")
            return
        self.testing = True
        self._cmdOn.emit(self.switch, 10)
        QTimer.singleShot(self.TEST_ON_MS, lambda: self._cmdStatus.emit(self.switch, "test")
                          if self.switch is not None else None)

    def toggleManual(self):
        """The header icon. Returns False when the click was ignored (capture running, U6)."""
        if self.captureRunning or self.switch is None:
            return False
        if self.state in (LampState.WARMING, LampState.ON):
            self.switchOff()
        else:
            self.switchOn(self.HOST_CAP_SECONDS, self.HOST_WARM_UP_SECONDS, 0, by="manual")
        return True

    def __onSwitched(self, on, error):
        if self.state == LampState.NOT_APPLICABLE or self.isShutDown:   # a reply after logout / exit
            return
        if error is not None:
            if self.testing:
                self.testing = False
                self.testResult.emit("Wrong password." if isinstance(error, LampAuthFailed)
                                     else "The plug did not answer.")
            self.__onError(error)
            return
        if self.testing:                        # the test pulse leaves the state machine alone
            return
        now = self.clock()
        if on:
            self.capStartedAt = now
            self.lastOffReason = None
            if self.state not in (LampState.WARMING, LampState.ON):
                self.onAt = now
                self.noPower = False
                self.__setState(LampState.WARMING)
                self.warmUpTick.emit(self.warmUpSeconds, self.warmUpSeconds)
                QTimer.singleShot(self.POWER_CHECK_MS, self.__checkPower)
            self.tickTimer.start()
            self.pollTimer.start()
        else:
            self.__markOff()

    def __checkPower(self):
        if self.switch is not None and self.state in (LampState.WARMING, LampState.ON):
            self._cmdStatus.emit(self.switch, "power")

    # --- clocks ------------------------------------------------------------------------------------------
    def tick(self):
        """1 s while on: warm-up countdown, WARMING → ON, and the mirrored cap (§4.3)."""
        if self.state not in (LampState.WARMING, LampState.ON) or self.onAt is None:
            return
        now = self.clock()
        if self.capStartedAt is not None and self.capSeconds is not None \
                and now - self.capStartedAt >= self.capSeconds:
            self.__markOff(reason="cap")
            self.lampWentOff.emit("cap")
            return
        if self.state == LampState.WARMING:
            remaining = max(0, int(round(self.warmUpSeconds - (now - self.onAt))))
            if remaining <= 0:
                self.__setState(LampState.ON)
            else:
                self.warmUpTick.emit(remaining, self.warmUpSeconds)

    def poll(self):
        if self.switch is not None and self.state in (LampState.OFF, LampState.WARMING, LampState.ON,
                                                      LampState.UNREACHABLE):
            self._cmdStatus.emit(self.switch, "poll")

    def offMessage(self):
        """Why a running measurement was stopped (§16 U5) — None after a normal off."""
        if self.lastOffReason == "cap":
            return "Lamp switched off after %d min — measurement stopped." % round((self.capSeconds or 0) / 60.0)
        if self.lastOffReason == "external":
            return "The lamp went off — measurement stopped."
        return None

    def capRemainingSeconds(self):
        if self.capStartedAt is None or self.capSeconds is None or self.state not in (LampState.WARMING, LampState.ON):
            return None
        return max(0.0, self.capSeconds - (self.clock() - self.capStartedAt))

    def warmUpRemainingSeconds(self):
        if self.state != LampState.WARMING or self.onAt is None:
            return 0
        return max(0, int(round(self.warmUpSeconds - (self.clock() - self.onAt))))

    def __onStatus(self, purpose, status, error):
        if self.state in (LampState.NOT_APPLICABLE, LampState.SEARCHING, LampState.NO_PLUG) or self.isShutDown:
            return
        if purpose == "test":
            self.__finishTest(status, error)
            return
        if error is not None:
            if purpose != "power":
                self.__onError(error)
            return
        if self.state == LampState.UNREACHABLE:
            previous, self.stateBeforeUnreachable = self.stateBeforeUnreachable, None
            if status.isOn and previous in (LampState.WARMING, LampState.ON):
                self.__setState(previous)
            elif status.isOn:
                self.__adoptExternalOn()
            else:
                self.__markOff()
                self.__resumeForOwner()
            return
        if purpose == "power":
            noPower = status.isOn and status.watts is not None and status.watts < self.NO_POWER_WATTS
            if noPower != self.noPower:
                self.noPower = noPower
                self.hintChanged.emit()
            return
        if status.isOn and self.state == LampState.OFF:
            self.__adoptExternalOn()
        elif not status.isOn and self.state in (LampState.WARMING, LampState.ON):
            self.__markOff(reason="external")
            self.lampWentOff.emit("external")

    def __finishTest(self, status, error):
        if error is not None:
            self.testResult.emit("The plug did not answer.")
        elif status.watts is None:
            self.testResult.emit("On 2 s ✓")
        elif status.watts < self.NO_POWER_WATTS:
            self.testResult.emit("On 2 s · %.1f W — the lamp draws no power: check the switch on the lamp socket."
                                 % status.watts)
        else:
            self.testResult.emit("On 2 s · %.1f W ✓" % status.watts)
        if self.switch is not None:
            self._cmdOff.emit(self.switch)
        self.testing = False

    def __adoptExternalOn(self):
        # Switched by the plug's button, the web page or another app instance (G5/G6): it is on, we do not know
        # since when — treat it as warm and its cap as unknown, so the next ACQUISITION entry re-arms it (Q1).
        self.onAt = self.clock() - self.warmUpSeconds
        self.capStartedAt = None
        self.__setState(LampState.ON)
        self.tickTimer.start()
        self.pollTimer.start()

    def __onError(self, error):
        LOG.warning("lamp: %s", error)
        if isinstance(error, LampAuthFailed):
            self.switch = None
            self.needsPassword = True
            self.__markOff(LampState.NO_PLUG)
            self.hintChanged.emit()
            return
        if self.state != LampState.UNREACHABLE:
            self.stateBeforeUnreachable = self.state
            self.__setState(LampState.UNREACHABLE)
            self.pollTimer.start()

    def __markOff(self, state=LampState.OFF, reason=None):
        self.lastOffReason = reason
        self.onAt = None
        self.capStartedAt = None
        self.noPower = False
        self.tickTimer.stop()
        self.__setState(state)

    def __reset(self):
        self.switch = None
        self.device = None
        self.otherDevices = []
        self.setupSsids = []
        self.needsPassword = False
        self.pendingOn = None
        self.owner = None
        self.ownerPolicy = None
        self.wantsOn = False
        self.lastOnBy = None
        self.onAt = None
        self.capStartedAt = None
        self.tickTimer.stop()
        self.pollTimer.stop()

    def __setState(self, state):
        if state != self.state:
            self.state = state
            self.stateChanged.emit(state.value)

    # --- exit (§7.1) -------------------------------------------------------------------------------------
    def shutdown(self):
        """Lamp off on every exit path the app can see. Synchronous on the calling thread (the worker may be
        stopping), 1 s × 2 tries, then the worker is joined. Idempotent: the 2nd and later calls do nothing."""
        if self.isShutDown:
            return
        self.isShutDown = True
        self.tickTimer.stop()
        self.pollTimer.stop()
        switch = self.switch
        if switch is not None:
            switch.setTimeout(self.SHUTDOWN_TIMEOUT_SECONDS)
            for attempt in (1, 2):
                try:
                    switch.off()
                    break
                except LampUnreachable as error:
                    LOG.warning("lamp: shutdown off, try %d: %s", attempt, error)
        if self.thread is not None:
            self.thread.quit()
            if not self.thread.wait(self.WORKER_JOIN_MS):
                # still inside a long call (a discovery scan): keep the QThread referenced, so it is never
                # destroyed while running — the process ends around it
                LOG.warning("lamp: worker still busy at exit, left to the process end")
                LampService._abandonedThreads.append(self.thread)
