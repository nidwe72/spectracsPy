"""The "Director's Cut" — dev measurement bench, two-sweep narrated screencast (SPEC_director_cut.md).

ONE recording, two sweeps:
  SWEEP 1 — "do it" (forward): login -> capture Reference -> capture Sample -> the should-be AUTO-ADVANCE jumps
    straight to Details (metadata) -> type the dummy metadata -> Verdict/Publish -> explain the verdict -> publish.
  SWEEP 2 — "explain it" (backward): Back into Evaluation (point+explain six Metrics fields, then Absorption
    (bands), then Report) -> Back into Processing (Spectra, Absorption). The record ends there.

WHY two sweeps: the DEV plugin is permanently should-be (AUTO_ADVANCE + Reference/Sample step-chevrons), so the Next
at the Sample boundary JUMPS over Processing+Evaluation to Details — a forward walk of every phase is impossible. The
skipped phases are reached by Back (Option C keeps their computed content viewable). See SPEC_director_cut.md §1.

POST-M2 objectNames: everything renders through the base's ONE PluginExecutionView.tabWidget; nav is
PluginExecutionView.{next,back}Button. Role advance Reference->Sample is a NEXT (the role-tabs are hidden in
should-be). Field pointing uses the E2 "workflowItem.<slug>" objectNames.

Both narration layers show at once: the app's own status-bar coach line (terse imperative, from the plugin
CaptureView.prompt) + the doc panel (the narrated 'why', below). Authored to COMPLEMENT the coach line, not echo it.

Prerequisites (the bench enforces them):
  * master session (masterUserExakta) — scripted from director.ini [bench] if present, else a human gate,
  * a REAL non-virtual spectrometer plugged DIRECT-to-USB (the bench refuses virtual devices),
  * a steady LIGHT SOURCE on the slit for both reference and sample,
  * the LIMS (SENAITE) stack up if the publish click should land (SPEC_lims_integration.md §12.1).

Run:  DOC_ATTACH=1 python automation/scenarios/measurement_bench.py    (or: automation/bench.sh)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from automation.automation_director import main

TITLE = "The measurement bench — a real sample, verdict, and the analysis behind it"

# --- objectName targets (post-M2 — SPEC_director_cut.md §5) ---
CAPTURE = "CapturePanel.captureButton"            # single button; label flips Reference/Sample by chevron
INNER_TABS = "CapturePanel.innerTabs"             # Spectrum (0) | Image (1); opens on Image, capture -> Spectrum
NEXT = "PluginExecutionView.nextButton"           # base nav (was DevMeasurementBenchViewModule.nextButton — retired)
BACK = "PluginExecutionView.backButton"
TABS = "PluginExecutionView.tabWidget"            # ALL phases render into this ONE widget (cleared per stop)
SEND_LIMS = "DevMeasurementBenchViewModule.sendToLimsButton"
MD_TITLE = "PluginExecutionView.metadata.title"   # E1 field objectNames
MD_TEMP = "PluginExecutionView.metadata.temperature"
SPECTRUM_TAB = 0                                  # inner tabs: 0 = Spectrum, 1 = Image (C2 order)

# The six Metrics fields to point at + explain, in order (E2 "workflowItem.<slug>", SPEC_director_cut.md §4).
METRIC_FIELDS = [
    ("workflowItem.verdict", "field:verdict"),
    ("workflowItem.intrinsic_despiked", "field:intrinsicDespiked"),
    ("workflowItem.intrinsic_perceived_despiked", "field:intrinsicPerceivedDespiked"),
    # ⚠ The slug follows the LABEL, and the label carries the window — trimmed 440-460 -> 448-460 on
    # 2026-08-10 (SPEC_soret_448_trim.md §6). A stale slug here is a silent locate failure mid-video.
    ("workflowItem.soret_448_460_nm", "field:soret"),
    ("workflowItem.q_560_580_nm", "field:q"),
    ("workflowItem.pigment_ratio", "field:pigmentRatio"),
]

# Doc-panel outline (highlighted as each phase is visited — story order, not chevron order).
OUTLINE = ["Acquisition", "Details", "Verdict/Publish", "Evaluation", "Processing"]

# The opening summary card (§18.7 CR-B) — headlines the VERDICT + Roast Ampel (Edwin).
AGENDA = [
    "Measure a real pumpkin-seed oil on a real spectrometer, end to end.",
    "Get a roast VERDICT — the Roast Ampel: green for a fresh oil, brown for an over-roasted one.",
    "See the analytical metrics the verdict is built on.",
    "Generate a PDF report with all the spectral data embedded — ready to send to a lab's LIMS.",
]

# Claude-authored narration — the 'why' (§16.0), a different register from the in-app coach line (SPEC_director_cut §13).
NARRATION = {
    "useCase": "From a real sample to a lab-ready roast verdict, on the bench.",
    # sweep 1 — do it
    "phase:Acquisition": "First we capture two spectra — a reference blank, then the sample. Everything is "
                         "measured against the reference.",
    "step:REFERENCE": "The reference is pure isopropanol in the cuvette — no oil. It's the 100 % baseline; "
                      "whatever the oil absorbs shows up relative to this.",
    "step:SAMPLE": "The sample is that same solvent with the pumpkin-seed oil dissolved in. The difference "
                   "between the two spectra is the whole measurement.",
    "jump": "Measurement done. The bench jumps straight to the summary — a details form, then the verdict. "
            "We'll come back for the analysis.",
    "phase:Details": "A few labels for the record — they travel with the run and into the report.",
    "md:title": "The title identifies the batch — here, Kernöl-20260724A.",
    "md:temperature": "And the temperature the oil was roasted at — 122 °C.",
    "verdict:badge": "The headline: the Roast Ampel — the roast verdict, read straight from the pigment ratio. "
                     "Green means a fresh, well-roasted oil; brown means over-roasted.",
    "publish": "One click sends this measurement and its PDF report to the lab's LIMS as a new sample.",
    "bridge": "That's the whole end-user flow — measure, verdict, publish. But nothing is hidden: an interested "
              "user can step Back through the phases any time to see the detail behind the verdict.",
    # sweep 2 — explain it
    "phase:Evaluation": "Now the analysis behind that verdict — the numbers the Ampel is built on.",
    "field:verdict": "The verdict again as the analytical gauge — the marker rides the pigment-ratio scale, "
                     "from green (fresh) down to brown (over-roasted).",
    "field:intrinsicDespiked": "The oil's intrinsic colour — what it actually absorbs — with the narrow "
                               "instrument spikes removed.",
    "field:intrinsicPerceivedDespiked": "The same colour flipped to how the eye would perceive it — the green "
                                         "a person sees.",
    "field:soret": "The Soret band: blue-light absorption from the green pigment. A fresh oil absorbs strongly here.",
    "field:q": "The Q band: the green pigment's second fingerprint, in the yellow-green.",
    "field:pigmentRatio": "Soret over Q — the one dilution-invariant number that separates a green oil from a "
                          "browned one. This drives the Ampel.",
    "eval:absorptionBands": "The absorbance spectrum with those bands marked — the pigment features the metrics read.",
    "eval:report": "The one-click PDF: every spectrum, metric and the verdict on one page, raw data embedded "
                   "for the lab.",
    "phase:Processing": "And underneath it all — the raw processing.",
    "proc:spectra": "The two captured spectra overlaid, reference against sample, before any maths.",
    "proc:absorption": "Turned into absorbance, A(λ) = −log₁₀(sample / reference): the oil's absorption bands "
                       "stand out as peaks.",
}


def run(d):
    d.launch_app()   # attach mode (bench.sh): drives the app the operator already started with --doc-mode
    d.doc(use_case=NARRATION["useCase"], outline=OUTLINE)

    # Order (§18.1): logo card -> visible login -> agenda card -> bench. The card stands in for Home so the
    # measurements-overview is never filmed; showing it after login performs the camera handoff.
    d.cover("measurement bench", hold=3)
    d.login("bench")
    d.cover("measurement bench", points=AGENDA)
    d.wait_for_human("Confirm a CALIBRATED real spectrometer setup is active, then press Ctrl+Shift+ß.")
    d.nav("DevMeasurementBenchViewModule")   # menu entry is a QAction -> nav, not a click

    # ============ SWEEP 1 — DO IT (forward; the Next at the Sample boundary JUMPS) ============
    d.doc(phase="Acquisition")
    d.narrate(NARRATION["phase:Acquisition"])

    # Reference chevron (step 0; role-tabs hidden — the chevron IS the role selector, so we advance with NEXT).
    d.narrate(NARRATION["step:REFERENCE"])
    d.wait_for_human("Place the REFERENCE (isopropanol blank) in the beam, illuminate the slit, then press "
                     "Ctrl+Shift+ß.")
    d.click(CAPTURE)                             # "Capture reference" (auto-exposes first)
    d.wait_capture(CAPTURE)                      # wait for auto-expose + the WHOLE frame burst (C3b)
    d.dismiss()                                  # clear a capture-fail modal if one popped (no-op otherwise)
    d.click(INNER_TABS, tab=SPECTRUM_TAB)        # show the extracted reference spectrum
    d.screenshot("bench_01_reference")
    d.wait_ready(NEXT, enabled=True)             # Next enables once Reference is captured
    d.click(NEXT)                                # Reference -> Sample chevron (plain step, not the boundary)

    # Sample chevron.
    d.narrate(NARRATION["step:SAMPLE"])
    d.wait_for_human("Swap in the SAMPLE (oil in isopropanol), then press Ctrl+Shift+ß.")
    d.click(CAPTURE)                             # "Capture sample"
    d.wait_capture(CAPTURE)                      # sample has no auto-expose leg — __capturing is its only gate
    d.dismiss()
    d.click(INNER_TABS, tab=SPECTRUM_TAB)
    d.screenshot("bench_02_sample")
    d.wait_ready(NEXT, enabled=True)             # boundary Next enables only once BOTH roles are captured
    d.narrate(NARRATION["jump"])
    d.click(NEXT)                                # boundary -> AUTO-ADVANCE JUMP over Processing+Evaluation -> Details

    # Details (METADATA) — type the dummy metadata. Wait for the form (the jump runs the heavy compute hooks).
    d.wait_ready(MD_TITLE, visible=True, timeout=40)
    d.doc(phase="Details")
    d.narrate(NARRATION["phase:Details"])
    d.click(MD_TITLE)
    d.narrate(NARRATION["md:title"])
    d.type_text("Kernöl-20260724A")             # unicode ö via xdotool (E3)
    d.click(MD_TEMP)
    d.narrate(NARRATION["md:temperature"])
    d.type_text("122")
    d.screenshot("bench_03_details")
    d.click(NEXT)                                # Details -> Verdict/Publish

    # Verdict/Publish — point at the verdict badge, explain it, then publish.
    d.wait_ready(SEND_LIMS, visible=True, timeout=20)
    d.doc(phase="Verdict/Publish")
    d.point("workflowItem.verdict")
    d.narrate(NARRATION["verdict:badge"])
    d.screenshot("bench_04_verdict")
    d.click(SEND_LIMS)                           # just click (D-publish-live: no gate; operator ensures SENAITE up)
    d.narrate(NARRATION["publish"])
    d.sleep(2)
    d.screenshot("bench_05_published")

    # Bridge into sweep 2 (still on Verdict/Publish, before the first Back).
    d.narrate(NARRATION["bridge"])

    # ============ SWEEP 2 — EXPLAIN IT (backward; each Back = exactly ONE stop) ============
    d.click(BACK)                                # Verdict/Publish -> Details
    d.click(BACK)                                # Details -> Evaluation
    d.wait_ready(TABS, visible=True, timeout=20)
    d.doc(phase="Evaluation")
    d.narrate(NARRATION["phase:Evaluation"])

    # Metrics tab (index 0, shown on entry) — point + explain the six fields.
    d.visit_tab(TABS, "Metrics")
    for objectName, key in METRIC_FIELDS:
        d.point(objectName)
        d.narrate(NARRATION[key])
    d.screenshot("bench_06_metrics")

    d.visit_tab(TABS, "Absorption (bands)")
    d.narrate(NARRATION["eval:absorptionBands"])
    d.screenshot("bench_07_bands")

    d.visit_tab(TABS, "Report")
    d.narrate(NARRATION["eval:report"])
    d.screenshot("bench_08_report")

    # Back into Processing — Spectra + Absorption.
    d.click(BACK)                                # Evaluation -> Processing
    d.wait_ready(TABS, visible=True, timeout=20)
    d.doc(phase="Processing")
    d.narrate(NARRATION["phase:Processing"])
    d.visit_tab(TABS, "Spectra")
    d.narrate(NARRATION["proc:spectra"])
    d.screenshot("bench_09_spectra")
    d.visit_tab(TABS, "Absorption")
    d.narrate(NARRATION["proc:absorption"])
    d.screenshot("bench_10_absorption")

    d.screenshot("bench_11_end")


if __name__ == "__main__":
    main(run, title=TITLE)
