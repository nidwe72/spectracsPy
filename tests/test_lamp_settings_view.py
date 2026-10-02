"""
P6 of SPEC_lamp_switch.md — Settings → Lamp plug (§6, §16 U12) and the unconfigured-plug hint (§15.5), offscreen,
against a FakeShellyServer and an unthreaded LampService.

    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest tests/test_lamp_settings_view.py -q
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from fakes.FakeShellyServer import FakeClock, FakeShellyServer
from sciens.spectracs.logic.lamp.LampDiscovery import LampDiscovery
from sciens.spectracs.logic.lamp.LampPlugStore import LampPlugStore
from sciens.spectracs.logic.lamp.LampService import LampService
from sciens.spectracs.logic.lamp.LampState import LampState
from sciens.spectracs.view.settings.lamp.LampSettingsViewModule import LampSettingsViewModule


class LampSettingsViewTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def startService(self, plug, wifi=()):
        LampService.instance = None
        discovery = LampDiscovery(mdnsBrowse=lambda types, seconds: [plug.host], subnetHosts=lambda: [],
                                  probeTimeout=0.5)
        service = LampService(clock=FakeClock(), threaded=False, discovery=discovery, plugStore=LampPlugStore(),
                              wifiScan=lambda: list(wifi))
        service.TEST_ON_MS = 0
        service.configure(True)
        return service

    def tearDown(self):
        if LampService.instance is not None:
            LampService.instance.shutdown()
        LampService.instance = None

    def page(self):
        page = LampSettingsViewModule()
        page.initialize()
        page.show()
        return page

    def settle(self):
        for _ in range(5):
            QCoreApplication.processEvents()

    def test_shows_the_plug_and_tests_it(self):
        with FakeShellyServer() as plug:
            self.startService(plug)
            page = self.page()
            self.assertIn("E8:6B:EA:E3:CB:60", page.plugValue.text())
            self.assertIn("reachable", page.stateValue.text())
            page.onClickedTest()
            self.settle()
            self.assertEqual("On 2 s · 11.2 W ✓", page.resultLabel.text())
            self.assertFalse(plug.output)                      # the pulse switched off again

    def test_test_reports_no_power(self):
        with FakeShellyServer(apower=0.0) as plug:
            self.startService(plug)
            page = self.page()
            page.onClickedTest()
            self.settle()
            self.assertIn("check the switch on the lamp socket", page.resultLabel.text())

    def test_password_needed_then_saved(self):
        with FakeShellyServer(password="geheim") as plug:
            service = self.startService(plug)
            page = self.page()
            self.assertIn("needs a password", page.stateValue.text())
            page.passwordEdit.setText("geheim")
            page.onClickedSave()
            self.assertEqual(LampState.OFF, service.state)
            self.assertIn("reachable", page.stateValue.text())
            self.assertEqual("", page.passwordEdit.text())     # never left on screen

    def test_wrong_password_is_found_at_once(self):
        with FakeShellyServer(password="geheim") as plug:
            service = self.startService(plug)
            page = self.page()
            page.passwordEdit.setText("falsch")
            page.onClickedSave()
            self.assertTrue(service.needsPassword)
            self.assertIn("needs a password", page.stateValue.text())

    def test_unconfigured_shelly_hint(self):
        with FakeShellyServer() as plug:
            self.startService(plug, wifi=[("ShellyPlusPlugS-0123456789AB", ""), ("ShellyPlusPlugS-E86BEAE3CB60", "")])
            page = self.page()
            self.assertIn("ShellyPlusPlugS-0123456789AB", page.hintLabel.text())
            self.assertNotIn("E86BEAE3CB60", page.hintLabel.text())
            self.assertIn("http://192.168.33.1", page.hintLabel.text())

    def test_without_a_lamp(self):
        page = self.page()
        self.assertIn("real spectrometer", page.plugValue.text())
        self.assertFalse(page.testButton.isEnabled())


if __name__ == "__main__":
    unittest.main()
