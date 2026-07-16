#!/usr/bin/env bash
# Launch the Spectracs desktop app.
# The sibling repos (model/base/server) are PEP-420 namespace packages on PYTHONPATH;
# spectracsPy-server is required because the server-sync client imports from it.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
export PYTHONPATH=".:../spectracsPy-core:../spectracsPy-model:../spectracsPy-base:../spectracsPy-server"
exec ./venv/bin/python spectracsMain.py "$@"
