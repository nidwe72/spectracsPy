# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# pyqtgraph imports its submodules dynamically (graphics items, the Qt binding
# shim, colormaps), so PyInstaller cannot discover them statically - collect them
# explicitly (QtCharts->pyqtgraph migration, docs/SPEC_pyside6_and_android.md).
pyqtgraph_hiddenimports = collect_submodules('pyqtgraph')

a = Analysis(
    ['spectracsMain.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Windows\\System32\\libusb0.dll', '.'),],
    hiddenimports=["pyi_splash"] + pyqtgraph_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
splash = Splash(
    './resource/splash.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    text_size=12,
    minify_script=True,
    always_on_top=False,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    splash,
    splash.binaries,
    [],
    name='spectracsMain',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
