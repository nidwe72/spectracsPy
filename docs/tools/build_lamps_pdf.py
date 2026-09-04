#!/usr/bin/env python3
"""
Generator for the internal *Lamps* knowledge-base PDF.

    SOURCE OF TRUTH:  docs/KB_lamps.md   <- edit the prose THERE, never the PDF
    OUTPUT:           ../spectracs-docs/internal/Spectracs_Lamps.pdf

Sixth of the internal document set. `build_capture_fidelity_pdf.py` covers the INSTRUMENT,
`build_sample_physics_pdf.py` the SAMPLE, `build_metric_algebra_pdf.py` the ARITHMETIC and
`build_lamp_410_680_pdf.py` one specific PURCHASING question about the light source. This one is the
GENERAL lamp note: what any lamp has to do for this instrument, and the Yuji-vs-halogen measurement that
first separates the lamp from the instrument. The rendering is done by the capture-fidelity renderer;
this script only supplies the different source, output and title.

Figures 1-3 are produced by:
    ./venv/bin/python diagnostics/lamp_yuji_vs_halogen.py --figures
which writes three SVGs to docs/figures/. Re-run it if the screenshots, the ROI or the calibration
cubic change, then re-run this.

HOW TO REGENERATE
-----------------
    python3 docs/tools/build_lamps_pdf.py
"""
import os
import sys

import build_capture_fidelity_pdf as renderer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SOURCE_MD = os.path.join(REPO, "docs", "KB_lamps.md")
OUT_PDF = os.path.abspath(os.path.join(
    REPO, "..", "spectracs-docs", "internal", "Spectracs_Lamps.pdf"))
TITLE = "Spectracs — Lamps"


def main():
    forwarded = sys.argv[1:]
    sys.argv = [sys.argv[0], "--source", SOURCE_MD, "--out", OUT_PDF, "--title", TITLE] + forwarded
    renderer.main()


if __name__ == "__main__":
    main()
