#!/usr/bin/env python3
"""
Generator for the internal *The DN Budget of the Red Band* documentation PDF.

    SOURCE OF TRUTH:  docs/DOC_red_band_budget.md   <- edit the prose THERE, never the PDF
    OUTPUT:           ../spectracs-docs/internal/Spectracs_RedBandBudget.pdf

The instrument-side companion to *The Jar in the Beam*: that document asks what the jar does to the
beam, this one asks how many camera counts are left by the time the verdict band is reached. The
rendering is done by the capture-fidelity renderer; this script only supplies source, output and title.

The numbers and both figures come from:
    PYTHONPATH="./diagnostics:.:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracs-plugins" \
        ./venv/bin/python diagnostics/red_band_budget.py
Re-run it before regenerating this PDF.

HOW TO REGENERATE
-----------------
    python3 docs/tools/build_red_band_budget_pdf.py
"""
import os
import sys

import build_capture_fidelity_pdf as renderer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SOURCE_MD = os.path.join(REPO, "docs", "DOC_red_band_budget.md")
OUT_PDF = os.path.abspath(os.path.join(
    REPO, "..", "spectracs-docs", "internal", "Spectracs_RedBandBudget.pdf"))
TITLE = "Spectracs — The DN Budget of the Red Band"


def main():
    forwarded = sys.argv[1:]
    sys.argv = [sys.argv[0], "--source", SOURCE_MD, "--out", OUT_PDF, "--title", TITLE] + forwarded
    renderer.main()


if __name__ == "__main__":
    main()
