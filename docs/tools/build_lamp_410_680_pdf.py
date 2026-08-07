#!/usr/bin/env python3
"""
Generator for the internal *Choosing the Lamp for 410-680 nm* documentation PDF.

    SOURCE OF TRUTH:  docs/DOC_lamp_410_680.md   <- edit the prose THERE, never the PDF
    OUTPUT:           ../spectracs-docs/internal/Spectracs_Lamp_410_680.pdf

Fifth of the internal document set. `build_capture_fidelity_pdf.py` covers the INSTRUMENT,
`build_sample_physics_pdf.py` the SAMPLE, `build_metric_algebra_pdf.py` the ARITHMETIC; this one covers
the LIGHT SOURCE — which Avonec 3 W LED combination best serves the pumpkin-oil bands across
410-680 nm. The rendering is done by the capture-fidelity renderer; this script only supplies the
different source, output and title.

The document's numbers and Figures 1-4 are produced by:
    diagnostics/led_lamp_410_680.py --verify --figures
which writes the plots to spectracs-references/tmp/lamp410680/. Re-run it if the digitiser, the scoring
or the candidate set changes, then re-run this.

HOW TO REGENERATE
-----------------
    python3 docs/tools/build_lamp_410_680_pdf.py
"""
import os
import sys

import build_capture_fidelity_pdf as renderer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SOURCE_MD = os.path.join(REPO, "docs", "DOC_lamp_410_680.md")
OUT_PDF = os.path.abspath(os.path.join(
    REPO, "..", "spectracs-docs", "internal", "Spectracs_Lamp_410_680.pdf"))
TITLE = "Spectracs — Choosing the Lamp for 410–680 nm"


def main():
    forwarded = sys.argv[1:]
    sys.argv = [sys.argv[0], "--source", SOURCE_MD, "--out", OUT_PDF, "--title", TITLE] + forwarded
    renderer.main()


if __name__ == "__main__":
    main()
