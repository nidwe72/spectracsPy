import sys

from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerSensor import SpectrometerSensor

# Set once pyusb reports NoBackendError (no libusb DLL on Windows, SPEC_windows_build.md B6/U4): pyusb retries
# every backend on every find() and, frozen, logs a traceback each time — so after the first miss we stop asking.
_usbBackendMissing = False


class ApplicationSpectrometerUtil:

    def isSensorConnected(self, spectrometerSensor: SpectrometerSensor):
        global _usbBackendMissing
        # Parse outside the guard: a malformed VID/PID is a data bug and must stay loud (U5).
        vendorId = int('0x' + spectrometerSensor.vendorId, base=16)
        modelId = int('0x' + spectrometerSensor.modelId, base=16)
        if sys.platform == "win32":
            # Windows asks the camera enumeration, not the USB bus (SPEC_windows_build.md §6.1, W1.2): the same
            # lookup that gives the capture index, and no libusb DLL needed.
            from sciens.spectracs.logic.application.video.capture.SensorCaptureIndexResolver import \
                SensorCaptureIndexResolver
            return SensorCaptureIndexResolver().isPresent(spectrometerSensor)
        if _usbBackendMissing:
            return False

        # pyusb/libusb is desktop-only (deferred on Android) and has no backend on Windows. Any failure to ask
        # the bus means "not connected" — the setup screen calls this for every spectrometer (R3).
        try:
            import usb.core
            dev = usb.core.find(idVendor=vendorId, idProduct=modelId)
        except ImportError:
            return False
        except Exception as exception:
            if type(exception).__name__ == "NoBackendError":
                _usbBackendMissing = True
            print("ApplicationSpectrometerUtil.isSensorConnected: USB unavailable (%s: %s) - sensor absent"
                  % (type(exception).__name__, exception))
            return False

        return dev is not None
