#!/usr/bin/env bash
# Re-stage android/spike/app_src for the MAIN app from the current source repos.
#
# app_src is a gitignored build artifact: the p4a shim `main.py`, the real entry `spectracsMain.py`,
# and a MERGED `sciens/` namespace assembled from all four sibling repos (model/base/server/app).
# Run this before a main-app rebuild so the APK picks up committed source changes. Idempotent.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"          # .../spectracsPy/android/spike
DST="$HERE/app_src"
APP="$(cd "$HERE/../.." && pwd)"               # .../spectracsPy
ROOT="$(cd "$APP/.." && pwd)"                  # .../spectracs (repo siblings live here)

mkdir -p "$DST"
rm -rf "$DST/sciens"
for repo in spectracsPy-model spectracsPy-base spectracsPy-server spectracsPy; do
    if [ -d "$ROOT/$repo/sciens" ]; then
        rsync -a --exclude='__pycache__' --exclude='*.pyc' "$ROOT/$repo/sciens/" "$DST/sciens/"
    fi
done

# The real entry module lives at app_src root; the p4a shim main.py imports it. main.py is
# app_src-specific (not sourced from a repo), so it is preserved as-is.
cp "$APP/spectracsMain.py" "$DST/spectracsMain.py"

echo "staged app_src/sciens from: model, base, server, app  (+ spectracsMain.py)"
echo "main.py (p4a shim): $( [ -f "$DST/main.py" ] && echo present || echo MISSING )"
