"""P3 smoke gate (SPEC_doc_automation §10 step 0).

Proves the whole Director<->app seam on a DEAD-SIMPLE, always-present widget — the status-bar logo box
("logoBox") — before any real scenario. If the cursor visibly glides to the logo and clicks, and the hint
panel updates, then flag + panel + UDP + Director all talk to each other. No hardware, no navigation.

Run:  python automation/scenarios/_smoke.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from automation.automation_director import main


def run(d):
    d.launch_app()
    d.set_hint("Smoke test — proving the Director↔app seam.")
    d.prompt("Watch the cursor glide to the Spectracs logo, then click CONTINUE.")
    d.sleep(1)
    d.click("logoBox")            # always present in the status bar, any view
    d.screenshot("smoke_logo")
    d.wait_for_human("Seam proven — the cursor reached the logo and the hint updated.\n"
                     "Click CONTINUE to close.")


if __name__ == "__main__":
    main(run, title="Smoke test")
