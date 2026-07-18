"""B4 (SPEC_plugin_distribution.md §8) — the master-side publish helper: derive title/className/targetSdk by
importing the picked source, and enforce the one-self-contained-module lint (Q1) + the codeRef↔class rule
(D-coderef). Pure — no DB, no key, no server.

Run from the spectracsPy repo root:
    PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python -m pytest tests/test_plugin_publish.py -q
"""
import unittest

from sciens.spectracs.logic.spectral.plugin.PluginPublishUtil import (
    inspectPluginSource, codeRefMatchesClass, PluginSourceError)

_GOOD = (
    "import math\n"
    "from sciens.spectracs.plugin_sdk import SpectralPlugin\n"
    "class MyPlugin(SpectralPlugin):\n"
    "    title = 'My QM'\n"
    "    targetSdkVersion = 1\n"
    "    def evaluation(self, workflow):\n"
    "        return math.pi\n"
)


class InspectPluginSourceTest(unittest.TestCase):

    def test_derives_class_title_and_sdk(self):
        derived = inspectPluginSource(_GOOD)
        self.assertEqual(derived["className"], "MyPlugin")
        self.assertEqual(derived["title"], "My QM")
        self.assertEqual(derived["targetSdkVersion"], 1)

    def test_default_target_sdk_when_unset(self):
        source = _GOOD.replace("    targetSdkVersion = 1\n", "")
        self.assertIsNotNone(inspectPluginSource(source)["targetSdkVersion"])  # inherits SDK_VERSION

    def test_rejects_sibling_app_import(self):
        bad = _GOOD.replace("import math\n",
                            "from sciens.spectracs.logic.session.CurrentUserSession import CurrentUserSession\n")
        with self.assertRaises(PluginSourceError):
            inspectPluginSource(bad)

    def test_rejects_relative_import(self):
        bad = _GOOD.replace("import math\n", "from . import sibling\n")
        with self.assertRaises(PluginSourceError):
            inspectPluginSource(bad)

    def test_allows_plugin_sdk_and_stdlib_and_thirdparty(self):
        ok = ("import numpy\n"
              "from sciens.spectracs.plugin_sdk import SpectralPlugin\n"
              "class P(SpectralPlugin):\n"
              "    title = 't'\n")
        # numpy is on the venv path; the point is the lint does NOT reject it.
        self.assertEqual(inspectPluginSource(ok)["className"], "P")

    def test_rejects_multiple_plugin_classes(self):
        bad = _GOOD + ("class Other(SpectralPlugin):\n    title = 'x'\n")
        with self.assertRaises(PluginSourceError):
            inspectPluginSource(bad)

    def test_rejects_no_plugin_class(self):
        with self.assertRaises(PluginSourceError):
            inspectPluginSource("x = 1\n")

    def test_rejects_missing_title(self):
        bad = _GOOD.replace("    title = 'My QM'\n", "")
        with self.assertRaises(PluginSourceError):
            inspectPluginSource(bad)


class CodeRefMatchTest(unittest.TestCase):

    def test_tail_must_equal_class_name(self):
        self.assertTrue(codeRefMatchesClass("a.b.MyPlugin.MyPlugin", "MyPlugin"))
        self.assertFalse(codeRefMatchesClass("a.b.MyPlugin.MyPluginn", "MyPlugin"))
        self.assertFalse(codeRefMatchesClass("", "MyPlugin"))


if __name__ == "__main__":
    unittest.main()
