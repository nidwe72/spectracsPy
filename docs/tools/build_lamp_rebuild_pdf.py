#!/usr/bin/env python3
"""
Generator for the internal *Rebuilding the Lamp* documentation PDF.

    SOURCE OF TRUTH:  docs/DOC_lamp_rebuild.md   <- edit the prose THERE, never the PDF
    OUTPUT:           ../spectracs-docs/internal/Spectracs_Lamp_Rebuild.pdf

Sixth of the internal document set, and the successor to `build_lamp_410_680_pdf.py`: same subject —
which Avonec 3 W combination to build — but decided on MEASURED noise rather than on an emitted-spectrum
bracket, because the 2026-08-11 runs at ROI 400 nm overturned three of that study's inputs. The rendering
is done by the capture-fidelity renderer; this script only supplies the source, output and title.

The document's numbers and Figures 1-4 are produced by:
    PYTHONPATH=diagnostics python diagnostics/lamp_rebuild_search.py --verify --figures
which writes them to spectracs-references/tmp/lamprebuild/. Re-run it if the objective, the candidate set
or the measured inputs change, then re-run this.

HOW TO REGENERATE
-----------------
    python3 docs/tools/build_lamp_rebuild_pdf.py
"""
import os
import sys

import build_capture_fidelity_pdf as renderer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SOURCE_MD = os.path.join(REPO, "docs", "DOC_lamp_rebuild.md")
OUT_PDF = os.path.abspath(os.path.join(
    REPO, "..", "spectracs-docs", "internal", "Spectracs_Lamp_Rebuild.pdf"))
TITLE = "Spectracs — Rebuilding the Lamp"


def main():
    forwarded = sys.argv[1:]
    sys.argv = [sys.argv[0], "--source", SOURCE_MD, "--out", OUT_PDF, "--title", TITLE] + forwarded
    renderer.main()


if __name__ == "__main__":
    main()
