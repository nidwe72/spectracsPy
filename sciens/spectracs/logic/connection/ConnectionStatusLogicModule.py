from sciens.spectracs.logic.model.util.spectrometerSensor.ApplicationSpectrometerUtil import ApplicationSpectrometerUtil
from sciens.spectracs.logic.model.util.spectrometerSensor.SpectrometerSensorUtil import SpectrometerSensorUtil
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession


class ConnectionStatusLogicModule:
    """Connection status of the CURRENT user's instrument (SPEC_connection_and_calibration_ux.md §4.4).

    Targeted (not enumerate-and-match): the logged-in user's serial bundle names the device (code-name),
    so we check just that one. Virtual = always connected (software). Real = USB presence via VID/PID.
    'Present != capturable' (the RC-R0 resolver) is a 5b concern; here we only report presence.
    """

    NO_INSTRUMENT = "no_instrument"
    CONNECTED = "connected"
    NOT_CONNECTED = "not_connected"

    def getStatus(self) -> str:
        try:
            deviceCodeName = CurrentUserSession().getSpectrometerDevice()
            if not deviceCodeName:
                return self.NO_INSTRUMENT
            sensor = SpectrometerSensorUtil().getSensorByCodeName(deviceCodeName)
            if sensor is None:
                return self.NO_INSTRUMENT
            if sensor.isVirtual:
                return self.CONNECTED
            return self.CONNECTED if ApplicationSpectrometerUtil().isSensorConnected(sensor) else self.NOT_CONNECTED
        except Exception as exception:
            print("ConnectionStatusLogicModule.getStatus failed: %s" % exception)
            return self.NO_INSTRUMENT

    def getLabel(self) -> str:
        status = self.getStatus()
        if status == self.CONNECTED:
            deviceCodeName = CurrentUserSession().getSpectrometerDevice()
            return "Spectrometer: ● connected (%s)" % deviceCodeName
        if status == self.NOT_CONNECTED:
            return "Spectrometer: ○ not connected"
        return "Spectrometer: no instrument registered"
