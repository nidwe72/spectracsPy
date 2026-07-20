#!/usr/bin/env bash
# Run the capture diagnosis script (SPEC_capability_proof.md §7.0.1 — reference gray-outlier investigation).
# INTEGRATION: needs the real ELP camera connected AND the local server running (runServer.sh --local), because
# the calibration is resolved through a server RPC (masterUserExakta's SpectrometerSetup). Same PYTHONPATH as
# runApp.sh (the sibling repos are PEP-420 namespace packages).
#
# Password: export SPECTRACS_DIAG_PASSWORD, or the script prompts. Per-frame JSON -> ./captureDiagnostics
# (override with SPECTRACS_LOG_SPECTRA). Any extra args pass through to diagnoseCapture.py.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
export PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins"
exec ./venv/bin/python diagnoseCapture.py "$@"
