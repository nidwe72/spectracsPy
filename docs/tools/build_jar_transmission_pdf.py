#!/usr/bin/env python3
"""
Generator for the internal *The Jar in the Beam* documentation PDF.

    SOURCE OF TRUTH:  docs/DOC_jar_transmission.md   <- edit the prose THERE, never the PDF
    OUTPUT:           ../spectracs-docs/internal/Spectracs_JarTransmission.pdf

The shortest of the internal document set, and the only one whose result is negative: an empty jar
against the bare lamp, and the answer that it changes the LEVEL and not the SHAPE. The rendering is
done by the capture-fidelity renderer; this script only supplies the source, output and title.

The document's numbers and Figures 1-3 are produced by:
    ./venv/bin/python diagnostics/jar_transmission.py
which writes the three SVGs into docs/figures/. Re-run it if the digitisation, the DN guard or the
zone definitions change, then re-run this.

HOW TO REGENERATE
-----------------
    python3 docs/tools/build_jar_transmission_pdf.py
"""
import os
import sys

import build_capture_fidelity_pdf as renderer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SOURCE_MD = os.path.join(REPO, "docs", "DOC_jar_transmission.md")
OUT_PDF = os.path.abspath(os.path.join(
    REPO, "..", "spectracs-docs", "internal", "Spectracs_JarTransmission.pdf"))
TITLE = "Spectracs — The Jar in the Beam"


def main():
    forwarded = sys.argv[1:]
    sys.argv = [sys.argv[0], "--source", SOURCE_MD, "--out", OUT_PDF, "--title", TITLE] + forwarded
    renderer.main()


if __name__ == "__main__":
    main()
