#!/bin/bash
# Spectracs AppImage launcher — docs/SPEC_linux_appimage.md §5.2.
# The server is NOT bundled (D1): start it yourself before launching (see §17.1).
HERE="$(dirname "$(readlink -f "$0")")"
BIN="$HERE/usr/bin/spectracs"
export LD_LIBRARY_PATH="$HERE/usr/lib:$BIN${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

case "$1" in --fresh) SUFFIX="-demo"; shift;; *) SUFFIX="";; esac

# D2: the process CWD selects the data directory — appdata resolves ~/.<basename of cwd>.
# No suffix  -> ~/.spectracsPy       (the real archive + prepProtocol.txt)
# --fresh    -> ~/.spectracsPy-demo  (virgin; NEVER for a real measurement — no lab recipe)
APP_CWD="${SPECTRACS_CWD_ROOT:-$HOME/Spectracs}/spectracsPy$SUFFIX"
mkdir -p "$APP_CWD"

cat "$HERE/RELEASE_MANIFEST.txt" 2>/dev/null
cd "$APP_CWD" || exit 1

# 8e.4: double-clicked there is no console. Keep stderr (tracebacks, Qt warnings) in a file.
# NOTE (measured): the frozen app's print() output does NOT reach a redirected stdout — only
# stderr does. So this log holds errors, not the capture diagnostics. Run from a terminal for those.
if [ ! -t 2 ]; then exec 2>> "$APP_CWD/spectracs.log"; fi

exec "$BIN/spectracsMain" "$@"
