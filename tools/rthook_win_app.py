"""PyInstaller runtime hook of the WINDOWS app — the twin of AppRun.app (SPEC_windows_build.md D4, D5).

Runs before PyInstaller's own pyi_rth_* hooks and before spectracsMain.py, in the same __main__ namespace:

  - chdir to <root>\\spectracsPy[-demo] before anything imports appdata, which names the data dir after the cwd
    (a double-clicked exe would otherwise get a DB named after the zip folder, B7). --fresh, anywhere in argv,
    is stripped and selects -demo; root = SPECTRACS_CWD_ROOT or <home>\\Spectracs.
  - stdout/stderr -> spectracs.log in that folder, UTF-8 (the windowed exe has none, B8; cp1252 would choke on
    the "→" in our prints, U7), with a start banner; faulthandler into the same file for native crashes.

The side effects run only in a frozen build; tests load this file and call _plan/_apply directly (U14). Wired
into spectracsAppImage.spec on win32 only.
"""
import sys


def _plan(argv, environ, home):
    """-> (cwd, argv without --fresh, log path)."""
    import os
    suffix = "-demo" if "--fresh" in argv[1:] else ""
    newArgv = argv[:1] + [arg for arg in argv[1:] if arg != "--fresh"]
    root = environ.get("SPECTRACS_CWD_ROOT") or os.path.join(home, "Spectracs")
    cwd = os.path.join(root, "spectracsPy" + suffix)
    return cwd, newArgv, os.path.join(cwd, "spectracs.log")


def _apply(plan, sysmod, osmod):
    """Move into the data folder, rewrite argv, point stdout/stderr at the log. Returns the open log file."""
    import datetime
    cwd, argv, logPath = plan
    osmod.makedirs(cwd, exist_ok=True)
    osmod.chdir(cwd)
    sysmod.argv[:] = argv
    log = open(logPath, "a", buffering=1, encoding="utf-8", errors="backslashreplace")
    sysmod.stdout = log
    sysmod.stderr = log
    print("==== Spectracs start %s ====" % datetime.datetime.now().isoformat(timespec="seconds"), file=log)
    manifest = osmod.path.join(osmod.path.dirname(sysmod.executable), "RELEASE_MANIFEST.txt")
    if osmod.path.isfile(manifest):
        with open(manifest, encoding="utf-8", errors="backslashreplace") as manifestFile:
            log.write(manifestFile.read())
    else:  # the by-hand builds W0.4/W0.5 have no manifest yet (U18)
        print("executable: %s" % sysmod.executable, file=log)
    print("argv: %s" % argv, file=log)
    return log


if getattr(sys, "frozen", False):
    import faulthandler as _faulthandler
    import os as _os
    import pathlib as _pathlib
    _log = _apply(_plan(sys.argv, _os.environ, str(_pathlib.Path.home())), sys, _os)
    _faulthandler.enable(_log)
    # hooks share __main__ with spectracsMain.py: leave nothing behind but the open log (kept alive by sys.stdout)
    del _plan, _apply, _log, _faulthandler, _os, _pathlib
