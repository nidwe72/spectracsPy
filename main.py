"""python-for-android entry point for the Spectracs MAIN app (P1).

p4a launches ``main.py``. On desktop the four sibling repos are placed on PYTHONPATH by runApp.sh;
inside the APK they are bundled together. This shim makes the sibling source roots importable when
present (harmless if already importable), then runs the real entry module.
"""
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
_parent = os.path.dirname(_here)
for _sibling in ("spectracsPy-model", "spectracsPy-base", "spectracsPy-server"):
    _path = os.path.join(_parent, _sibling)
    if os.path.isdir(_path) and _path not in sys.path:
        sys.path.insert(0, _path)
if _here not in sys.path:
    sys.path.insert(0, _here)

import spectracsMain  # noqa: E402,F401  — importing runs the application
