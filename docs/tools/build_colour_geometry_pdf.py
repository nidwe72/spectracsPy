#!/usr/bin/env python3
"""
Generator for the *Colour Geometry* discussion PDF.

    SOURCE OF TRUTH:  docs/DOC_colour_geometry.md   <- edit the prose THERE, never the PDF
    OUTPUT:           ../spectracs-docs/internal/Spectracs_ColourGeometry.pdf

The COLOUR member of the internal document set, and the counterpart to `build_metric_algebra_pdf.py`:
that one covers the arithmetic from absorbance to verdict, this one the arithmetic from absorbance to
the colour chips. Rendering is done by the capture-fidelity renderer; this script only supplies source,
output and title.

⚠ It started life as a discussion note in `spectracs-references/tmp/discussion/` and moved here on
2026-08-24, once the work it argued for was implemented (§13) and it became documentation of what the
app does rather than a proposal for what it should do.

The figures are built by `diagnostics/colour_geometry_figures.py` - re-run that first if the colour
code changes, then re-run this.

HOW TO REGENERATE
-----------------
    python3 docs/tools/build_colour_geometry_pdf.py
"""
import os
import sys

import build_capture_fidelity_pdf as renderer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SOURCE_MD = os.path.join(REPO, "docs", "DOC_colour_geometry.md")
OUT_PDF = os.path.abspath(os.path.join(
    REPO, "..", "spectracs-docs", "internal", "Spectracs_ColourGeometry.pdf"))
TITLE = "Spectracs — From Spectrum to Colour"


def main():
    forwarded = sys.argv[1:]
    sys.argv = [sys.argv[0], "--source", SOURCE_MD, "--out", OUT_PDF, "--title", TITLE] + forwarded
    renderer.main()


if __name__ == "__main__":
    main()
