#!/usr/bin/env bash
# Launch the Spectracs desktop app.
# The sibling repos (core/model/base/server/plugins) are PEP-420 namespace packages on PYTHONPATH;
# spectracsPy-server is required because the server-sync client imports from it; spectracs-plugins carries
# the SpectralPlugin subclasses (S5) — resolved by plain import until M3-B3's DB loader replaces that.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
export PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server:../spectracs-plugins"
exec ./venv/bin/python spectracsMain.py "$@"
