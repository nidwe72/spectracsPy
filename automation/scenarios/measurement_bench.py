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

# The overview typed onto the SECOND cover card (§18.7 CR-B) — what the viewer is about to see.
AGENDA = [
    "Measurement on a real spectrometer of real oil.",
    "Evaluations create some metrics.",
    "A PDF is created for viewing, with all spectral data embedded.",
    "The PDF can be sent to a laboratory information management system (LIMS).",
]

# Every evaluation metric, in the grid order the Dev plugin emits them (DevSpectralPlugin) — Edwin: describe
# them ALL, including 'color'.
EVAL_METRICS = ["color", "Greenness G", "Pigment D_Q", "Soret A_blue",
                "Clarity A_green", "Pigment ratio · legacy", "G' (alt.)"]

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
    "metric:Soret A_blue": "Soret A_blue — absorption in the blue Soret region, which tracks the intact "
                           "green pigment; a fresher, greener oil absorbs more blue here.",
    "metric:Clarity A_green": "Clarity A_green — the green-window floor, which rises with turbidity or "
                              "darkening from sediment or a heavy roast.",
    "metric:Pigment ratio · legacy": "Pigment ratio, legacy bands — blue Soret over the green clarity floor. "
                             "Higher means more intact pigment; a greener, fresher oil.",
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

    # Order (SPEC §18.1, C1c): logo card → visible login → bench. The card is a page in the MainViewModule
    # stack, so it stands in for Home — the measurements-overview is never filmed. hold=3 so card #1 is
    # readable before login replaces it (§18.7 CR-A).
    d.cover("measurement bench", hold=3)     # opening frame: Documentation › measurement bench

    # Login — scripted from director.ini [bench] if credentials are filled, else a human gate; VISIBLE on
    # camera (the login page replaces the card). The bench additionally needs a CALIBRATED real setup, which
    # the harness can't synthesize — so that stays a human gate.
    d.login("bench")
    # Logo card #2 — the agenda (§18.7 CR-B), typed in char-by-char (its computed hold lets the whole
    # overview type out on camera). In --doc-mode login does NOT auto-jump to the wizard (§18.8), so the
    # measurement view never flashes and never opens the camera — the bench opens it fresh at step (4).
    d.cover("measurement bench", points=AGENDA)
    d.wait_for_human("Confirm a CALIBRATED real spectrometer setup is active, then press Ctrl+Shift+ß.")
    d.nav("DevMeasurementBenchViewModule")   # menu entry is a QAction → nav, not a click

    # --- ACQUISITION ---
    d.doc(phase="Acquisition")
    d.narrate(NARRATION["phase:Acquisition"])

    # Reference — the Reference step-tab is already active on entry (CapturePanel opens on step 0), so
    # glide-to-point it (cursor visits, no no-op click — C2b) and describe it.
    d.go_to_tab(ROLE_TABS, REFERENCE_TAB, activate=False)
    d.narrate(NARRATION["step:REFERENCE"])
    d.wait_for_human("Place the REFERENCE (isopropanol blank) in the beam, illuminate the slit, then press "
                     "Ctrl+Shift+ß.")
    d.click(CAPTURE)                              # "Capture reference" (auto-exposes first)
    d.wait_capture(CAPTURE)                       # wait for auto-expose + the WHOLE frame burst to finish (C3b)
    d.dismiss()                                  # clear a capture-fail modal if one popped (no-op otherwise)
    d.click(INNER_TABS, tab=SPECTRUM_TAB)        # reveal the extracted reference spectrum
    d.screenshot("bench_01_reference")

    # Sample — switch to the Sample step-tab (a real switch) and describe it.
    d.go_to_tab(ROLE_TABS, SAMPLE_TAB, activate=True)
    d.narrate(NARRATION["step:SAMPLE"])
    d.wait_for_human("Swap in the SAMPLE (oil in isopropanol), then press Ctrl+Shift+ß.")
    d.click(CAPTURE)                             # "Capture sample"
    d.wait_capture(CAPTURE)                      # sample has no auto-expose leg — __capturing is its only gate (C3b)
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
