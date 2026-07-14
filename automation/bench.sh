#!/usr/bin/env bash
# One-command measurement-bench run. Launches the app (--doc-mode) in the background, then attaches the
# Director to drive it — no copy/paste of multiple commands. You still: (1) log in as masterUserExakta and
# confirm a CALIBRATED real setup when the Prompter asks, then CONTINUE; (2) do the physical beats (insert
# reference + lamp, swap sample). Real camera → real frames, so no virtual-image setup needed.
set -e
cd "$(dirname "$0")/.."
export PYTHONPATH=".:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server"

# record the whole run to automation/recordings/bench_<timestamp>.mp4 (ffmpeg x11grab). Pass "norecord"
# to skip. The Director starts/stops ffmpeg itself.
if [ "${1:-}" != "norecord" ]; then
  export DOC_RECORD=1 DOC_RECORD_NAME=bench
fi

# fresh start: clear any stale --doc-mode app (never touches a normal Spectracs window) and any orphaned
# screen recorder left behind by a hard-killed prior run (else it keeps grabbing the screen forever).
pkill -f "spectracsMain.py --doc-mode" 2>/dev/null || true
pkill -f "ffmpeg -y -f x11grab" 2>/dev/null || true
sleep 1

# launch the app detached; its log goes to a temp file
APP_LOG="${TMPDIR:-/tmp}/spectracs_docmode_app.log"
nohup ./runApp.sh --doc-mode > "$APP_LOG" 2>&1 &
echo "bench.sh: launched app (--doc-mode); log -> $APP_LOG"

# attach the Director; it polls until the app answers, shows the Prompter, then drives the bench
DOC_ATTACH=1 exec ./venv/bin/python automation/scenarios/measurement_bench.py
