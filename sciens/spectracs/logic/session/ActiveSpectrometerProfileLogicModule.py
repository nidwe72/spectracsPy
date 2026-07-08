from sciens.spectracs.controller.application.ApplicationContextLogicModule import ApplicationContextLogicModule
from sciens.spectracs.logic.model.util.SpectrometerProfileUtil import SpectrometerProfileUtil
from sciens.spectracs.logic.model.util.SpectrometerUtil import SpectrometerUtil
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerProfile import SpectrometerProfile

# ROI + pixel->nm coefficient fields carried in the instrument bundle's `calibration` dict.
_CAL_FIELDS = ("regionOfInterestX1", "regionOfInterestY1", "regionOfInterestX2", "regionOfInterestY2",
               "interpolationCoefficientA", "interpolationCoefficientB",
               "interpolationCoefficientC", "interpolationCoefficientD")


class ActiveSpectrometerProfileLogicModule:
    """Install the logged-in user's calibrated SpectrometerProfile into the in-memory ApplicationSettings,
    so views that read getSpectrometerProfile() (the dev measurement bench, extraction) see the calibration
    the user actually owns.

    SPEC_dev_measure_bench §11. IMPORTANT: it re-fetches through the SERVER RPC (resolveInstrumentBySerial),
    NOT an in-process DB read — because a calibration authored via SpectrometerSetup Save is written by the
    SERVER process; an in-process session could return a stale cached row. Call it at login AND whenever a
    view needs the *current* calibration (e.g. the bench on open, after the user just calibrated)."""

    def installFromSession(self) -> bool:
        serial = CurrentUserSession().getRegisteredSerial()
        if not serial:
            return False
        bundle = SpectracsPyServerClient().resolveInstrumentBySerial(serial)
        if not bundle or not bundle.get("ok"):
            return False
        profile = self.__buildProfile(serial, bundle)
        ApplicationContextLogicModule().getApplicationSettings().setSpectrometerProfile(profile)
        return True

    def __buildProfile(self, serial, bundle) -> SpectrometerProfile:
        # Mirrors SpectrometerSetupViewModule.__buildModelFromDto: resolve the device, then fill the
        # calibration profile from the bundle's coefficients (fresh from the server that wrote them).
        profile = SpectrometerProfile()
        SpectrometerProfileUtil().initializeSpectrometerProfile(profile)
        profile.serial = serial

        spectrometer = self.__findSpectrometerByDevice(bundle.get("deviceCodeName"))
        if spectrometer is not None:
            profile.spectrometer = spectrometer

        calibration = bundle.get("calibration")
        if calibration:
            cal = profile.spectrometerCalibrationProfile
            for field in _CAL_FIELDS:
                value = calibration.get(field)
                if value is not None:
                    setattr(cal, field, value)
        return profile

    def __findSpectrometerByDevice(self, deviceCodeName):
        if not deviceCodeName:
            return None
        for spectrometer in SpectrometerUtil().getSpectrometers().values():
            sensor = spectrometer.spectrometerSensor
            if sensor is not None and sensor.codeName == deviceCodeName:
                return spectrometer
        return None
