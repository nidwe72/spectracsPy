#!/usr/bin/env bash
# One-command M0 capture-quality probe (SPEC_capture_quality.md §4). Sets the app PYTHONPATH + venv and
# forwards all args to the probe. Run on the rig with the real camera + lamp attached.
#
#   diagnostics/probe.sh --device 0 --roi X1,Y1,X2,Y2 --coeffs A,B,C,D
#
# ROI (regionOfInterestX1/Y1/X2/Y2) and cubic (interpolationCoefficientA..D) are on the active
# SpectrometerCalibrationProfile; omit them to let the probe auto-resolve from the app context (works only
# when a spectrometer profile is populated). Offscreen self-test (no rig): diagnostics/probe.sh --selftest
set -e
cd "$(dirname "$0")/.."
export PYTHONPATH=".:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server"
exec ./venv/bin/python diagnostics/capture_quality_probe.py "$@"
