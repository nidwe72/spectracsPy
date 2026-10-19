"""
SpectracsPyServerClient.syncSpectrometers matches the server's catalog by NATURAL key (vendorId, model, camera
codeName, styleId; chip vendor_product), not by id. The app's own get-or-create gives local rows their own uuids,
so matching by id duplicated every vendor/style/camera/chip/spectrometer (seen 2026-10-19).

NOTE: exercises the real app DB in appdata (like test_dynarex_instrument_seed); cleans up what it adds.
"""
import unittest
import uuid
from unittest import mock

from sciens.spectracs.logic.model.util.SpectrometerSensorChipUtil import SpectrometerSensorChipUtil
from sciens.spectracs.logic.model.util.SpectrometerStyleUtil import SpectrometerStyleUtil
from sciens.spectracs.logic.model.util.SpectrometerUtil import SpectrometerUtil
from sciens.spectracs.logic.model.util.SpectrometerVendorUtil import SpectrometerVendorUtil
from sciens.spectracs.logic.model.util.spectrometerSensor.SpectrometerSensorUtil import SpectrometerSensorUtil
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
from sciens.spectracs.model.databaseEntity.DbServerBase import server_session_factory
from sciens.spectracs.model.databaseEntity.spectral.device.Spectrometer import Spectrometer
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerSensor import SpectrometerSensor
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerSensorChip import SpectrometerSensorChip
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerStyle import SpectrometerStyle
from sciens.spectracs.model.databaseEntity.spectral.device.SpectrometerVendor import SpectrometerVendor


def counts():
    return (len(SpectrometerVendorUtil().getPersistentSpectrometerVendors()),
            len(SpectrometerStyleUtil().getPersistentSpectrometerStyles()),
            len(SpectrometerSensorUtil().getPersistedSpectrometerSensors()),
            len(SpectrometerSensorChipUtil().getPersistentSpectrometerSensorChips()),
            len(SpectrometerUtil().getPersistentSpectrometers()))


def serverCopy(local: Spectrometer, modelName: str = None) -> Spectrometer:
    """The same catalog entry as the server would send it: same natural keys, every id different."""
    chip = SpectrometerSensorChip()
    chip.id = str(uuid.uuid4())
    chip.vendorName = local.spectrometerSensor.spectrometerSensorChip.vendorName
    chip.productName = local.spectrometerSensor.spectrometerSensorChip.productName
    sensor = SpectrometerSensor()
    sensor.id = str(uuid.uuid4())
    for field in ("vendorId", "vendorName", "sellerName", "modelId", "description", "codeName", "isVirtual"):
        setattr(sensor, field, getattr(local.spectrometerSensor, field))
    sensor.spectrometerSensorChip = chip
    vendor = SpectrometerVendor()
    vendor.id = str(uuid.uuid4())
    vendor.vendorId = local.spectrometerVendor.vendorId
    vendor.vendorName = local.spectrometerVendor.vendorName
    style = SpectrometerStyle()
    style.id = str(uuid.uuid4())
    style.styleId = local.spectrometerStyle.styleId
    style.styleName = local.spectrometerStyle.styleName
    remote = Spectrometer()
    remote.id = str(uuid.uuid4())
    remote.modelName = modelName or local.modelName
    remote.spectrometerSensor = sensor
    remote.spectrometerVendor = vendor
    remote.spectrometerStyle = style
    return remote


class SyncSpectrometersTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        SpectrometerUtil().getSpectrometers()  # the app's get-or-create: the catalog exists locally

    def sync(self, remotes):
        proxy = mock.Mock()
        proxy.getSpectrometers.return_value = {remote.id: remote for remote in remotes}
        with mock.patch.object(SpectracsPyServerClient, "getProxy", return_value=proxy):
            SpectracsPyServerClient().syncSpectrometers()

    def test_known_catalog_with_other_ids_adds_nothing(self):
        before = counts()
        self.sync([serverCopy(s) for s in SpectrometerUtil().getSpectrometers().values()])
        self.assertEqual(before, counts())

    def test_new_spectrometer_reuses_local_parts(self):
        dynarex = next(s for s in SpectrometerUtil().getSpectrometers().values()
                       if s.spectrometerSensor.codeName == "Dynarex")
        remote = serverCopy(dynarex, modelName="SyncTestModel")
        vendors, styles, sensors, chips, spectrometers = counts()
        try:
            self.sync([remote])
            self.assertEqual((vendors, styles, sensors, chips, spectrometers + 1), counts())
            added = [s for s in SpectrometerUtil().getPersistentSpectrometers().values()
                     if s.modelName == "SyncTestModel"]
            self.assertEqual(1, len(added))
            self.assertEqual(dynarex.spectrometerSensor.id, added[0].spectrometerSensorId)
            self.assertEqual(dynarex.spectrometerStyle.id, added[0].spectrometerStyleId)
            self.assertEqual(dynarex.spectrometerVendor.id, added[0].spectrometerVendorId)
            self.sync([remote])  # a second sync adds nothing
            self.assertEqual(spectrometers + 1, counts()[4])
        finally:
            session = server_session_factory()
            for row in session.query(Spectrometer).filter(Spectrometer.modelName == "SyncTestModel").all():
                session.delete(row)
            session.commit()


if __name__ == "__main__":
    unittest.main()
