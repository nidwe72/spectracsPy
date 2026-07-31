#!/usr/bin/env python3
"""
Generator for the internal *From Spectrum to Verdict* documentation PDF.

    SOURCE OF TRUTH:  docs/DOC_metric_algebra.md   <- edit the prose THERE, never the PDF
    OUTPUT:           ../spectracs-docs/internal/Spectracs_MetricAlgebra.pdf

Third of the internal document set, and the one that closes the loop. `build_capture_fidelity_pdf.py`
covers the INSTRUMENT (camera to spectrum); `build_sample_physics_pdf.py` covers the SAMPLE (what is
in the jar); this one covers the ARITHMETIC that turns the resulting absorbance curve into a verdict.
The rendering is done by the capture-fidelity renderer — this script only supplies the different
source, output and title.

The document's numbers and figures are produced by:
    diagnostics/metric_walkthrough.py      (every intermediate quantity, via the SHIPPED code paths)
    diagnostics/metric_algebra_plots.py    (the three figures, into spectracs-references/tmp/)
Re-run both if the metric code changes, then re-run this.

HOW TO REGENERATE
-----------------
    python3 docs/tools/build_metric_algebra_pdf.py
"""
import os
import sys

import build_capture_fidelity_pdf as renderer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SOURCE_MD = os.path.join(REPO, "docs", "DOC_metric_algebra.md")
OUT_PDF = os.path.abspath(os.path.join(
    REPO, "..", "spectracs-docs", "internal", "Spectracs_MetricAlgebra.pdf"))
TITLE = "Spectracs — From Spectrum to Verdict"


def main():
    forwarded = sys.argv[1:]
    sys.argv = [sys.argv[0], "--source", SOURCE_MD, "--out", OUT_PDF, "--title", TITLE] + forwarded
    renderer.main()


if __name__ == "__main__":
    main()
