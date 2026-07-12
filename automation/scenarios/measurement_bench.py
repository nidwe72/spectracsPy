"""P5 — dev measurement bench, first video sweep (SPEC_doc_automation §7.1).

The hero clip: the master's swiss-knife measuring a REAL sample end-to-end. Hardware-in-the-loop.

Prerequisites (the bench enforces them):
  * master session (masterUserExakta),
  * a REAL non-virtual spectrometer plugged DIRECT-to-USB (the bench refuses virtual devices),
  * a steady LIGHT SOURCE on the slit for both reference and sample.

Complete 8-beat flow: acquire reference (auto-expose -> capture -> reveal Spectrum) -> acquire sample ->
PROCESSING (raster/ROI) -> EVALUATION Metrics -> EVALUATION Report (preview only; native Save skipped) ->
PUBLISHING (Send to LIMS). Two human beats: insert reference, swap to sample.

Run:  python automation/scenarios/measurement_bench.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from automation.automation_director import main

TITLE = "The measurement bench — a real sample, end to end"

CAPTURE = "DevMeasurementBenchViewModule.captureButton"
ROLE_TABS = "DevMeasurementBenchViewModule.roleTabs"
INNER_TABS = "DevMeasurementBenchViewModule.innerTabs"
NEXT = "DevMeasurementBenchViewModule.nextButton"
SEND_LIMS = "DevMeasurementBenchViewModule.sendToLimsButton"
SPECTRUM_TAB = 1   # inner tabs: 0 = Captured image, 1 = Spectrum


def run(d):
    d.launch_app()   # attach mode: waits for the app bench.sh launched (or one you started)
    # Let the operator prepare the real session before we drive the bench. The bench needs a logged-in
    # master with a CALIBRATED real setup — it can't be synthesized, so this is a human beat.
    d.prompt("Prepare the app, then CONTINUE.")
    d.wait_for_human("In the app: log in as masterUserExakta and confirm a\n"
                     "CALIBRATED real spectrometer setup is active.\n"
                     "Then click CONTINUE.")
    d.nav("DevMeasurementBenchViewModule")                 # menu entry is a QAction -> use nav
    d.set_hint("The measurement bench — a real sample, end to end.")

    # Beat 1 — reference
    d.set_hint("Step 1 — Acquire the reference.")
    d.wait_for_human("Place the REFERENCE in the beam, illuminate the slit, then click CONTINUE.")
    d.click(CAPTURE)                                       # "Capture reference" (auto-exposes first)
    d.wait_ready(CAPTURE, enabled=True, timeout=60)        # capture/auto-expose loop finished
    d.click(INNER_TABS, tab=SPECTRUM_TAB)                  # reveal the extracted reference spectrum
    d.screenshot("bench_01_reference")

    # Beat 2 — sample
    d.set_hint("Step 2 — Acquire the sample.")
    d.click(ROLE_TABS, tab=1)                              # switch to the Sample tab (header rect)
    d.wait_for_human("Swap in the SAMPLE, then click CONTINUE.")
    d.click(CAPTURE)                                       # "Capture sample"
    d.wait_ready(CAPTURE, enabled=True, timeout=60)
    d.click(INNER_TABS, tab=SPECTRUM_TAB)                  # reveal the sample spectrum
    d.screenshot("bench_02_sample")
    d.wait_ready(NEXT, enabled=True)                       # Next enables only when both roles captured

    # Beat 3 — PROCESSING (raster / ROI view)
    d.set_hint("Processing — the captured region, ready for evaluation.")
    d.click(NEXT)                                          # ACQUISITION -> PROCESSING
    d.sleep(2)                                             # linger so the raster view reads on video
    d.screenshot("bench_03_processing")

    # Beat 4/5 — EVALUATION (Metrics, then Report preview)
    d.set_hint("Evaluation — transmission, absorbance and the pumpkin-oil metric.")
    d.click(NEXT)                                          # PROCESSING -> EVALUATION
    d.sleep(1)
    d.screenshot("bench_04_metrics")
    d.set_hint("A one-click PDF report of the whole run (preview).")
    d.sleep(2)                                             # show the Report preview; native Save is skipped
    d.screenshot("bench_05_report")

    # Beat 6 — PUBLISHING (Send to LIMS) — only if the plugin declares it
    d.set_hint("Publishing the sample to the lab (LIMS).")
    d.click(NEXT)                                          # EVALUATION -> PUBLISHING
    d.click(SEND_LIMS)
    d.sleep(2)
    d.screenshot("bench_06_published")

    d.set_hint("Done — a full bench measurement, start to finish.")


if __name__ == "__main__":
    main(run, title=TITLE)
