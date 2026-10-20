from sciens.spectracs.view.application.widgets.InWindowDialog import InWindowDialog


class AddPlugViewModule:
    """Plug page → [Add new plug…] (SPEC_shelly_instrument_memory.md §11.5, L6): the in-window steps around
    PlugOnboardingLogicModule — scan over Bluetooth → pick the plug → WLAN name (this PC's) + password → join →
    wait until it is on the LAN. The WLAN password goes to the plug only; it is never stored (E13). Nothing else is
    written to the plug (E10). The network steps run as _Jobs, so the window stays alive; the dialogs are in-window
    (no second top-level window, P4c)."""

    def __init__(self, host, onJoined=None, logic=None):
        from sciens.spectracs.logic.instrumentMemory.PlugOnboardingLogicModule import PlugOnboardingLogicModule
        self.host = host
        self.onJoined = onJoined
        self.logic = logic or PlugOnboardingLogicModule()
        self.found = []
        self.job = None

    @staticmethod
    def run(host, onJoined=None):
        from sciens.spectracs.logic.instrumentMemory.PlugOnboardingLogicModule import PlugOnboardingLogicModule
        if not PlugOnboardingLogicModule.available():
            host.resultLabel.setText("✗ Add new plug needs Linux and the Python package 'bleak' (Bluetooth).")
            return
        flow = AddPlugViewModule(host, onJoined)
        host._addPlugFlow = flow                       # keep it (and its jobs) alive
        flow.scan()

    def __job(self, work, onDone):
        from sciens.spectracs.view.settings.instrumentPlug.InstrumentPlugViewModule import _Job
        self.job = _Job(work, self.host)
        self.job.done.connect(onDone)
        self.job.start()

    def scan(self):
        self.host.resultLabel.setText("Looking for new plugs over Bluetooth (about 10 s) …")
        lanMacs = [c.device.mac for c in getattr(self.host, "candidates", [])]

        def work():
            self.found = self.logic.newPlugs(lanMacs)
            return "%d new plug(s)" % len(self.found)
        self.__job(work, self.__onScanned)

    def __onScanned(self, text):
        if text.startswith("✗"):
            self.host.resultLabel.setText(text)
            return
        if not self.found:
            self.host.resultLabel.setText("✗ No new plug over Bluetooth. A new or factory-reset plug blinks and "
                                          "opens its own WiFi — plug it in near this PC and try again.")
            return
        buttons = [(shelly.describe(), index, "secondary") for index, shelly in enumerate(self.found)]
        buttons.append(("Cancel", None, None))
        chosen = InWindowDialog.choose(self.host, "Which plug?",
                                       "Plugs seen over Bluetooth that are not on the network yet (nearest first).",
                                       buttons)
        if chosen is None:
            self.host.resultLabel.setText("")
            return
        self.shelly = self.found[chosen]
        values = InWindowDialog.askFields(self.host, "Join the WLAN",
                                          "The plug %s joins this WLAN. The password goes to the plug only — it is "
                                          "not stored." % self.shelly.name,
                                          [("ssid", "WLAN", self.logic.currentSsid() or "", False),
                                           ("password", "WLAN password", "", True)])
        if not values or not values.get("ssid"):
            self.host.resultLabel.setText("")
            return
        ssid, wlanPassword = values["ssid"], values["password"]
        self.host.resultLabel.setText("Sending the WLAN to %s over Bluetooth …" % self.shelly.name)
        shelly = self.shelly

        def work():
            text = self.logic.join(shelly, ssid, wlanPassword)
            if not text.startswith("✓"):
                return text
            device = self.logic.waitOnLan(shelly.mac)
            if device is None:
                return "✗ %s took the WLAN but did not appear on the network within a minute — wrong WLAN " \
                       "password? It keeps its own WiFi open; try again." % shelly.name
            return "✓ %s is on the network at %s (%s). Nothing else was written — next: Harden, then create its " \
                   "setup." % (shelly.name, device.host, device.deviceId)
        self.__job(work, self.__onJoined)

    def __onJoined(self, text):
        self.host.resultLabel.setText(text)
        if text.startswith("✓") and self.onJoined is not None:
            self.onJoined(text)                         # looks again, keeping this line
