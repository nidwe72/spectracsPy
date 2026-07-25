# M3 unit test: the DEV plugin's should-be declarations (SPEC_simplified_plugin_navigation.md M3). The plugin
# drives should-be PERMANENTLY — the temporary SIMPLIFIED_NAVIGATION regression toggle was removed in phase X.

import unittest

from sciens.spectracs.model.spectral.SpectralWorkflow import SpectralWorkflow
from sciens.spectracs.model.spectral.SpectralWorkflowPhase import SpectralWorkflowPhase
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType as P
from sciens.spectracs.model.spectral.SpectraContainer import SpectraContainer
from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.model.spectral.plugin.view.SpectrumCaptureView import SpectrumCaptureView
from sciens.spectracs.model.spectral.plugin.view.TabGroupView import TabGroupView
from sciens.spectracs.plugin_sdk.roles import REFERENCE, SAMPLE
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

    def test_acquisition_report_captures_are_full_frame_and_cropped(self):
        # §7b: each acquisition step declares BOTH report captures — full frame (ROI border, roiOverlay) and
        # cropped-to-ROI — plus the extracted spectrum plot, all shownInReport.
        for step in _acquisitionSteps(DevSpectralPlugin()):
            captures = [item for item in step.getEvaluationResult().getItems()
                        if isinstance(item, SpectrumCaptureView)]
            self.assertEqual(len(captures), 2)
            self.assertEqual(sorted((c.cropped, c.roiOverlay) for c in captures),
                             [(False, True), (True, False)])   # full-frame-border + cropped
            self.assertTrue(all(c.isShownInReport for c in captures))

    def test_processing_declares_role_tagged_raster_steps(self):
        # Change G + T1/C1 (§7b): the Reference/Sample raster inspection views are PLUGIN-DECLARED, now grouped
        # into a TabGroupView (Full frame | Cropped ROI), role-tagged so the host can fill the nested pixels.
        wf = SpectralWorkflow()
        for pt in (P.ACQUISITION, P.PROCESSING, P.EVALUATION, P.METADATA, P.PUBLISHING):
            phase = SpectralWorkflowPhase(); phase.setType(pt); wf.addToPhases(phase)
        plugin = DevSpectralPlugin()
        plugin.acquisition(wf)
        for step in wf.getPhase(P.ACQUISITION).getSteps().values():
            spectrum = Spectrum()
            spectrum.setValuesByNanometers({nm: 100.0 for nm in range(440, 631, 2)})
            container = SpectraContainer(); container.addToSpectra(spectrum, step.getRole())
            step.setContainer(container)
        plugin.processing(wf)
        steps = list(wf.getPhase(P.PROCESSING).getSteps().values())
        rasters = {s.getRole(): s for s in steps if s.getRole() in (REFERENCE, SAMPLE)}
        self.assertEqual(set(rasters), {REFERENCE, SAMPLE})
        self.assertEqual([rasters[REFERENCE].getLabel(), rasters[SAMPLE].getLabel()],
                         ["Reference image", "Sample Image"])   # §7b rename "raster" -> "image"
        for role, step in rasters.items():
            items = step.getEvaluationResult().getItems()
            self.assertEqual(len(items), 1)
            group = items[0]
            self.assertIsInstance(group, TabGroupView)
            self.assertEqual([label for label, _ in group.tabs], ["Full frame", "Cropped ROI"])
            captures = group.children()
            self.assertTrue(all(isinstance(v, SpectrumCaptureView) for v in captures))
            self.assertEqual(sorted(v.cropped for v in captures), [False, True])  # full frame + cropped ROI

if __name__ == "__main__":
    unittest.main()
