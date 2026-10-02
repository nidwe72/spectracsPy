class LampPlugStore:
    # Where the plug found last time and its password live (SPEC_lamp_switch.md §6, D9). The app uses the DB
    # implementation (LampPlugDbStore); tests use this in-memory one.

    def __init__(self):
        self.__device = None
        self.__password = None

    def load(self):
        """-> (LampDevice | None, password | None)"""
        return self.__device, self.__password

    def saveDevice(self, device):
        """Remember the plug (host may have changed by DHCP); a stored password for the same MAC is kept."""
        if self.__device is None or self.__device.mac != device.mac:
            self.__password = None
        self.__device = device

    def savePassword(self, password):
        self.__password = password or None
