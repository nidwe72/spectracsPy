from sciens.spectracs.logic.lamp.LampDevice import LampDevice
from sciens.spectracs.model.databaseEntity.DbBase import save_session
from sciens.spectracs.model.databaseEntity.application.LampPlug import LampPlug


class LampPlugDbStore:
    # LampPlugStore on the app DB (SPEC_lamp_switch.md §6): ONE LampPlug row, the plug in use. A different MAC
    # replaces it (and drops the old password); the same MAC only updates host / model (DHCP may move it).
    # Short-lived sessions, like the workflow persistence: nothing else in the app can be flushed along.

    def load(self):
        session = save_session()
        try:
            row = session.query(LampPlug).first()
            if row is None:
                return None, None
            device = LampDevice(row.driverName, row.host, row.mac, model=row.model, deviceId=row.deviceId)
            return device, row.password
        finally:
            session.close()

    def saveDevice(self, device):
        session = save_session()
        try:
            row = session.query(LampPlug).filter(LampPlug.mac == device.mac).first()
            if row is None:
                session.query(LampPlug).delete()
                row = LampPlug(mac=device.mac)
                session.add(row)
            row.driverName = device.driverName
            row.host = device.host
            row.model = device.model
            row.deviceId = device.deviceId
            session.commit()
        finally:
            session.close()

    def savePassword(self, password):
        session = save_session()
        try:
            row = session.query(LampPlug).first()
            if row is not None:
                row.password = password or None
                session.commit()
        finally:
            session.close()
