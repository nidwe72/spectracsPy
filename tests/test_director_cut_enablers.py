# SPEC_director_cut.md E2 + E4 — the doc-mode pointing enablers, offscreen.
# E2: QtWorkflowRenderer stamps a stable "workflowItem.<slug>" objectName on the gauge + each metric row so the
#     Director can glide the cursor to an individual field.
# E4: DocModeUdpService.resolveByObjectName prefers the VISIBLE match among duplicate objectNames (the colour
#     chips are duplicated across the Metrics / Metrics (dev) tabs), regardless of tree order.

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QWidget

from sciens.spectracs.view.spectral.workflow.render.QtWorkflowRenderer import (
    QtWorkflowRenderer, workflowItemObjectName)
from sciens.spectracs.model.spectral.plugin.view.MetricFieldView import MetricFieldView
from sciens.spectracs.logic.application.docmode.DocModeUdpService import resolveByObjectName


class DirectorCutEnablersTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    # --- E2: the slug rule (shared contract with the scenario) ---

    def test_slug_rule_matches_the_scenario_object_names(self):
        self.assertEqual(workflowItemObjectName("Verdict"), "workflowItem.verdict")
        self.assertEqual(workflowItemObjectName("Soret · 448–460 nm"), "workflowItem.soret_448_460_nm")
        self.assertEqual(workflowItemObjectName("Q · 560–580 nm"), "workflowItem.q_560_580_nm")
        self.assertEqual(workflowItemObjectName("Intrinsic · despiked"), "workflowItem.intrinsic_despiked")
        self.assertEqual(workflowItemObjectName("Intrinsic-perceived · despiked"),
                         "workflowItem.intrinsic_perceived_despiked")
        self.assertEqual(workflowItemObjectName("Pigment ratio"), "workflowItem.pigment_ratio")

    # --- E2: the renderer stamps the objectName on the pointable widget ---

    def test_metric_row_label_gets_the_objectname(self):
        widget = QtWorkflowRenderer().render([MetricFieldView("Soret · 448–460 nm", value="0.5")])
        self.assertIsNotNone(widget.findChild(QWidget, "workflowItem.soret_448_460_nm"))

    def test_gauge_gets_the_verdict_objectname(self):
        from sciens.spectracs.plugins.dev.RoastGaugeView import RoastGaugeView
        from sciens.spectracs.model.spectral.plugin.view.GaugeRender import GaugeRender
        gauge = RoastGaugeView(3.0, render=GaugeRender.BAND | GaugeRender.LABEL | GaugeRender.SWATCH)
        widget = QtWorkflowRenderer().render([gauge])
        self.assertIsNotNone(widget.findChild(QWidget, "workflowItem.verdict"))

    # --- E4: visible-preferring lookup across duplicate objectNames ---

    def test_resolve_prefers_the_visible_twin_regardless_of_tree_order(self):
        parent = QWidget()
        # The HIDDEN twin is added FIRST (earlier in tree order) — a plain findChild would return it.
        hiddenHolder = QWidget(parent)
        hiddenTwin = QWidget(hiddenHolder)
        hiddenTwin.setObjectName("dup")
        visibleTwin = QWidget(parent)
        visibleTwin.setObjectName("dup")
        parent.show()
        hiddenHolder.hide()   # hides hiddenTwin (isVisible() -> False)
        self.assertFalse(hiddenTwin.isVisible())
        self.assertTrue(visibleTwin.isVisible())
        self.assertIs(resolveByObjectName((parent,), "dup"), visibleTwin)

    def test_resolve_falls_back_to_the_only_match_when_all_hidden(self):
        parent = QWidget()
        only = QWidget(parent)
        only.setObjectName("solo")
        # parent never shown -> `only` is not visible; the fallback still returns it (for the hidden-diagnostic).
        self.assertIs(resolveByObjectName((parent,), "solo"), only)

    def test_resolve_returns_none_for_unknown_name(self):
        self.assertIsNone(resolveByObjectName((QWidget(),), "nope"))


if __name__ == "__main__":
    unittest.main()
