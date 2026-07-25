# T1 (SPEC_simplified_plugin_navigation.md §7b/§7c): the TabGroupView container view-model round-trips through
# the ViewModelFactory, recursing into its children — nested capture descriptors survive (no pixels, exactly as
# at top level), and an EvaluationResult holding a group reloads faithfully.

import unittest

from sciens.spectracs.model.spectral.plugin.view.EvaluationResult import EvaluationResult
from sciens.spectracs.model.spectral.plugin.view.SpectrumCaptureView import SpectrumCaptureView
from sciens.spectracs.model.spectral.plugin.view.TabGroupView import TabGroupView
from sciens.spectracs.model.spectral.plugin.view.ViewModelFactory import ViewModelFactory


class TabGroupViewTest(unittest.TestCase):

    def __group(self):
        return (TabGroupView()
                .addTab("Full frame", SpectrumCaptureView(caption="whole", cropped=False, roiOverlay=True))
                .addTab("Cropped ROI", SpectrumCaptureView(caption="roi", cropped=True)))

    def test_round_trips_through_factory_with_nested_children(self):
        restored = ViewModelFactory.fromJson(self.__group().toJson())
        self.assertIsInstance(restored, TabGroupView)
        self.assertEqual([label for label, _ in restored.tabs], ["Full frame", "Cropped ROI"])
        children = restored.children()
        self.assertTrue(all(isinstance(child, SpectrumCaptureView) for child in children))
        self.assertEqual([(c.cropped, c.roiOverlay) for c in children], [(False, True), (True, False)])
        self.assertEqual([c.caption for c in children], ["whole", "roi"])

    def test_shown_in_report_flag_round_trips(self):
        group = self.__group().setShownInReport(True)
        self.assertTrue(ViewModelFactory.fromJson(group.toJson()).isShownInReport)

    def test_group_inside_evaluation_result_reloads(self):
        result = EvaluationResult()
        result.addItem(self.__group())
        result.syncToColumn()
        reloaded = EvaluationResult()
        reloaded.resultJson = result.resultJson
        items = reloaded.getItems()
        self.assertEqual(len(items), 1)
        self.assertIsInstance(items[0], TabGroupView)
        self.assertEqual(len(items[0].children()), 2)


if __name__ == "__main__":
    unittest.main()
