# Buildozer spec — Spectracs SERVER app (P5). Headless local Pyro5 server.
#
# Much simpler than the main app: NO PySide6 (so no cp311/Python-3.11 pin, no qt bootstrap),
# NO numpy/scipy/opencv. Uses MAINLINE p4a (default Python) + sdl2 bootstrap (launchable). The one
# native dep is bcrypt -> cffi -> libffi/openssl (all p4a recipes). Entry runs
# SpectracsPyServer.serveLocalForever() (fixed URI 127.0.0.1:8091, no nameserver).
# NOTE: this is a SEPARATE buildozer project from android/spike (which is patched for python 3.11.9 +
# scipy); the server must NOT use those patches. Global SDK/NDK (~/.buildozer) are reused.

[app]
title = Spectracs Server
package.name = spectracsserver
package.domain = at.sciens
source.dir = ./app_src
source.include_exts = py
version = 0.1

# Pure-python (Pyro5/SQLAlchemy/marshmallow/serpent/typing_extensions) + bcrypt (native via cffi).
# pyjnius+android: the launcher activity (main.py) uses them to start the foreground service and
# request the notification permission.
requirements = python3,Pyro5,serpent,SQLAlchemy,sqlalchemy-serializer,marshmallow,marshmallow-sqlalchemy,typing_extensions,pycparser,bcrypt,pyjnius,android

orientation = portrait
fullscreen = 0

# The Pyro5 daemon runs in a FOREGROUND SERVICE (separate `:service_pyro` process) so it survives the
# activity being backgrounded/closed. main.py (activity) starts it; service_pyro.py is its entrypoint.
# foregroundServiceType=dataSync (+ its permission) is required on Android 14+ (API 34 target); ignored
# on the API 33 test device. Class name becomes at.sciens.spectracsserver.ServicePyro.
services = pyro:service_pyro.py:foreground:foregroundServiceType=dataSync

android.archs = arm64-v8a
android.api = 34
android.minapi = 24
android.ndk_path = /home/nidwe72/.buildozer/android/platform/android-ndk-r28c
# Loopback RPC to the client app + foreground-service plumbing (FGS + its dataSync subtype + the
# runtime notification permission the FGS notification needs on Android 13+).
android.permissions = android.permission.INTERNET,android.permission.FOREGROUND_SERVICE,android.permission.FOREGROUND_SERVICE_DATA_SYNC,android.permission.POST_NOTIFICATIONS

# Mainline p4a, default (unpatched) Python — NO qt bootstrap, NO 3.11.9 pin.
p4a.bootstrap = sdl2
p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 1
