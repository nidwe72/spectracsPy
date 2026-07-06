from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerSensor import SpectrometerSensor


class ApplicationSpectrometerUtil:

    def isSensorConnected(self, spectrometerSensor: SpectrometerSensor):
        # pyusb/libusb is desktop-only (deferred on Android). Import lazily so this module stays
        # importable without pyusb; if it is unavailable, treat the sensor as not connected.
        try:
            import usb.core
        except ImportError:
            return False

        dev = usb.core.find(idVendor=int('0x' + spectrometerSensor.vendorId, base=16),
                            idProduct=int('0x' + spectrometerSensor.modelId, base=16))

        return dev is not None
