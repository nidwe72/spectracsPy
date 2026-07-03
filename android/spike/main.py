"""P0 composition spike (docs/SPEC_android_port.md P0).

Proves the load-bearing assumption of the whole Android port: that PySide6 + scipy + cv2 + a
`sciens.*` import spanning the 4 repos all run together under the python-for-android runtime on a
real device.

GO  = the screen shows "scipy ... OK", "cv2 ... OK", and "sciens.* ... OK" with numeric results.
NO-GO = any line shows FAIL → escalate (K3 was opted out; no silent fallback). See README.md.
"""
import sys
import traceback

from PySide6 import QtWidgets


def _run_checks():
    lines = []

    try:
        import numpy as np
        lines.append(f"numpy {np.__version__} OK")
    except Exception as e:
        lines.append(f"numpy FAIL: {e!r}")

    try:
        import numpy as np
        import scipy
        from scipy.signal import find_peaks
        peaks, _ = find_peaks(np.array([0, 2, 0, 5, 0, 3, 0], dtype=float))
        sv = np.linalg.svd(np.array([[1.0, 2.0], [3.0, 4.0]]), compute_uv=False)
        lines.append(f"scipy {scipy.__version__} OK  peaks={peaks.tolist()}  svd0={sv[0]:.3f}")
    except Exception as e:
        lines.append(f"scipy FAIL: {e!r}")

    try:
        import numpy as np
        import cv2
        gray = cv2.cvtColor(np.zeros((4, 4, 3), dtype=np.uint8), cv2.COLOR_BGR2GRAY)
        lines.append(f"cv2 {cv2.__version__} OK  gray={gray.shape}")
    except Exception as e:
        lines.append(f"cv2 FAIL: {e!r}")

    try:
        # base repo + model repo — proves the PEP-420 sciens.* namespace bundles across repos.
        from sciens.base.PlatformUtil import is_android
        from sciens.spectracs.model.databaseEntity.AppDataPathUtil import get_app_data_dir
        lines.append(f"sciens.* OK  android={is_android()}  dir={get_app_data_dir()}")
    except Exception as e:
        lines.append(f"sciens.* FAIL: {e!r}\n{traceback.format_exc()}")

    return "\n".join(lines)


def main():
    app = QtWidgets.QApplication(sys.argv)
    widget = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(widget)
    title = QtWidgets.QLabel("Spectracs · P0 composition spike")
    title.setStyleSheet("font-size: 22px; font-weight: bold;")
    layout.addWidget(title)
    output = QtWidgets.QPlainTextEdit()
    output.setReadOnly(True)
    output.setStyleSheet("font-size: 18px;")
    output.setPlainText(_run_checks())
    layout.addWidget(output)
    widget.showFullScreen()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
