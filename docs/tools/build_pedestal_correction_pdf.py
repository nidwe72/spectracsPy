#!/usr/bin/env python3
"""
Generator for the internal *Pedestal Correction* documentation PDF.

    SOURCE OF TRUTH:  docs/DOC_pedestal_correction.md   <- edit the prose THERE, never the PDF
    OUTPUT:           ../spectracs-docs/internal/Spectracs_PedestalCorrection.pdf

Fourth of the internal document set, and the narrowest. `build_capture_fidelity_pdf.py` covers the
INSTRUMENT, `build_sample_physics_pdf.py` the SAMPLE, `build_metric_algebra_pdf.py` the ARITHMETIC
that yields a verdict. This one takes a single step of that arithmetic — the linear baseline — and
asks what it leaves behind. The rendering is done by the capture-fidelity renderer; this script only
supplies the different source, output and title.

The document's numbers and both figures are produced by:
    diagnostics/pedestal_correction.py     (via the SHIPPED code paths, into docs/figures/)
Re-run it if the metric code or the data set changes, then re-run this.

⚠ The document contains a PROPOSAL (its chapter 7) that is NOT implemented. Its chapter 10 argues
against adopting it on present evidence. Do not let the two drift apart.

HOW TO REGENERATE
-----------------
    python3 docs/tools/build_pedestal_correction_pdf.py
"""
import os
import sys

import build_capture_fidelity_pdf as renderer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SOURCE_MD = os.path.join(REPO, "docs", "DOC_pedestal_correction.md")
OUT_PDF = os.path.abspath(os.path.join(
    REPO, "..", "spectracs-docs", "internal", "Spectracs_PedestalCorrection.pdf"))
TITLE = "Spectracs — The Pedestal Correction"


def main():
    forwarded = sys.argv[1:]
    sys.argv = [sys.argv[0], "--source", SOURCE_MD, "--out", OUT_PDF, "--title", TITLE] + forwarded
    renderer.main()


if __name__ == "__main__":
    main()
