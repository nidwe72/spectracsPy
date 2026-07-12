"""P4 — pumpkin measurement wizard, virtual (SPEC_doc_automation §7.2).

The no-hardware seam-validation scenario AND the template for every other chapter. Drives WizardViewModule
through the pumpkin plugin's ACQUISITION (Reference | Sample) -> EVALUATION on the virtual device, so it
exercises nav + click + a tab switch + a gated Next -> without a camera.

Prereq: the session must be logged in as a user with the pumpkin plugin configured
(getPluginCodeRef() non-empty), else the wizard shows "No plugin configured for this user."

Run:  python automation/scenarios/pumpkin_wizard.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from automation.automation_director import main

TITLE = "Measuring a sample (pumpkin oil)"


def run(d):
    d.launch_app()
    d.nav("WizardViewModule")                                   # menu entry is a QAction -> use nav
    d.set_hint("Step 1 — Measure the reference.")
    d.prompt("The Director will run the pumpkin-oil measurement. Click CONTINUE to start.")
    d.wait_for_human("Click CONTINUE to begin.")               # demo gate (no hardware beat here)

    d.click("WizardViewModule.measureButton.reference")        # engine virtual capture -> reference spectrum
    d.screenshot("wizard_01_reference")

    d.set_hint("Step 2 — Measure the sample.")
    d.click("WizardViewModule.tabWidget", tab=1)               # switch to the Sample tab (header rect)
    d.click("WizardViewModule.measureButton.sample")           # -> sample spectrum
    d.screenshot("wizard_02_sample")

    d.set_hint("Computing transmission / absorbance and the pumpkin-oil evaluation…")
    d.wait_ready("WizardViewModule.nextButton", enabled=True)  # Next enables only when both measured
    d.click("WizardViewModule.nextButton")                     # ACQUISITION -> EVALUATION
    d.screenshot("wizard_03_evaluation")

    d.set_hint("Result ready.")


if __name__ == "__main__":
    main(run, title=TITLE)
