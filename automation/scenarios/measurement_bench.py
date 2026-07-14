"""B5 — dev measurement bench, narrated first video sweep (SPEC_doc_automation §7.1 + §16).

The hero clip: the master's swiss-knife measuring a REAL sample end-to-end, narrated by the 3-zone doc panel
(use-case → phase outline → progressive-reveal captions). Hardware-in-the-loop.

POST-CONVERGENCE (2026-07-13): ACQUISITION runs through the shared CapturePanel, so the capture widgets are
addressed as `CapturePanel.*` (they moved off DevMeasurementBenchViewModule during the capture-panel
convergence — SPEC_doc_automation §16.0). Only nav/next/publish stay on the bench view.

Both narration layers show at once (§16.0 decision): the app's own status-bar coach line (terse imperative,
from the plugin CaptureView.prompt) + the doc panel (the narrated 'why', below). The NARRATION table is
authored to COMPLEMENT the coach line, never echo it.

Prerequisites (the bench enforces them):
  * master session (masterUserExakta) — scripted from director.ini [bench] if present, else a human gate,
  * a REAL non-virtual spectrometer plugged DIRECT-to-USB (the bench refuses virtual devices),
  * a steady LIGHT SOURCE on the slit for both reference and sample.

Run:  DOC_ATTACH=1 python automation/scenarios/measurement_bench.py    (or: automation/bench.sh)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from automation.automation_director import main

TITLE = "The measurement bench — a real sample, end to end"

# Post-convergence targets: the capture surface lives on the shared CapturePanel (§16.0 finding 2).
CAPTURE = "CapturePanel.captureButton"       # single button; label flips Reference/Sample by role-tab
ROLE_TABS = "CapturePanel.roleTabs"          # Reference | Sample (the SpectralWorkflowStep tabs)
INNER_TABS = "CapturePanel.innerTabs"        # Captured image | Spectrum
NEXT = "DevMeasurementBenchViewModule.nextButton"
SEND_LIMS = "DevMeasurementBenchViewModule.sendToLimsButton"
# Per-phase step-tab widgets — walked so EVERY step of each phase is clicked + described (Edwin).
PROCESSING_TABS = "DevMeasurementBenchViewModule.processingTabs"
EVAL_TABS = "DevMeasurementBenchViewModule.evaluationTabs"
PUBLISHING_TABS = "DevMeasurementBenchViewModule.publishingTabs"
SPECTRUM_TAB = 1   # inner tabs: 0 = Captured image, 1 = Spectrum
REFERENCE_TAB = 0  # role tabs: 0 = Reference, 1 = Sample
SAMPLE_TAB = 1
OUTLINE = ["Acquisition", "Processing", "Evaluation", "Publishing"]

# Every evaluation metric, in the grid order the Dev plugin emits them (DevSpectralPlugin) — Edwin: describe
# them ALL, including 'color'.
EVAL_METRICS = ["color", "Greenness G", "Pigment D_Q", "Browning A_blue",
                "Clarity A_green", "Browning ratio", "G' (alt.)"]

# Claude-authored narration — the 'why', a different register from the in-app coach line (§16.0).
NARRATION = {
    "useCase": "Measuring a real sample on the bench",
    "phase:Acquisition": "First we capture two spectra — a reference, then the sample itself.",
    # The 'blank' is the isopropanol solvent, NOT an empty beam (Edwin's correction 2026-07-14).
    "step:REFERENCE": "The reference — the blank — is the isopropanol solvent in its cuvette, with no oil "
                      "dissolved in it. It is our 100% baseline: everything the sample shows is measured "
                      "against it.",
    "step:SAMPLE": "The sample is the same isopropanol, now with the pumpkin-seed oil dissolved in it. The "
                   "difference between the two spectra is the whole measurement.",
    "phase:Processing": "The bench turns the two captures into transmission, and then absorbance, across the "
                        "visible band.",
    "phase:Evaluation": "From those curves the plugin computes the quality metrics and a perceived-colour "
                        "swatch — the numbers a lab actually reports. Let's read each one.",
    "phase:Publishing": "Finally the measurement and its PDF report are published to the lab's LIMS.",
    # every evaluation metric field (Edwin: describe them all)
    "metric:color": "Colour — the perceived colour of the sample under a daylight illuminant. A fresh oil "
                    "reads green; a browned one shifts toward red.",
    "metric:Greenness G": "Greenness G, the headline index — pigment depth divided by the green floor. "
                          "Higher means a greener, fresher oil.",
    "metric:Pigment D_Q": "Pigment D_Q — the depth of the green-pigment Q-band: how much intact green "
                          "pigment the oil still carries.",
    "metric:Browning A_blue": "Browning A_blue — absorption in the blue region, which rises with roasting "
                              "and Maillard browning.",
    "metric:Clarity A_green": "Clarity A_green — the green-window floor, which rises with turbidity or "
                              "darkening from sediment or a heavy roast.",
    "metric:Browning ratio": "Browning ratio — blue over green absorption: the roast axis on its own, "
                             "independent of pigment. Higher means more browned.",
    "metric:G' (alt.)": "G-prime — an alternative greenness using the blue denominator. Browning-sensitive, "
                        "and a little fragile on this rig.",
}

# Descriptions for each phase's STEP-TABS, keyed by the tab label the plugin declares (walk_tabs falls back
# to the raw label for anything not listed). PROCESSING and EVALUATION each have several steps.
TAB_NARRATION = {
    # PROCESSING steps
    "Reference raster": "The reference frame's raster — the raw camera strip the reference spectrum was "
                        "extracted from.",
    "Sample raster": "The sample frame's raster — the raw strip behind the sample spectrum.",
    "Spectra": "The two raw spectra overlaid, reference against sample, before any math.",
    "Transmission": "Transmission, T(λ) = S ÷ R: the fraction of the reference light the sample lets "
                    "through at each wavelength.",
    "Absorption": "Absorption, A(λ) = −log₁₀(S/R): the same information as optical density — the oil's "
                  "absorption bands now stand out as peaks.",
    # EVALUATION steps
    "Metrics": "The evaluation metrics — the quality numbers the plugin computes from the spectra.",
    "Spectrum": "The absorption spectrum again, now with the pumpkin-oil evaluation bands marked on it.",
    "Report": "The one-click PDF report: every spectrum, metric and capture from this run, ready to save "
              "or attach.",
    # PUBLISHING step
    "Send to LIMS": "The publishing step — send this measurement and its report to the lab's LIMS as a new "
                    "sample.",
}


def run(d):
    d.launch_app()   # attach mode (bench.sh): drives the app the operator already started with --doc-mode
    d.doc(use_case=NARRATION["useCase"], outline=OUTLINE)

    # Login — scripted from director.ini [bench] if credentials are filled, else a human gate. The bench
    # additionally needs a CALIBRATED real setup, which the harness can't synthesize — so that stays human.
    d.login("bench")
    # masterUserExakta is plugin-bound, so login lands in the WIZARD, which opens the camera. Bounce via Home
    # so the wizard's hideEvent releases /dev/video0 BEFORE the bench reopens it — else the bench sees "no
    # camera" (the wizard's stream thread is still holding the device). The sleep lets the release complete.
    d.nav("Home")
    d.sleep(2)
    d.wait_for_human("Confirm a CALIBRATED real spectrometer setup is active, then press Ctrl+Shift+ß.")
    d.nav("DevMeasurementBenchViewModule")   # menu entry is a QAction → nav, not a click

    # --- ACQUISITION ---
    d.doc(phase="Acquisition")
    d.narrate(NARRATION["phase:Acquisition"])

    # Reference — click the Reference step-tab explicitly (on camera) and describe it.
    d.click(ROLE_TABS, tab=REFERENCE_TAB)
    d.narrate(NARRATION["step:REFERENCE"])
    d.wait_for_human("Place the REFERENCE (isopropanol blank) in the beam, illuminate the slit, then press "
                     "Ctrl+Shift+ß.")
    d.click(CAPTURE)                              # "Capture reference" (auto-exposes first)
    d.wait_ready(CAPTURE, enabled=True, timeout=60)
    d.dismiss()                                  # clear a capture-fail modal if one popped (no-op otherwise)
    d.click(INNER_TABS, tab=SPECTRUM_TAB)        # reveal the extracted reference spectrum
    d.screenshot("bench_01_reference")

    # Sample — click the Sample step-tab and describe it.
    d.click(ROLE_TABS, tab=SAMPLE_TAB)
    d.narrate(NARRATION["step:SAMPLE"])
    d.wait_for_human("Swap in the SAMPLE (oil in isopropanol), then press Ctrl+Shift+ß.")
    d.click(CAPTURE)                             # "Capture sample"
    d.wait_ready(CAPTURE, enabled=True, timeout=60)
    d.dismiss()
    d.click(INNER_TABS, tab=SPECTRUM_TAB)
    d.screenshot("bench_02_sample")
    d.wait_ready(NEXT, enabled=True)             # Next enables only once BOTH roles are captured

    # --- PROCESSING --- walk EVERY step-tab (rasters, Spectra, Transmission, Absorption).
    d.click(NEXT)                               # ACQUISITION → PROCESSING
    d.doc(phase="Processing")
    d.narrate(NARRATION["phase:Processing"])
    d.walk_tabs(PROCESSING_TABS, TAB_NARRATION, screenshot="bench_03_processing")

    # --- EVALUATION --- walk every step-tab (Metrics, Spectrum, Report); on Metrics, describe each field.
    d.click(NEXT)                               # PROCESSING → EVALUATION
    d.doc(phase="Evaluation")
    d.narrate(NARRATION["phase:Evaluation"])

    def describe_metrics(label, _index):
        if label == "Metrics":
            for metric in EVAL_METRICS:
                d.narrate(NARRATION["metric:" + metric])

    d.walk_tabs(EVAL_TABS, TAB_NARRATION, on_tab=describe_metrics, screenshot="bench_04_evaluation")

    # --- PUBLISHING (only if the plugin declares it) ---
    d.click(NEXT)                               # EVALUATION → PUBLISHING
    d.doc(phase="Publishing")
    d.narrate(NARRATION["phase:Publishing"])
    d.walk_tabs(PUBLISHING_TABS, TAB_NARRATION, screenshot="bench_05_publishing")
    d.click(SEND_LIMS)
    d.sleep(2)
    d.screenshot("bench_06_published")

    d.set_hint("Done — a full bench measurement, start to finish.")


if __name__ == "__main__":
    main(run, title=TITLE)
