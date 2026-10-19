"""
S1b of SPEC_shelly_instrument_memory.md (R12): the app refuses a server whose DB was migrated by newer code.
The client's login is driven with a fake proxy, so no server runs.
"""
import unittest

import sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient as clientModule
from sciens.spectracs.logic.server.ServerCompatibility import ServerCompatibility
from sciens.spectracs.logic.user.LoginLogicModule import LoginLogicModule
from sciens.spectracs.model.databaseEntity.DatabaseInitializer import getServerScriptHead, getServerScriptRevisions


class _FakeProxy:
    def __init__(self, revision):
        self.revision = revision

    def login(self, username, password):
        return {"ok": True, "userId": "u1", "username": username, "roles": [], "serverSchemaRevision": self.revision,
                "message": None}


class ServerCompatibilityTest(unittest.TestCase):

    def setUp(self):
        self.originalGetProxy = clientModule.SpectracsPyServerClient.getProxy

    def tearDown(self):
        clientModule.SpectracsPyServerClient.getProxy = self.originalGetProxy

    def __loginAgainst(self, revision):
        clientModule.SpectracsPyServerClient.getProxy = lambda self: _FakeProxy(revision)
        return clientModule.SpectracsPyServerClient().login("u", "p")

    def test_the_tree_knows_its_head(self):
        self.assertIn(getServerScriptHead(), getServerScriptRevisions())

    def test_known_revision_logs_in(self):
        self.assertTrue(self.__loginAgainst(getServerScriptHead())["ok"])

    def test_old_server_without_revision_logs_in(self):
        self.assertTrue(self.__loginAgainst(None)["ok"])

    def test_newer_server_is_refused(self):
        result = self.__loginAgainst("ffffffffffff")
        self.assertFalse(result["ok"])
        self.assertEqual(ServerCompatibility.NEWER_SERVER, result["message"])

    def test_server_login_reports_a_revision_key(self):
        result = LoginLogicModule().login("nobody-here", "x")
        self.assertIn("serverSchemaRevision", result)


if __name__ == "__main__":
    unittest.main()
