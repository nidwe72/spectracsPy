#!/usr/bin/env python3
"""
Generator for the internal *Light, Pigment and Solvent* documentation PDF.

    SOURCE OF TRUTH:  docs/DOC_sample_physics.md   <- edit the prose THERE, never the PDF
    OUTPUT:           ../spectracs-docs/internal/Spectracs_LightPigmentSolvent.pdf

Companion to `build_capture_fidelity_pdf.py`, which does the actual rendering — this script only
supplies the different source, output and title. The two PDFs are deliberately complementary:
Capture Fidelity covers the INSTRUMENT (camera to spectrum); this one covers the SAMPLE and the
LIGHT (what is in the jar, and what it does to a photon).

HOW TO REGENERATE
-----------------
    python3 docs/tools/build_sample_physics_pdf.py
"""
import os
import sys

import build_capture_fidelity_pdf as renderer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SOURCE_MD = os.path.join(REPO, "docs", "DOC_sample_physics.md")
OUT_PDF = os.path.abspath(os.path.join(
    REPO, "..", "spectracs-docs", "internal", "Spectracs_LightPigmentSolvent.pdf"))
TITLE = "Spectracs — Light, Pigment and Solvent"


def main():
    forwarded = sys.argv[1:]
    sys.argv = [sys.argv[0], "--source", SOURCE_MD, "--out", OUT_PDF, "--title", TITLE] + forwarded
    renderer.main()


if __name__ == "__main__":
    main()
