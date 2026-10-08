"""PyInstaller runtime hook of the WINDOWS server — the twin of AppRun.server (SPEC_windows_build.md D4).

Runs before spectracsServerAppImageEntry.py, in the same __main__ namespace:

  - chdir to <root>\\spectracsPy-server (root = SPECTRACS_CWD_ROOT or <home>\\Spectracs), so appdata puts the
    server DB in %USERPROFILE%\\spectracsPy-server wherever the zip was unpacked (B7).
  - PYRO_SOCK_REUSE=false: Pyro5 defaults to SO_REUSEADDR, which on Windows lets a second daemon bind 8091
    silently (S4). Pyro5 reads PYRO_* when it is imported, i.e. after this hook (U15).
  - with no arguments (the loopback mode) refuse when 127.0.0.1:8091 is already taken (§8g.3 of the Linux spec).
  - ⛔ never touches argv: any argument switches the entry to the stock CLI.
  - the server keeps its console window (D5) — nothing is redirected; only stdout's errors are made lenient (U7).

The side effects run only in a frozen build; tests call the helpers directly (U14). Wired into
spectracsServerAppImage.spec on win32 only.
"""
import sys

_LOOPBACK_PORT = 8091


def _plan(environ, home):
    """-> the server's working folder."""
    import os
    root = environ.get("SPECTRACS_CWD_ROOT") or os.path.join(home, "Spectracs")
    return os.path.join(root, "spectracsPy-server")


def _portTaken(port, host="127.0.0.1"):
    import socket
    try:
        socket.create_connection((host, port), timeout=1).close()
        return True
    except OSError:
        return False


def _apply(cwd, argv, environ, sysmod, osmod, port=_LOOPBACK_PORT):
    """Move into the server folder and harden Pyro. Returns False when the loopback port is already taken."""
    osmod.makedirs(cwd, exist_ok=True)
    osmod.chdir(cwd)
    environ["PYRO_SOCK_REUSE"] = "false"
    if sysmod.stdout is not None and hasattr(sysmod.stdout, "reconfigure"):
        sysmod.stdout.reconfigure(errors="backslashreplace")
    if len(argv) == 1 and _portTaken(port):
        print("SpectracsServer: 127.0.0.1:%d is already in use - another server is running; not starting a second"
              % port, file=sysmod.stdout, flush=True)
        return False
    return True


if getattr(sys, "frozen", False):
    import os as _os
    import pathlib as _pathlib
    if not _apply(_plan(_os.environ, str(_pathlib.Path.home())), sys.argv, _os.environ, sys, _os):
        _os._exit(1)
    del _plan, _portTaken, _apply, _os, _pathlib, _LOOPBACK_PORT
