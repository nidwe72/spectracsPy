#!/usr/bin/env bash
# Smoke-test the Spectracs SERVER app on a USB-connected device.
#
#   ./test_server.sh            # launch + check foreground service + real login RPC + survival
#   ./test_server.sh --install  # (re)install the APK first
#
# Needs: adb on PATH, a device with USB debugging, and the desktop venv (has Pyro5).
set -uo pipefail

PKG=at.sciens.spectracsserver
ACT="$PKG/org.kivy.android.PythonActivity"
HERE="$(cd "$(dirname "$0")" && pwd)"
APK="$HERE/bin/spectracsserver-0.1-arm64-v8a-debug.apk"
VP=/home/nidwe72/development/spectracs/spectracsPy/venv/bin/python
URI="PYRO:sciens.spectracs.spectracsPyServer@127.0.0.1:18091"

hr(){ printf '\n=== %s ===\n' "$1"; }

if [[ "${1:-}" == "--install" ]]; then
    hr "install"; adb install -r "$APK" | tail -1
fi

hr "launch (am start — NOT monkey: Samsung monkey can onStop before SDL_main)"
adb shell am force-stop "$PKG"; sleep 1
adb shell am start -n "$ACT" | tail -1
echo "waiting for the service process to boot..."; sleep 14

hr "processes (want the activity AND :service_pyro)"
adb shell ps -A | grep -i spectracsserver | awk '{print $2, $9}'

hr "foreground service state"
adb shell dumpsys activity services "$PKG" | grep -iE "ServicePyro|isForeground" | head -3

hr "real login RPC over loopback (adb forward -> device 8091)"
adb forward tcp:18091 tcp:8091 >/dev/null
timeout 15 "$VP" - <<PY
import Pyro5.api
p = Pyro5.api.Proxy("$URI")
print("login:", p.login("endUser", "endUser"))
PY

hr "survival: HOME + kill backgroundable procs, then hit it again"
adb shell input keyevent KEYCODE_HOME; sleep 3
adb shell am kill "$PKG"; sleep 6
echo "activity should be gone, :service_pyro should remain:"
adb shell ps -A | grep -i spectracsserver | awk '{print $2, $9}'
timeout 15 "$VP" -c "import Pyro5.api; p=Pyro5.api.Proxy('$URI'); print('SURVIVED login ok:', p.login('endUser','endUser')['ok'])"
adb forward --remove tcp:18091 >/dev/null 2>&1

hr "done"
echo "On the phone you should also see a notification: 'Spectracs Server / Serving locally on 127.0.0.1:8091'"
