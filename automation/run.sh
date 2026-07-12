#!/usr/bin/env bash
# Run a doc-automation scenario with the app's PYTHONPATH (SPEC_doc_automation).
# Usage:  ./automation/run.sh <scenario>
#   e.g.  ./automation/run.sh _smoke
#         ./automation/run.sh pumpkin_wizard
#         ./automation/run.sh measurement_bench
set -e
cd "$(dirname "$0")/.."
export PYTHONPATH=".:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server"
scenario="${1:?usage: ./automation/run.sh <scenario> [bypass|attach]  (e.g. pumpkin_wizard)}"
shift || true
flags=" $* "   # remaining args as space-delimited flags

# "bypass": auto-log-in a synthetic master + pumpkin-plugin (virtual device) session so a no-hardware
# scenario can run without a manual login. Dev-only. The codeRef is the full module.Class path (the
# app-side default omits the trailing class segment).
if [[ "$flags" == *" bypass "* ]]; then
  export SPECTRACS_DEV_LOGIN_BYPASS=1
  export SPECTRACS_DEV_PLUGIN_CODEREF="sciens.spectracs.logic.spectral.plugin.pumpkin.PumpkinOilPlugin.PumpkinOilPlugin"
  # Preload the virtual reference/sample/calibration images so the wizard can capture with no hardware.
  export SPECTRACS_DEV_VIRTUAL_CAPTURES="$PWD/../spectracs-references/pumpkin_oil/virtual_captures/pumpkinoil_perfect_v1"
fi

# "record": capture the whole run to automation/recordings/<scenario>_<timestamp>.mp4 via ffmpeg.
if [[ "$flags" == *" record "* ]]; then
  export DOC_RECORD=1 DOC_RECORD_NAME="$scenario"
fi

# "attach": drive an app the operator already launched + prepared (logged in, calibrated) instead of
# spawning a fresh one — required for the bench. In attach mode we must NOT kill the running app.
if [[ "$flags" == *" attach "* ]]; then
  export DOC_ATTACH=1
else
  # Clear any stale --doc-mode app still holding UDP :5555 (e.g. a previous run left on its CONTINUE
  # prompt). Only ever matches doc-mode instances, never a normal Spectracs window.
  pkill -f "spectracsMain.py --doc-mode" 2>/dev/null || true
  sleep 1
fi
exec ./venv/bin/python "automation/scenarios/${scenario}.py"
