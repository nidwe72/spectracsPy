# T2 (SPEC_simplified_plugin_navigation.md §7b/§7c): visitTabGroup across BOTH render targets — Qt draws a
# QTabWidget with one sub-tab per child; matplotlib stacks the children under their tab headings (paper has no
# tabs). Offscreen-testable — no camera, no pixels needed (a capture with .image=None renders its caption).

import os
import unittest

from sciens.spectracs.model.spectral.plugin.view.SpectrumCaptureView import SpectrumCaptureView
from sciens.spectracs.model.spectral.plugin.view.SpectrumPlotView import SpectrumPlotView
from sciens.spectracs.model.spectral.plugin.view.TabGroupView import TabGroupView


def _group():
    return (TabGroupView()
            .addTab("Full frame", SpectrumCaptureView(caption="whole", cropped=False, roiOverlay=True))
            .addTab("Cropped ROI", SpectrumCaptureView(caption="roi", cropped=True)))


class TabGroupRenderTest(unittest.TestCase):

    def test_qt_renders_group_as_a_tab_widget_with_a_sub_tab_per_child(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QTabWidget
        from sciens.spectracs.view.spectral.workflow.render.QtWorkflowRenderer import QtWorkflowRenderer
        QApplication.instance() or QApplication([])
        widget = QtWorkflowRenderer().render([_group()])
        tabWidgets = widget.findChildren(QTabWidget)
        self.assertEqual(len(tabWidgets), 1)
        subTabs = tabWidgets[0]
        self.assertEqual([subTabs.tabText(i) for i in range(subTabs.count())], ["Full frame", "Cropped ROI"])

    def test_qt_group_mixes_child_view_model_types(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from sciens.spectracs.view.spectral.workflow.render.QtWorkflowRenderer import QtWorkflowRenderer
        QApplication.instance() or QApplication([])
        group = TabGroupView().addTab("Image", SpectrumCaptureView(caption="x")) \
                              .addTab("Plot", SpectrumPlotView(title="y"))
        self.assertIsNotNone(QtWorkflowRenderer().render([group]))   # renders both child types without error

    def test_matplotlib_stacks_group_children_under_headings(self):
        # ⛔ THIS ASSERTION USED TO BE `assertTrue(figures)` — which a page carrying nothing but its header
        # also satisfies, so it could not fail before OR after D1 (SPEC_settled_measurement.md §27.14/W8).
        # ⇒ it now asserts what was actually DRAWN.
        from sciens.spectracs.logic.spectral.report.MatplotlibWorkflowRenderer import MatplotlibWorkflowRenderer
        from sciens.spectracs.model.spectral.plugin.view.ReportView import ReportView
        group = _group()
        for child in group.children():
            child.setShownInReport(True)
        group.setShownInReport(True)
        figures = MatplotlibWorkflowRenderer().render(ReportView("test"), [("Acquisition", [group])])
        drawn = [text.get_text() for text in figures[0].texts]
        self.assertIn("Full frame", drawn)
        self.assertIn("Cropped ROI", drawn)
        self.assertIn("whole", drawn)          # the caption stands in for a capture with no pixels

    def test_matplotlib_prints_only_the_children_flagged_for_the_report(self):
        # ⭐⭐ D1 (§27.13b): `isShownInReport` is the canonical say-so and a tab group is not an exception.
        # Measured before the fix: a settling group put its summary AND all three curves AND both diagnostic
        # tables on paper — three pages where §18.8 promised the summary alone.
        from sciens.spectracs.logic.spectral.report.MatplotlibWorkflowRenderer import MatplotlibWorkflowRenderer
        from sciens.spectracs.model.spectral.plugin.view.ReportView import ReportView
        group = _group().setShownInReport(True)
        group.tabs[0][1].setShownInReport(True)        # "Full frame" opts in; "Cropped ROI" does not
        figures = MatplotlibWorkflowRenderer().render(ReportView("test"), [("Acquisition", [group])])
        drawn = [text.get_text() for text in figures[0].texts]
        self.assertIn("Full frame", drawn)
        self.assertNotIn("Cropped ROI", drawn, "an unflagged child was printed anyway")
        self.assertNotIn("roi", drawn)

    def test_an_unflagged_group_draws_nothing_at_all(self):
        from sciens.spectracs.logic.spectral.report.MatplotlibWorkflowRenderer import MatplotlibWorkflowRenderer
        from sciens.spectracs.model.spectral.plugin.view.ReportView import ReportView
        figures = MatplotlibWorkflowRenderer().render(ReportView("test"), [("Acquisition", [_group()])])
        drawn = [text.get_text() for text in figures[0].texts]
        self.assertNotIn("Full frame", drawn)

    def test_a_flagged_group_with_no_flagged_child_draws_no_orphan_heading(self):
        # ⚠ §27.14/W1 — the tab label used to be written BEFORE the children were dispatched, so filtering
        # in place would have replaced three curve pages with three bold headings over nothing.
        from sciens.spectracs.logic.spectral.report.MatplotlibWorkflowRenderer import MatplotlibWorkflowRenderer
        from sciens.spectracs.model.spectral.plugin.view.ReportView import ReportView
        figures = MatplotlibWorkflowRenderer().render(ReportView("test"),
                                                      [("Acquisition", [_group().setShownInReport(True)])])
        drawn = [text.get_text() for text in figures[0].texts]
        self.assertNotIn("Full frame", drawn)
        self.assertNotIn("Cropped ROI", drawn)

    def test_the_screen_ignores_the_report_flag_entirely(self):
        # ⛔ §27.14/W5 — ReportableView's contract is "the report includes only flagged items; the GUI
        # ignores the flag". An unflagged settling curve must still be a tab on the bench.
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication, QTabWidget
        from sciens.spectracs.view.spectral.workflow.render.QtWorkflowRenderer import QtWorkflowRenderer
        QApplication.instance() or QApplication([])
        widget = QtWorkflowRenderer().render([_group()])       # nothing flagged anywhere
        subTabs = widget.findChildren(QTabWidget)[0]
        self.assertEqual(["Full frame", "Cropped ROI"],
                         [subTabs.tabText(i) for i in range(subTabs.count())])


if __name__ == "__main__":
    unittest.main()
