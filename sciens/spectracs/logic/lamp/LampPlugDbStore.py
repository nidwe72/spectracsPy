from sciens.spectracs.logic.lamp.LampDevice import LampDevice
from sciens.spectracs.model.databaseEntity.DbBase import save_session
from sciens.spectracs.model.databaseEntity.application.LampPlug import LampPlug


class LampPlugDbStore:
    # LampPlugStore on the app DB (SPEC_lamp_switch.md §6): ONE LampPlug row PER PLUG (MAC) this PC has seen —
    # SPEC_shelly_instrument_memory.md §11, R33: a PC near two instruments must not forget the first plug's password
    # when it meets the second. The same MAC only updates host / model / id (DHCP may move it). Short-lived sessions,
    # like the workflow persistence: nothing else in the app can be flushed along.

    def load(self, deviceId=None, mac=None):
        """-> (LampDevice | None, password | None): the row with that device id or MAC, else (no key) the first."""
        session = save_session()
        try:
            query = session.query(LampPlug)
            if deviceId is not None:
                query = query.filter(LampPlug.deviceId == deviceId)
            elif mac is not None:
                query = query.filter(LampPlug.mac == LampDevice("", "", mac).mac)
            row = query.first()
            return (self.__device(row), row.password) if row is not None else (None, None)
        finally:
            session.close()

    def loadAll(self):
        session = save_session()
        try:
            return [(self.__device(row), row.password) for row in session.query(LampPlug).all()]
        finally:
            session.close()

    def saveDevice(self, device):
        session = save_session()
        try:
            row = session.query(LampPlug).filter(LampPlug.mac == device.mac).first()
            if row is None:
                row = LampPlug(mac=device.mac)
                session.add(row)
            row.driverName = device.driverName
            row.host = device.host
            row.model = device.model
            row.deviceId = device.deviceId
            session.commit()
        finally:
            session.close()

    def savePassword(self, password, mac=None):
        """The password of the plug with `mac` (else the first row); None clears it = the default (the MAC) again."""
        session = save_session()
        try:
            query = session.query(LampPlug)
            if mac is not None:
                query = query.filter(LampPlug.mac == LampDevice("", "", mac).mac)
            row = query.first()
            if row is not None:
                row.password = password or None
                session.commit()
        finally:
            session.close()

    @staticmethod
    def __device(row):
        return LampDevice(row.driverName, row.host, row.mac, model=row.model, deviceId=row.deviceId)
