#!/usr/bin/env bash
# Build the Spectracs Linux AppImages — docs/SPEC_linux_appimage.md §19.1.
#
#   tools/buildAppImages.sh [--app] [--server] [--tag <tag>] [--out <name|path>] [--keep N] [--no-verify]
#
# Defaults: both images · --tag presentation-2026-09-12 · --out <ISO timestamp> · --keep 3
#
# The build ALWAYS runs against git worktrees of the tag (never the live tree), and never writes into
# any repository. Two roots are kept apart on purpose (§8g.1/8g.6): SPECTRACS_SRC_ROOT points the specs
# at the TAGGED sources, while the spec + entry files themselves come from this checkout and may be
# newer than the tag. Both facts land in each RELEASE_MANIFEST.txt.
set -euo pipefail

TAG="presentation-2026-09-12"
OUT=""
KEEP=3
DO_APP=""; DO_SERVER=""; VERIFY=1
BUILD_ROOT="${SPECTRACS_BUILD_ROOT:-$HOME/spectracs-build}"

while [ $# -gt 0 ]; do
  case "$1" in
    --app)        DO_APP=1 ;;
    --server)     DO_SERVER=1 ;;
    --tag)        TAG="$2"; shift ;;
    --out)        OUT="$2"; shift ;;
    --keep)       KEEP="$2"; shift ;;
    --no-verify)  VERIFY=0 ;;
    -h|--help)    sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done
[ -z "$DO_APP$DO_SERVER" ] && { DO_APP=1; DO_SERVER=1; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"      # …/spectracsPy
REPOS_DIR="$(dirname "$HERE")"
VENV="$HERE/venv/bin"
REPOS="spectracsPy spectracsPy-core spectracsPy-model spectracsPy-base spectracsPy-server spectracs-plugins spectracs-docs"
say() { printf "\n\033[1m== %s\033[0m\n" "$*"; }

# ---------------------------------------------------------------- target folder
if [ -n "$OUT" ]; then
  case "$OUT" in */*) TARGET="$(readlink -f "$OUT")" ;; *) TARGET="$BUILD_ROOT/$OUT" ;; esac
  NAMED=1
else
  TARGET="$BUILD_ROOT/$(date +%Y-%m-%dT%H-%M-%S)"
  NAMED=0
fi
# §8b.2: PyInstaller writes build/ and dist/; .gitignore covers neither. Never inside a repo.
if git -C "$(dirname "$TARGET")" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "REFUSING: $TARGET is inside a git work tree (see SPEC §8b.2)." >&2; exit 1
fi
mkdir -p "$TARGET"
rm -rf "$TARGET/work" "$TARGET/dist" "$TARGET"/*.AppDir "$TARGET"/*.AppImage
say "target: $TARGET  (named=$NAMED)"

# ---------------------------------------------------------------- worktrees at the tag
SRC="$BUILD_ROOT/src-$TAG"
say "worktrees: $SRC"
mkdir -p "$SRC"
for repo in $REPOS; do
  if [ ! -d "$SRC/$repo/.git" ] && [ ! -f "$SRC/$repo/.git" ]; then
    git -C "$REPOS_DIR/$repo" worktree add -q --detach "$SRC/$repo" "$TAG"
  fi
  printf "  %-20s %s\n" "$repo" "$(git -C "$SRC/$repo" rev-parse --short HEAD)"
  [ -n "$(git -C "$SRC/$repo" status --porcelain)" ] && { echo "REFUSING: worktree $repo is dirty" >&2; exit 1; }
done
export SPECTRACS_SRC_ROOT="$SRC/spectracsPy"

# ---------------------------------------------------------------- helpers
APPIMAGETOOL="$BUILD_ROOT/appimagetool-x86_64.AppImage"
[ -x "$APPIMAGETOOL" ] || { echo "missing $APPIMAGETOOL — download it once from AppImageKit releases" >&2; exit 1; }

makeIcon() {  # $1 = output png, $2 = "frame" to draw the brand-green border (server) or "" (app)
  "$VENV/python" - "$1" "${2:-}" <<'PY'
import sys, os
from PIL import Image, ImageDraw
import numpy as np
out, frame = sys.argv[1], sys.argv[2]
logo = os.path.join(os.environ["SPECTRACS_SRC_ROOT"], "resource", "logo.png")
src = Image.open(logo).convert("RGBA"); a = np.array(src); alpha = a[:, :, 3]
cols = (alpha > 10).any(axis=0); runs = []; s = None
for i, v in enumerate(cols):
    if v and s is None: s = i
    if not v and s is not None: runs.append((s, i)); s = None
x0, x1 = runs[0]                                   # the S — §16
rows = (alpha[:, x0:x1] > 10).any(axis=1); ys = np.where(rows)[0]
glyph = src.crop((x0, ys[0], x1, ys[-1] + 1))
green = tuple(int(v) for v in a[np.unravel_index(alpha.argmax(), alpha.shape)][:3])
icon = Image.new("RGBA", (256, 256), (26, 26, 26, 255))
size = 150 if frame else 168
sc = size / max(glyph.size)
g = glyph.resize((int(glyph.width * sc), int(glyph.height * sc)), Image.LANCZOS)
icon.paste(g, ((256 - g.width) // 2, (256 - g.height) // 2), g)
if frame:
    ImageDraw.Draw(icon).rectangle([4, 4, 251, 251], outline=green + (255,), width=8)
icon.save(out)
PY
}

contentShas() { for r in "$@"; do printf "  %-20s %s\n" "$r" "$(git -C "$SRC/$r" rev-parse HEAD)"; done; }
RECIPE_SHA="$(git -C "$HERE" rev-parse --short HEAD)"
BUILT_AT="$(date -Iseconds)"

# ---------------------------------------------------------------- the app image
if [ -n "$DO_APP" ]; then
  say "building the APP"
  "$VENV/pyinstaller" --noconfirm --clean --log-level ERROR \
    --workpath "$TARGET/work/app" --distpath "$TARGET/dist/app" "$HERE/spectracsAppImage.spec"
  # N8 — the licence gate, re-checked on the artefact and not only inside the spec
  if find "$TARGET/dist/app" \( -iname "*Charts*" -o -iname "*DataVisualization*" -o -iname "*WebEngine*" \) | grep -q .; then
    echo "LICENCE GATE FAILED — GPL/unused Qt modules in the bundle" >&2; exit 1
  fi
  AD="$TARGET/Spectracs.AppDir"
  mkdir -p "$AD/usr/bin" "$AD/usr/lib" "$AD/usr/share/applications" "$AD/usr/share/icons/hicolor/256x256/apps"
  cp -a "$TARGET/dist/app/spectracsMain" "$AD/usr/bin/spectracs"
  # only SAFE leaf libraries, and only if PyInstaller did not already bundle them (§18.2b):
  # NEVER libc/libm/libdl/libpthread/ld-linux (the host's loader owns those) and NEVER libGL* (drivers).
  for lib in libxcb-cursor.so.0 libxcb-xinerama.so.0 libusb-1.0.so.0; do
    find "$AD/usr/bin/spectracs" -maxdepth 2 -name "$lib" | grep -q . || \
      cp -aL "/lib/x86_64-linux-gnu/$lib" "$AD/usr/lib/" 2>/dev/null || true
  done
  makeIcon "$AD/spectracs.png"
  cp "$AD/spectracs.png" "$AD/.DirIcon"; cp "$AD/spectracs.png" "$AD/usr/share/icons/hicolor/256x256/apps/"
  cat > "$AD/spectracs.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Spectracs
Comment=Spectroscopy measurement and evaluation
Exec=AppRun
Icon=spectracs
Categories=Science;Education;
Terminal=false
EOF
  cp "$AD/spectracs.desktop" "$AD/usr/share/applications/"
  cp "$HERE/tools/AppRun.app" "$AD/AppRun"; chmod +x "$AD/AppRun"
  { echo "Spectracs — $TAG"
    echo "built $BUILT_AT on $(lsb_release -ds) / glibc $(ldd --version | head -1 | grep -o '[0-9]\+\.[0-9]\+$')"
    echo; echo "contents built from git worktrees of the tagged commits:"; contentShas $REPOS
    echo "build recipe (may be newer than the tag — SPEC §8f.4):"
    echo "  spectracsPy        $RECIPE_SHA"
    echo; echo "toolchain:  Python $("$VENV/python" -V | cut -d' ' -f2) · PyInstaller $("$VENV/pyinstaller" --version) · PySide6 6.5.0"
    echo "server:     NOT bundled. Run Spectracs-Server-$TAG-x86_64.AppImage first (same tag)."
    echo "data:       ~/.spectracsPy   (app DB + prepProtocol.txt)"
    echo "degraded:   SENAITE, PayPal and plugin PUBLISHING are off (no server-config, no signing key)."
    echo "licence:    QtCharts / QtDataVisualization / QtWebEngine excluded; the build asserts their absence."
  } > "$AD/RELEASE_MANIFEST.txt"
  ( cd "$TARGET" && ARCH=x86_64 "$APPIMAGETOOL" Spectracs.AppDir "Spectracs-$TAG-x86_64.AppImage" >/dev/null 2>&1 )
  echo "  -> $(du -h "$TARGET/Spectracs-$TAG-x86_64.AppImage" | cut -f1)"
fi

# ---------------------------------------------------------------- the server image
if [ -n "$DO_SERVER" ]; then
  say "building the SERVER"
  "$VENV/pyinstaller" --noconfirm --clean --log-level ERROR \
    --workpath "$TARGET/work/server" --distpath "$TARGET/dist/server" "$HERE/spectracsServerAppImage.spec"
  AD="$TARGET/SpectracsServer.AppDir"
  mkdir -p "$AD/usr/bin" "$AD/usr/share/applications" "$AD/usr/share/icons/hicolor/256x256/apps"
  cp -a "$TARGET/dist/server/spectracsServer" "$AD/usr/bin/spectracs-server"
  makeIcon "$AD/spectracs-server.png" frame
  cp "$AD/spectracs-server.png" "$AD/.DirIcon"; cp "$AD/spectracs-server.png" "$AD/usr/share/icons/hicolor/256x256/apps/"
  cat > "$AD/spectracs-server.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Spectracs Server
Comment=Spectracs Pyro server (headless)
Exec=AppRun
Icon=spectracs-server
Categories=Science;
Terminal=true
EOF
  cp "$AD/spectracs-server.desktop" "$AD/usr/share/applications/"
  cp "$HERE/tools/AppRun.server" "$AD/AppRun"; chmod +x "$AD/AppRun"
  { echo "Spectracs SERVER — $TAG"
    echo "built $BUILT_AT on $(lsb_release -ds) / glibc $(ldd --version | head -1 | grep -o '[0-9]\+\.[0-9]\+$')"
    echo; echo "contents built from git worktrees of the tagged commits:"
    contentShas spectracsPy-server spectracsPy-model spectracsPy-base
    echo "build recipe (newer than the tag, by design — SPEC §8f.4):"
    echo "  spectracsPy        $RECIPE_SHA  (spectracsServerAppImage.spec + entry)"
    echo; echo "pairs with: Spectracs-$TAG-x86_64.AppImage — SAME TAG, both required."
    echo "usage:      no arguments -> 127.0.0.1:8091, no network needed"
    echo "            any argument -> the stock CLI (--local, --nameserverHost, --daemonPort, ...)"
    echo "data:       ~/.spectracsPy-server/spectracsPyServer.db"
  } > "$AD/RELEASE_MANIFEST.txt"
  ( cd "$TARGET" && ARCH=x86_64 "$APPIMAGETOOL" SpectracsServer.AppDir "Spectracs-Server-$TAG-x86_64.AppImage" >/dev/null 2>&1 )
  echo "  -> $(du -h "$TARGET/Spectracs-Server-$TAG-x86_64.AppImage" | cut -f1)"
fi

# ---------------------------------------------------------------- verify
if [ "$VERIFY" = "1" ]; then
  say "verifying"
  if [ -n "$DO_APP" ]; then
    rm -rf "$HOME/.spectracsPy-demo"
    ( cd /tmp && QT_QPA_PLATFORM=offscreen timeout 40 "$TARGET/Spectracs-$TAG-x86_64.AppImage" --fresh >/dev/null 2>&1 || true )
    HEAD_REV="$("$VENV/python" -c "import sqlite3,os,sys
try:
    c=sqlite3.connect(os.path.expanduser('~/.spectracsPy-demo/spectracsPy.db'))
    print(c.execute('select version_num from alembic_version').fetchone()[0])
except Exception as e: print('FAILED', e)")"
    echo "  app: alembic at $HEAD_REV"
    case "$HEAD_REV" in FAILED*) echo "  APP VERIFY FAILED" >&2; exit 1 ;; esac
  fi
  if [ -n "$DO_SERVER" ]; then
    if (exec 3<>/dev/tcp/127.0.0.1/8091) 2>/dev/null; then
      echo "  server: SKIPPED — 127.0.0.1:8091 already in use; refusing to test someone else's daemon (§8g.3)"
    else
      # setsid: fully detach, so killing it later cannot print "Terminated" into this script's output
      ( cd /tmp && setsid --fork "$TARGET/Spectracs-Server-$TAG-x86_64.AppImage" >/tmp/spectracs_verify_server.log 2>&1 )
      for _ in $(seq 30); do (exec 3<>/dev/tcp/127.0.0.1/8091) 2>/dev/null && break; sleep 1; done
      PYTHONPATH="$SRC/spectracsPy:$SRC/spectracsPy-core:$SRC/spectracsPy-model:$SRC/spectracsPy-base:$SRC/spectracsPy-server" \
      "$VENV/python" -c "
from sciens.spectracs.logic.server.spectracs.SpectracsPyServerClient import SpectracsPyServerClient
r = SpectracsPyServerClient().login('masterUserExakta','masterUserExakta')
assert r['ok'] and 'MASTER_USER' in r['roles'], r
print('  server: login ok — %s / %s / calibration %s' % (r['roles'][0], r.get('registeredSerial'),
      'present' if r.get('calibration') else 'MISSING'))" || { echo "  SERVER VERIFY FAILED" >&2; pkill -f spectracsServer; exit 1; }
      pkill -f "spectracs-server/spectracsServer" 2>/dev/null || true
    fi
  fi
fi

# ---------------------------------------------------------------- prune, then the symlink (8g.4)
say "housekeeping"
mapfile -t RUNS < <(find "$BUILD_ROOT" -maxdepth 1 -type d -regextype posix-extended \
                    -regex '.*/[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}-[0-9]{2}-[0-9]{2}$' | sort -r)
i=0; for d in "${RUNS[@]}"; do i=$((i+1)); [ "$i" -gt "$KEEP" ] && { echo "  pruning $(basename "$d")"; rm -rf "$d"; }; done
ln -sfn "$TARGET" "$BUILD_ROOT/latest"                  # prune FIRST, then repoint — never a dangling latest
say "done"
ls -lh "$TARGET"/*.AppImage 2>/dev/null | sed 's/^/  /'
echo "  latest -> $(readlink -f "$BUILD_ROOT/latest")"
