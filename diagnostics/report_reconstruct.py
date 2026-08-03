"""Rebuild a SpectralWorkflow from a report PDF's embedded JSON.  (SPEC_capture_quality.md §16.20.8)

WHY THIS EXISTS. Workflow persistence is Option A — "the workflow IS the record" — so a saved run reloads
from the app DB as an entity graph and needs no deserializer (`SPEC_workflow_persistence.md` §10). But 66 of
the 124 archived reports predate the habit of saving runs, and for those the PDF's embedded `workflow.json`
is the ONLY record. `toReportJson()` is one-way; this module inverts it.

⚠ IT IS A REPORT-JSON RECONSTRUCTOR, NOT A PERSISTENCE LAYER. It lives in diagnostics on purpose. The DB
path is the supported way to reload a workflow; this exists so historical reports can be re-rendered, and it
reconstructs exactly what `toReportJson` emits — no more:

  * step `view` vs `evaluationResult` cannot be told apart, because `toReportJson` appends the passive view
    into the same `items` list. Everything therefore comes back inside the EvaluationResult. HARMLESS for
    rendering: `WorkflowReportBuilder.__stepItems` merges both and filters on `isShownInReport`, which every
    view-model round-trips.
  * captured image PIXELS are not in the JSON (§5b) — only the `attachmentName`. `attachImages()` re-injects
    them from the PDF's own attachments, and WITHOUT that call every capture is silently dropped from the
    regenerated report.
  * transient plugin state (hints, frames, mandatory/persist flags, metadata fields) is not in the report
    JSON and does not come back. It is not rendered either.

Run (self-test over the archive):
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/report_reconstruct.py
"""
import io
import json
import os

from pypdf import PdfReader

from sciens.spectracs.model.spectral.SpectralWorkflow import SpectralWorkflow
from sciens.spectracs.model.spectral.SpectralWorkflowPhase import SpectralWorkflowPhase
from sciens.spectracs.model.spectral.SpectralWorkflowStep import SpectralWorkflowStep
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.model.spectral.SpectraContainer import SpectraContainer
from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.model.spectral.plugin.view.EvaluationResult import EvaluationResult
from sciens.spectracs.model.spectral.plugin.view.ViewModelFactory import ViewModelFactory
from sciens.spectracs.model.spectral.plugin.view.SpectrumCaptureView import SpectrumCaptureView


def phaseTypeOf(name):
    """'ACQUISITION' -> SpectralWorkflowPhaseType.ACQUISITION, tolerating value- or name-style tags."""
    for phaseType in SpectralWorkflowPhaseType:
        if name in (getattr(phaseType, "value", None), getattr(phaseType, "name", None), str(phaseType)):
            return phaseType
    return None


def workflowFromReportJson(report):
    """The inverse of SpectralWorkflow.toReportJson(). Returns a transient (unpersisted) workflow."""
    header = report.get("header") or {}
    workflow = SpectralWorkflow()
    workflow.username = header.get("username")
    workflow.userId = header.get("userId")
    workflow.pluginCodeRef = header.get("pluginCodeRef")
    workflow.pluginVersion = header.get("pluginVersion")
    workflow.timestampIso = header.get("timestampIso")

    for phaseEntry in report.get("phases") or []:
        phaseType = phaseTypeOf(phaseEntry.get("type"))
        if phaseType is None:                       # a phase type retired since the report was written
            continue
        phase = SpectralWorkflowPhase()
        phase.setType(phaseType)
        for stepEntry in phaseEntry.get("steps") or []:
            phase.addToSteps(stepFromReportJson(stepEntry))
        workflow.addToPhases(phase)
    return workflow


def stepFromReportJson(entry):
    step = SpectralWorkflowStep()
    if entry.get("id"):
        step.setId(entry["id"])                     # keep the original id: attachment names key off the role,
    step.setRole(entry.get("role"))                 # but the id is what a reader cross-references
    step.setLabel(entry.get("label"))

    spectra = entry.get("spectra") or {}
    if spectra:
        container = SpectraContainer()
        for role, values in spectra.items():
            container.addToSpectra(Spectrum().fromJson(values), role)
        step.setContainer(container)

    items = [ViewModelFactory.fromJson(item) for item in (entry.get("items") or [])]
    items = [item for item in items if item is not None]     # unknown "type" tags are dropped, not fatal
    if items:
        result = EvaluationResult()
        for item in items:
            result.addItem(item)
        step.setEvaluationResult(result)
    return step


def attachImages(workflow, attachments):
    """Re-inject capture pixels from the PDF's own /EmbeddedFiles, keyed by attachmentName.

    ⚠ WITHOUT THIS THE REGENERATED REPORT SILENTLY LOSES EVERY CAPTURE. `SpectrumCaptureView.toJson` carries
    the descriptor only; `WorkflowReportBuilder.__prepareCapture` skips any capture whose `reportImage` is
    None, with no warning. Returns how many were restored, so a caller can assert on it."""
    from PIL import Image
    restored = 0
    for capture in captureViews(workflow):
        payload = attachments.get(capture.attachmentName)
        if payload is None:
            continue
        capture.reportImage = Image.open(io.BytesIO(payload)).convert("RGB")
        restored += 1
    return restored


def captureViews(workflow):
    for phaseType in SpectralWorkflowPhaseType:
        phase = workflow.getPhase(phaseType)
        if phase is None:
            continue
        for step in phase.getSteps().values():
            result = step.getEvaluationResult()
            if result is None:
                continue
            for item in result.getItems():
                if isinstance(item, SpectrumCaptureView):
                    yield item


def readReport(path):
    """(workflow, attachments) straight from a report PDF. attachments = {name: bytes}."""
    reader = PdfReader(path)
    raw = reader.attachments.get("workflow.json")
    if not raw:
        raise KeyError("%s carries no workflow.json" % path)
    attachments = {name: payload[0] for name, payload in reader.attachments.items()
                   if name != "workflow.json"}
    workflow = workflowFromReportJson(json.loads(raw[0]))
    return workflow, attachments


def main():
    from settling_sweep import BASE
    paths = sorted(os.path.join(root, name)
                   for root, _, files in os.walk(BASE) for name in files if name.endswith(".pdf"))
    print("Reconstructing %d archived reports — checking the round trip is lossless where it matters.\n"
          % len(paths))
    print("   %-46s %6s %6s %6s %8s %s" % ("report", "phases", "steps", "items", "captures", "note"))
    print("   " + "-" * 100)
    failures = 0
    for path in paths:
        try:
            workflow, attachments = readReport(path)
            restored = attachImages(workflow, attachments)
            phases = [p for p in (workflow.getPhase(t) for t in SpectralWorkflowPhaseType) if p is not None]
            steps = sum(len(p.getSteps()) for p in phases)
            items = sum(len(s.getEvaluationResult().getItems())
                        for p in phases for s in p.getSteps().values()
                        if s.getEvaluationResult() is not None)
            captures = len(list(captureViews(workflow)))
            note = "" if restored == captures else "⚠ %d of %d captures had no attachment" % (
                restored, captures)
            if note:
                failures += 1
            print("   %-46s %6d %6d %6d %5d/%-2d %s"
                  % (os.path.relpath(path, BASE), len(phases), steps, items, restored, captures, note))
        except Exception as error:
            failures += 1
            print("   %-46s %s: %s" % (os.path.relpath(path, BASE), type(error).__name__, error))
    print()
    print("   %d report(s) with a problem." % failures)


if __name__ == "__main__":
    main()
