# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the SERVER AppImage — docs/SPEC_linux_appimage.md §19.

Measured, and the reason this is a separate file rather than weight inside the app image: the server's
import graph pulls NO numpy, scipy, matplotlib, cv2, PySide6, pandas or PIL, and it needs only three
repos — -server, -model, -base. (runServer.sh's comment about needing the app repo for
SpectralLineMasterDataUtil is STALE: that class lives in -model since the tiering work.)
"""
import os

# TWO roots, and they are not the same thing (8g.6):
#   SRC    — the TAGGED sources the bundle is built FROM (SPECTRACS_SRC_ROOT, set by the build script)
#   RECIPE — where this spec and its entry script live, which may be NEWER than the tag (8f.4)
# Getting this wrong is silent: point both at the worktree and PyInstaller cannot find a post-tag entry
# script; point both at the live tree and the bundle is built from unfrozen sources.
SRC = os.path.abspath(os.environ.get("SPECTRACS_SRC_ROOT", SPECPATH))     # …/spectracsPy (tagged)
RECIPE = os.path.abspath(SPECPATH)                                        # …/spectracsPy (live)
SIBLINGS = os.path.dirname(SRC)

def sibling(name):
    return os.path.join(SIBLINGS, name)

PATHEX = [sibling(n) for n in ("spectracsPy-server", "spectracsPy-model", "spectracsPy-base")]

def tree(sourceDir, targetDir):
    result = []
    for root, dirs, files in os.walk(sourceDir):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in files:
            if name.endswith(".pyc"):
                continue
            rel = os.path.relpath(root, sourceDir)
            result.append((os.path.join(root, name), os.path.join(targetDir, rel) if rel != "." else targetDir))
    return result

# The server process owns spectracsPyServer.db and runs initServerDatabase() at boot; DatabaseInitializer
# resolves the trees four levels up from its own __file__, so they must sit at the bundle root. Both trees
# ship — the app tree is ~50 KB and it is cheaper than betting on having enumerated every path.
datas = tree(os.path.join(sibling("spectracsPy-model"), "alembic"), "alembic")

hiddenimports = [
    "spectracsPyServer",                                          # reached only via the argv dispatch
    "sciens.spectracs.model.databaseEntity.AllEntities",          # imported for its metadata side effect
]

# Nothing graphical or numerical belongs in a headless Pyro daemon. Verified by import: none of these
# appear in the server's module graph, so excluding them is a guard, not a removal.
excludes = [
    "PySide6", "pyqtgraph", "shiboken6", "cv2", "matplotlib", "PIL", "colour", "luxpy", "pandas",
    "colormath", "scipy", "spectres", "rgbxy", "pypdf", "astropy", "pyspectra", "usb", "psutil",
    "tkinter", "IPython", "pytest", "sphinx", "notebook", "jupyter",
]

a = Analysis(
    [os.path.join(RECIPE, "spectracsServerAppImageEntry.py")],   # the recipe, not the tag
    pathex=PATHEX,
    binaries=[],
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

_leaked = [e[0] for e in list(a.binaries) + list(a.datas)
           if any(bad in e[0] for bad in ("PySide6", "libQt6", "cv2", "matplotlib"))]
if _leaked:
    raise SystemExit("SERVER BUNDLE GATE FAILED — GUI/science artefacts leaked in: %s" % _leaked[:5])

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="spectracsServer",
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=True, disable_windowed_traceback=False, argv_emulation=False,
          target_arch=None, codesign_identity=None, entitlements_file=None)

coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=False, upx_exclude=[],
               name="spectracsServer")
