class LampPlugStore:
    # Where the plugs found so far and their passwords live (SPEC_lamp_switch.md §6, D9) — one entry per MAC
    # (SPEC_shelly_instrument_memory.md R33). The app uses the DB implementation (LampPlugDbStore); tests use this
    # in-memory one, with the same calls.

    def __init__(self):
        self.__rows = {}                         # mac -> [LampDevice, password]

    def load(self, deviceId=None, mac=None):
        """-> (LampDevice | None, password | None): the entry with that device id or MAC, else (no key) the first."""
        for device, password in self.__rows.values():
            if (deviceId is None and mac is None) or (deviceId is not None and device.deviceId == deviceId) \
                    or (mac is not None and device.mac == mac.upper().replace(":", "")):
                return device, password
        return None, None

    def loadAll(self):
        return [(device, password) for device, password in self.__rows.values()]

    def saveDevice(self, device):
        """Remember the plug (host may have changed by DHCP); a stored password for the same MAC is kept."""
        password = self.__rows.get(device.mac, [None, None])[1]
        self.__rows[device.mac] = [device, password]

    def savePassword(self, password, mac=None):
        key = mac.upper().replace(":", "") if mac is not None else next(iter(self.__rows), None)
        if key in self.__rows:
            self.__rows[key][1] = password or None
