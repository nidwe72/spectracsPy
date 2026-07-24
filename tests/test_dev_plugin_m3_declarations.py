# M3 unit test: the DEV plugin's should-be declarations (SPEC_simplified_plugin_navigation.md M3), and that the
# temporary SIMPLIFIED_NAVIGATION toggle flips them all back to the as-is behaviour.

import unittest

from sciens.spectracs.model.spectral.SpectralWorkflow import SpectralWorkflow
from sciens.spectracs.model.spectral.SpectralWorkflowPhase import SpectralWorkflowPhase
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType as P
from sciens.spectracs.plugin_sdk.policy.NavigationMode import NavigationMode
from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin


def _acquisitionSteps(plugin):
    workflow = SpectralWorkflow()
    for phaseType in (P.ACQUISITION,):
        phase = SpectralWorkflowPhase()
        phase.setType(phaseType)
        workflow.addToPhases(phase)
    plugin.acquisition(workflow)
    return list(workflow.getPhase(P.ACQUISITION).getSteps().values())


class DevPluginM3DeclarationsTest(unittest.TestCase):

    def test_should_be_policy_auto_advance_with_acquisition_step_chevrons(self):
        nav = DevSpectralPlugin().policy().getNavigation()
        self.assertEqual(nav.getMode(), NavigationMode.AUTO_ADVANCE)
        self.assertTrue(nav.expandsSteps(P.ACQUISITION))
        self.assertFalse(nav.expandsSteps(P.PROCESSING))

    def test_metadata_three_fields(self):
        fields = DevSpectralPlugin().metadata(None)
        self.assertEqual([f.name for f in fields], ["title", "temperature", "dateOfRoasting"])
        self.assertTrue([f for f in fields if f.name == "title"][0].showInWorkflowsTable)

    def test_cropped_preview_on_acquisition_captureviews(self):
        steps = _acquisitionSteps(DevSpectralPlugin())
        self.assertEqual(len(steps), 2)
        self.assertTrue(all(step.getView().croppedPreview for step in steps))

    def test_toggle_off_restores_as_is(self):
        plugin = DevSpectralPlugin()
        plugin.SIMPLIFIED_NAVIGATION = False   # temporary regression toggle
        nav = plugin.policy().getNavigation()
        self.assertEqual(nav.getMode(), NavigationMode.STEP)
        self.assertFalse(nav.expandsSteps(P.ACQUISITION))
        self.assertFalse(any(step.getView().croppedPreview for step in _acquisitionSteps(plugin)))
        # METADATA is a permanent phase regardless of the toggle
        self.assertEqual(len(plugin.metadata(None)), 3)


if __name__ == "__main__":
    unittest.main()
