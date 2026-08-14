"""Re-render every archived measurement report on the CURRENT metric.  (SPEC_capture_quality.md §16.20.8)

Edwin 2026-08-03: the three-verdict EVALUATION (§16.20.7) changed what the app computes, and the archived
reports should show it. This rebuilds each report from its own embedded record and writes it back.

⚠⚠ THIS REPLACES FILES IN PLACE, AND `spectracs-references/` IS NOT A GIT REPO. `--dry-run` is the default;
`--write` is required to touch anything. Verified backups, each made immediately before its run:
    tmp_backup_pre620_20260803/       124 files — before the §16.20 three-verdict pass
    tmp_backup_pre_v_20260814/        172 files — before the `V`/`Q%` pass, `diff -rq` clean

⭐ 2026-08-14, THE `V` PASS (`SPEC_v_metric_integration.md` §9, V10). It carried THREE generations of change
at once, because the archive had not been regenerated since 2026-08-03: the 448–460 Soret trim with its
re-derived thresholds 6.8/8.3 (every M448 number in every report moved), the numbered band plot + legend,
and Q%/`V` with its new tab and the `Absorption (bands)` -> `(bands, baseline)` rename.
⭐ The spectra are provably untouched: ABSORPTION/REFERENCE/SAMPLE/TRANSMISSION round-trip BIT-IDENTICAL
(1305 keys, worst delta 0.0) — which matters because `settling_sweep.BASE` is this same folder, so every
number in SPEC_metric_research §10 is computed from the files this tool rewrites.

WHAT A REGENERATED REPORT IS, EXACTLY. It is a RE-EVALUATION, not a patch. The spectra are the originals —
nothing is re-measured — but every rendered row is recomputed by TODAY's plugin, so anything else that
changed since capture changes too, not only the three verdicts. The provenance is preserved by the embedded
`workflow.json`, which `savePdf` rewrites with the current `captureDecode` descriptor.

WHERE THE RECORD COMES FROM. Two sources, and the DB is preferred where it exists:
  * 58 of the 124 runs were saved through the wizard and live in the app DB as an entity graph
    (`SPEC_workflow_persistence.md` §10, "the workflow IS the record"). Not used here: matching a PDF to its
    row is by timestamp, which is a guess, and the PDF's own JSON is the authoritative record OF THAT PDF.
  * every report carries its complete `workflow.json`, so `report_reconstruct` rebuilds it from the artifact
    itself — no matching, no ambiguity. That is what this tool uses, for all of them.

⚠ CAPTURE PIXELS. `SpectrumCaptureView.toJson` carries the descriptor only; a capture whose `reportImage` is
None is SILENTLY DROPPED by the report builder. `report_reconstruct.attachImages` re-injects them from the
PDF's own attachments and this tool ASSERTS the count came back — otherwise every regenerated report would
quietly lose its two capture pages.

Run:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins" \
        ./venv/bin/python diagnostics/regenerate_reports.py                 # dry run, reports what WOULD change
        ./venv/bin/python diagnostics/regenerate_reports.py --one 20260801C/001.pdf --write --out /tmp/x.pdf
        ./venv/bin/python diagnostics/regenerate_reports.py --write         # replace all, in place
"""
import argparse
import os
import sys
import tempfile

import matplotlib
matplotlib.use("Agg")

from pypdf import PdfReader

from settling_sweep import BASE
from report_reconstruct import readReport, attachImages, captureViews
from sciens.spectracs.model.spectral.SpectralWorkflowPhaseType import SpectralWorkflowPhaseType
from sciens.spectracs.logic.spectral.report.WorkflowReportBuilder import WorkflowReportBuilder
from sciens.spectracs.plugins.dev.DevSpectralPlugin import DevSpectralPlugin

# Not measurement reports — generated capability-proof documents that carry no workflow.json. The archive
# metric tool skips exactly these two (`all_metrics_archive.SKIP`).
SKIP = {"CapabilityProof_pumpkin-oil_summary.pdf", "Spectracs_CapabilityProof_status.pdf"}


def reportPaths():
    return sorted(os.path.join(root, name)
                  for root, _, files in os.walk(BASE) for name in files
                  if name.endswith(".pdf") and name not in SKIP)


def rebuild(path):
    """(builder, workflow, captureCount, restoredCount) for one archived report, on today's plugin."""
    workflow, attachments = readReport(path)
    captures = len(list(captureViews(workflow)))
    restored = attachImages(workflow, attachments)

    # The reconstructed EVALUATION/PUBLISHING phases hold the items the OLD plugin produced. The hooks APPEND
    # rather than replace, so clear first or the report would carry both generations of verdict.
    plugin = DevSpectralPlugin()
    for phaseType in (SpectralWorkflowPhaseType.EVALUATION, SpectralWorkflowPhaseType.PUBLISHING):
        phase = workflow.getPhase(phaseType)
        if phase is not None:
            phase.getSteps().clear()
    plugin.evaluation(workflow)
    plugin.publishing(workflow)

    reportView = None
    evaluation = workflow.getPhase(SpectralWorkflowPhaseType.EVALUATION)
    for step in (evaluation.getSteps().values() if evaluation is not None else []):
        view = step.getView()
        if view is not None and hasattr(view, "embedMetadata"):
            reportView = view
    if reportView is None:
        raise RuntimeError("no ReportView after re-running evaluation() — nothing to render")
    return WorkflowReportBuilder(workflow, reportView).build(), workflow, captures, restored


def verifyAttachments(path, expected):
    """Every attachment the ORIGINAL carried must be present in the regenerated file.

    Counting SpectrumCaptureViews is the WRONG check and cost a debugging round: four capture views share two
    attachment names (full-frame and cropped renditions of the same role), so the count never matches. What
    actually matters is that nothing the original carried has been lost."""
    names = set(PdfReader(path).attachments.keys())
    missing = expected - names
    if missing:
        raise RuntimeError("regenerated file lost attachment(s): %s" % sorted(missing))
    if "workflow.json" not in names:
        raise RuntimeError("regenerated file carries no workflow.json")


def verdictsOf(workflow):
    """Every gauge value on the EVALUATION tab, for the console summary.

    ⚠ The COUNT is information, not noise. Since 2026-08-14 there are up to three — Q%, pedestal, far620 —
    and a row printing fewer means a guard withheld one (SPEC_v_metric_integration.md §3.1/§3.1a):
       2 values  ->  no Q% at all: either A_Soret below the floor (the 20260806A null series, 27 runs) or
                     the sample outside the metric's domain (34 of the loose pre-rebuild one-offs).
    ⛔ It used to be documented as "the three verdicts" of §16.20 — that is no longer what this prints, and
    reading it that way would make a WITHHELD verdict look like a missing rung of the correction ladder.
    """
    out = []
    evaluation = workflow.getPhase(SpectralWorkflowPhaseType.EVALUATION)
    for step in (evaluation.getSteps().values() if evaluation is not None else []):
        result = step.getEvaluationResult()
        for item in (result.getItems() if result is not None else []):
            if type(item).__name__.startswith("Roast"):
                out.append("%.3f" % item.value)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--write", action="store_true",
                        help="actually replace the PDFs (default is a dry run)")
    parser.add_argument("--one", help="a single report, relative to the archive root")
    parser.add_argument("--out", help="with --one: write here instead of over the original")
    parser.add_argument("--limit", type=int, help="stop after N reports (for a staged run)")
    args = parser.parse_args()

    paths = [os.path.join(BASE, args.one)] if args.one else reportPaths()
    if args.limit:
        paths = paths[:args.limit]
    print("%s %d report(s)%s\n"
          % ("REGENERATING" if args.write else "DRY RUN over", len(paths),
             "" if args.write else " — nothing will be written"))
    print("   %-44s %5s %5s %9s %s"
          % ("report", "pages", "capt", "size kB", "gauge values (Q% · pedestal · far620; fewer = withheld)"))
    print("   " + "-" * 96)

    failures = 0
    for path in paths:
        relative = os.path.relpath(path, BASE)
        try:
            expected = set(PdfReader(path).attachments.keys())
            builder, workflow, captures, restored = rebuild(path)
            if restored != captures:
                raise RuntimeError("only %d of %d captures had pixels — the report would lose pages"
                                   % (restored, captures))
            target = args.out if (args.one and args.out) else path
            before = os.path.getsize(path)
            if args.write:
                # Render to a TEMPORARY file and only move it into place once it has been verified. A check
                # that runs after an in-place write cannot protect anything: by then the original is gone.
                handle, staged = tempfile.mkstemp(suffix=".pdf", dir=os.path.dirname(target))
                os.close(handle)
                try:
                    builder.savePdf(staged)
                    verifyAttachments(staged, expected)
                    os.replace(staged, target)
                finally:
                    if os.path.exists(staged):
                        os.remove(staged)
                size = "%.0f→%.0f" % (before / 1024.0, os.path.getsize(target) / 1024.0)
            else:
                # Dry run still RENDERS — that is the only way to know it would succeed — but into a temp file
                # that is deleted immediately.
                handle, staged = tempfile.mkstemp(suffix=".pdf")
                os.close(handle)
                try:
                    builder.savePdf(staged)
                    verifyAttachments(staged, expected)
                finally:
                    os.remove(staged)
                size = "%.0f" % (before / 1024.0)
            print("   %-44s %5d %5d %9s %s"
                  % (relative, builder.pageCount(), restored, size, "  ".join(verdictsOf(workflow))))
        except Exception as error:
            failures += 1
            print("   %-44s ⛔ %s: %s" % (relative, type(error).__name__, error))

    print()
    print("   %d report(s) failed." % failures)
    if not args.write:
        print("   DRY RUN — re-run with --write to replace the files.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
