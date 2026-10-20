from sciens.spectracs.logic.lamp.LampAdmission import Admission


class FirstPlugAdmission:
    """For the lamp state-machine tests (no instrument copy on the fake plug): admit the first plug found with the
    password stored for it — the switching behaviour those tests are about, without SPEC_shelly_instrument_memory
    §11.3's registered-only rule, which test_lamp_admission.py covers on its own."""

    def __init__(self, store):
        self.store = store

    def admit(self, result, serial):
        device = result.chosen or (result.devices[0] if result.devices else None)
        if device is None:
            return Admission(reason="not found")
        password = self.store.load(mac=device.mac)[1]
        if device.authRequired and not password:
            return Admission(device, needsPassword=True, reason="locked")
        return Admission(device, password)
