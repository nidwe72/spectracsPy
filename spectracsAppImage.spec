# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Linux AppImage build — docs/SPEC_linux_appimage.md.

Entry is spectracsMain.py itself: the server is NOT part of the AppImage (D1), so no shim is needed.
Paths resolve from SPECPATH, not the process cwd, so a build launched from anywhere still finds the
five sibling repos (SPEC §8b.6).
"""
import os
import glob

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# 8g.1: the build script must be able to point a spec (which may be newer than the frozen tag) at the
# TAGGED worktree sources. SPECTRACS_SRC_ROOT does that; unset, behaviour is exactly as before.
HERE = os.path.abspath(os.environ.get("SPECTRACS_SRC_ROOT", SPECPATH))   # …/spectracsPy
SIBLINGS = os.path.dirname(HERE)

def sibling(name):
    return os.path.join(SIBLINGS, name)

# --- the five namespace-merged repos (PEP 420). -server carries SpectracsServerEndpoint +
# --- SqlAlchemySerializer, which the CLIENT imports; the @expose server impl is never imported
# --- by the app and so never lands in the bundle (SPEC D1).
PATHEX = [sibling(n) for n in ("spectracsPy-core", "spectracsPy-model", "spectracsPy-base",
                               "spectracsPy-server", "spectracs-plugins")]

# --- datas -------------------------------------------------------------------------------------
def tree(sourceDir, targetDir):
    """Every file under sourceDir -> targetDir, __pycache__ dropped. Alembic loads env.py and the
    versions/*.py BY PATH, so they must ship as data, not as hidden imports (SPEC §2.7)."""
    result = []
    for root, dirs, files in os.walk(sourceDir):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in files:
            if name.endswith(".pyc"):
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(root, sourceDir)
            result.append((full, os.path.join(targetDir, rel) if rel != "." else targetDir))
    return result

datas = []
# DatabaseInitializer computes <-model root>/alembic/<db>/alembic.ini four levels up from its own
# __file__, which inside a frozen bundle is <bundle>/sciens/... -> the trees must sit at the root.
datas += tree(os.path.join(sibling("spectracsPy-model"), "alembic"), "alembic")
datas += tree(os.path.join(HERE, "resource"), "resource")          # logo.png (PDF), expectedDetection.png
datas += tree(os.path.join(HERE, "testSpectra"), "testSpectra")    # playground CFL calibration image
datas += collect_data_files("colour")                              # colour-science spectral data

# --- binaries ----------------------------------------------------------------------------------
# pyusb loads libusb through ctypes, which PyInstaller cannot follow. It drives only the connection
# indicator (the capture gate is the sysfs resolver), but isSensorConnected does not guard
# NoBackendError — so ship the library (SPEC §8.2).
binaries = []
for candidate in ("/lib/x86_64-linux-gnu/libusb-1.0.so.0", "/usr/lib/x86_64-linux-gnu/libusb-1.0.so.0"):
    if os.path.exists(candidate):
        binaries.append((candidate, "."))
        break

# --- hidden imports ----------------------------------------------------------------------------
hiddenimports = collect_submodules("pyqtgraph")        # pyqtgraph imports its submodules dynamically
hiddenimports += [
    # PluginRegistry resolves these from codeRef STRINGS via importlib — invisible to the analysis.
    "sciens.spectracs.plugins.pumpkin.PumpkinOilPlugin",
    "sciens.spectracs.plugins.dev.DevSpectralPlugin",
    # imported for its side effect: it populates both SQLAlchemy metadatas.
    "sciens.spectracs.model.databaseEntity.AllEntities",
]

# --- excludes ----------------------------------------------------------------------------------
# Only QtWidgets/QtCore/QtGui/QtSvg/QtNetwork are imported anywhere in the five repos.
# ⛔ QtCharts and QtDataVisualization are GPL/commercial, not LGPL: the whole QtCharts->pyqtgraph
# migration was done to get out from under that, so they must not ship (SPEC §8c.1).
excludes = [
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtQuick", "PySide6.QtQuick3D",
    "PySide6.QtQml", "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtDesigner",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtBluetooth", "PySide6.QtNfc",
    "PySide6.QtPositioning", "PySide6.QtSerialBus", "PySide6.QtSerialPort", "PySide6.QtTest",
    "PySide6.QtHelp", "PySide6.QtRemoteObjects", "PySide6.QtSensors", "PySide6.QtSql",
    "PySide6.QtWebSockets", "PySide6.QtWebChannel", "PySide6.QtSpatialAudio", "PySide6.QtScxml",
    "PySide6.QtStateMachine", "PySide6.QtTextToSpeech", "PySide6.Qt3DCore", "PySide6.Qt3DRender",
    "PySide6.Qt3DInput", "PySide6.Qt3DLogic", "PySide6.Qt3DAnimation", "PySide6.Qt3DExtras",
    # luxpy is a LAZY import with a plain-Gaussian fallback (UV-A LED synthesis only) and drags
    # pandas; colormath is dead code (SPEC_project_structure.md "Dead chain").
    "luxpy", "pandas", "colormath",
    "tkinter", "IPython", "pytest", "sphinx", "notebook", "jupyter",
    # D5: no Splash() in this build. Excluding PyInstaller's fake pyi_splash module turns
    # spectracsMain.py's bare `import pyi_splash` into a clean, caught ImportError instead of the
    # KeyError traceback the fake module prints to stderr at import time (measured, first build).
    "pyi_splash",
]

a = Analysis(
    [os.path.join(HERE, "spectracsMain.py")],
    pathex=PATHEX,
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

# --- the licence gate, enforced rather than hoped for (SPEC §8c.1 / N8) -------------------------
# PyInstaller's PySide6 hook is greedy about Qt/lib, Qt/qml and Qt/resources. Drop by name, then
# assert. WebEngineCore alone is 160 MB; Charts/DataVisualization are the licence problem.
FORBIDDEN = ("WebEngine", "Charts", "DataVisualization", "Quick3D", "Qt6Qml", "Qt6Quick",
             "Multimedia", "Designer", "Bluetooth", "Qt63D")
DROP_DATA_DIRS = ("PySide6/Qt/qml", "PySide6/Qt/resources", "PySide6/Qt/translations",
                  "PySide6/translations", "PySide6/examples", "PySide6/glue")

def _keepBinary(entry):
    name = entry[0]
    return not any(bad in name for bad in FORBIDDEN)

def _keepData(entry):
    name = entry[0].replace("\\", "/")
    if any(name.startswith(d) or ("/" + d) in name for d in DROP_DATA_DIRS):
        return False
    return not any(bad in name for bad in FORBIDDEN)

a.binaries = TOC([e for e in a.binaries if _keepBinary(e)])
a.datas = TOC([e for e in a.datas if _keepData(e)])

_leaked = [e[0] for e in list(a.binaries) + list(a.datas)
           if any(bad in e[0] for bad in ("Charts", "DataVisualization", "WebEngine"))]
if _leaked:
    raise SystemExit("LICENCE GATE FAILED — GPL/unused Qt modules still in the bundle: %s" % _leaked[:5])

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,          # onedir: AppImage already compresses; onefile would re-extract
    name="spectracsMain",           # AppRun execs this
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                      # UPX breaks Qt shared libraries
    console=True,                   # the app prints capture diagnostics; AppRun tees them when no tty
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="spectracsMain",
)
