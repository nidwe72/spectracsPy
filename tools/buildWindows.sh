#!/usr/bin/env bash
# Build the Spectracs Windows zips in the build VM, driven from Linux — docs/SPEC_windows_build.md §5.
#
#   tools/buildWindows.sh [--app] [--server] [--tag <git ref>] [--out <name|path>] [--keep N] [--no-verify]
#                         [--no-installer]
#
# Defaults: both programs, each as a zip AND a per-user Setup.exe (§5b) · --tag main · --out <ISO timestamp> under
# ~/spectracs-build/windows · --keep 3
#
# Same contract as buildAppImages.sh: the contents come from the committed <ref> of each repo (never the live
# tree), the recipe (specs, server entry, runtime hooks) from this checkout, and nothing is written into a repo.
# The sources travel as `git archive` of the ref — no worktrees, no .git, nothing to reuse stale (S2) — in one tar
# with a sha256 on both ends (S8). PyInstaller runs IN the VM (D1, tools/windows/buildInVm.ps1); the manifest,
# START_HERE.txt and the zips are made here (R10). The VM is `ssh spectracs-win` (~/.ssh/config, key login).
set -euo pipefail

TAG="main"
OUT=""
KEEP=3
DO_APP=""; DO_SERVER=""; VERIFY=1; INSTALLER=1
BUILD_ROOT="${SPECTRACS_BUILD_ROOT:-$HOME/spectracs-build}/windows"
VM="${SPECTRACS_WIN_HOST:-spectracs-win}"
VM_ROOT='C:\spectracs-build'
VM_VENV='C:\spectracs-build\venv'
VM_ISCC="${SPECTRACS_WIN_ISCC:-C:\spectracs-build\InnoSetup6\ISCC.exe}"   # Inno Setup 6.7.3, W2.1a

while [ $# -gt 0 ]; do
  case "$1" in
    --app)        DO_APP=1 ;;
    --server)     DO_SERVER=1 ;;
    --tag)        TAG="$2"; shift ;;
    --out)        OUT="$2"; shift ;;
    --keep)       KEEP="$2"; shift ;;
    --no-verify)  VERIFY=0 ;;
    --no-installer) INSTALLER=0 ;;
    -h|--help)    sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done
[ -z "$DO_APP$DO_SERVER" ] && { DO_APP=1; DO_SERVER=1; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"      # …/spectracsPy (the recipe)
REPOS_DIR="$(dirname "$HERE")"
VENV="$HERE/venv/bin"
REPOS="spectracsPy spectracsPy-core spectracsPy-model spectracsPy-base spectracsPy-server spectracs-plugins"
say() { printf "\n\033[1m== %s\033[0m\n" "$*"; }
crlf() { sed 's/$/\r/'; }                                    # the txt files are read in Notepad

# ---------------------------------------------------------------- the ref, per repo
say "ref '$TAG'"
declare -A SHA
for repo in $REPOS; do
  SHA[$repo]="$(git -C "$REPOS_DIR/$repo" rev-parse --verify --quiet "$TAG^{commit}")" \
    || { echo "REFUSING: '$TAG' does not exist in $repo" >&2; exit 1; }
  printf "  %-20s %s\n" "$repo" "${SHA[$repo]:0:7}"
done
# a release tag names itself; any other ref gets the commit, so two builds of a moving `main` never share a name
if git -C "$HERE" show-ref --verify --quiet "refs/tags/$TAG"; then LABEL="$TAG"; else LABEL="${TAG//\//-}-${SHA[spectracsPy]:0:7}"; fi
RECIPE_SHA="$(git -C "$HERE" rev-parse --short HEAD)"
[ -n "$(git -C "$HERE" status --porcelain -- spectracsAppImage.spec spectracsServerAppImage.spec \
        spectracsServerAppImageEntry.py tools/)" ] && RECIPE_SHA="$RECIPE_SHA+dirty"

# ---------------------------------------------------------------- target folder
if [ -n "$OUT" ]; then
  case "$OUT" in */*) TARGET="$(readlink -f "$OUT")" ;; *) TARGET="$BUILD_ROOT/$OUT" ;; esac
else
  TARGET="$BUILD_ROOT/$(date +%Y-%m-%dT%H-%M-%S)"
fi
mkdir -p "$(dirname "$TARGET")"
if git -C "$(dirname "$TARGET")" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "REFUSING: $TARGET is inside a git work tree (see SPEC_linux_appimage.md §8b.2)." >&2; exit 1
fi
mkdir -p "$TARGET"
rm -rf "$TARGET/stage" "$TARGET/dist" "$TARGET"/Spectracs-*-win64 "$TARGET"/Spectracs-*-win64.zip \
       "$TARGET"/Spectracs-*Setup-*.exe \
       "$TARGET/upload.tar" "$TARGET/dist.tar" "$TARGET/vm-build.log" "$TARGET/vm-verify.log"
say "target: $TARGET  (label $LABEL)"

# ---------------------------------------------------------------- stage: sources + recipe + icons
STAGE="$TARGET/stage"
mkdir -p "$STAGE/src" "$STAGE/recipe/tools" "$STAGE/icons"
for repo in $REPOS; do
  git -C "$REPOS_DIR/$repo" archive --prefix="$repo/" "${SHA[$repo]}" | tar -x -C "$STAGE/src"
done
cp "$HERE/spectracsAppImage.spec" "$HERE/spectracsServerAppImage.spec" "$HERE/spectracsServerAppImageEntry.py" \
   "$STAGE/recipe/"
cp "$HERE/tools/rthook_win_app.py" "$HERE/tools/rthook_win_server.py" "$HERE/tools/windows/buildInVm.ps1" \
   "$STAGE/recipe/tools/"
LOGO="$STAGE/src/spectracsPy/resource/logo.png"
"$VENV/python" "$HERE/tools/makeIcon.py" --logo "$LOGO" --out "$STAGE/icons/spectracs.png" \
  --ico "$STAGE/icons/spectracs.ico"
"$VENV/python" "$HERE/tools/makeIcon.py" --logo "$LOGO" --out "$STAGE/icons/spectracs-server.png" --frame \
  --ico "$STAGE/icons/spectracs-server.ico"
# the head the bundled Alembic tree must report (§5.1.1), read from the archived -model here on Linux
EXPECTED_HEAD="$("$VENV/python" -c "import sys
from alembic.config import Config; from alembic.script import ScriptDirectory
print(ScriptDirectory.from_config(Config(sys.argv[1])).get_current_head())" \
  "$STAGE/src/spectracsPy-model/alembic/app/alembic.ini")"
cp "$HERE/tools/windows/verifyInVm.ps1" "$HERE/tools/windows/setupInVm.ps1" "$HERE/tools/windows/verifySetupInVm.ps1" \
   "$HERE/tools/windows/spectracs.iss" "$HERE/tools/windows/spectracs-server.iss" "$STAGE/recipe/tools/"
tar -cf "$TARGET/upload.tar" -C "$STAGE" .
UP_SHA="$(sha256sum "$TARGET/upload.tar" | cut -d' ' -f1)"
echo "  upload.tar $(du -h "$TARGET/upload.tar" | cut -f1)  sha256 ${UP_SHA:0:16}…"

# ---------------------------------------------------------------- to the VM, build there
RUN="b-$(basename "$TARGET")"                   # one fresh folder per build in the VM
VM_DIR="$VM_ROOT\\$RUN"
VM_DIR_SCP="${VM_ROOT//\\//}/$RUN"              # scp wants C:/…
say "VM $VM: $VM_DIR"
ssh "$VM" "if (Test-Path '$VM_DIR') { Remove-Item -Recurse -Force '$VM_DIR' }; New-Item -ItemType Directory '$VM_DIR' | Out-Null"
scp -q "$TARGET/upload.tar" "$VM:$VM_DIR_SCP/upload.tar"
ssh "$VM" "\$h = (Get-FileHash '$VM_DIR\\upload.tar' -Algorithm SHA256).Hash.ToLower(); if (\$h -ne '$UP_SHA') { Write-Output \"checksum mismatch: \$h\"; exit 1 }; tar -xf '$VM_DIR\\upload.tar' -C '$VM_DIR'; if (\$LASTEXITCODE -ne 0) { exit 1 }" \
  || { echo "UPLOAD FAILED (checksum or unpack) — VM folder kept: $VM_DIR" >&2; exit 1; }
FLAGS="${DO_APP:+-App} ${DO_SERVER:+-Server}"
say "building in the VM ($FLAGS)"
if ! ssh "$VM" "powershell -NoProfile -ExecutionPolicy Bypass -File '$VM_DIR\\recipe\\tools\\buildInVm.ps1' -BuildDir '$VM_DIR' -Venv '$VM_VENV' -Iscc '$VM_ISCC' $FLAGS" \
     | tee "$TARGET/vm-build.log"; then
  echo "VM BUILD FAILED — logs stay in $VM_DIR (build-app.log / build-server.log)" >&2; exit 1
fi
DIST_SHA="$(grep -o 'RESULT ok [0-9a-f]\{64\}' "$TARGET/vm-build.log" | cut -d' ' -f3 || true)"
[ -n "$DIST_SHA" ] || { echo "VM BUILD FAILED (no RESULT line) — logs stay in $VM_DIR" >&2; exit 1; }

# ---------------------------------------------------------------- verify in the VM (§5.1, W0.7)
if [ "$VERIFY" = "1" ]; then
  say "verifying in the VM (alembic head $EXPECTED_HEAD)"
  if ! ssh "$VM" "powershell -NoProfile -ExecutionPolicy Bypass -File '$VM_DIR\\recipe\\tools\\verifyInVm.ps1' -BuildDir '$VM_DIR' -Venv '$VM_VENV' -ExpectedHead '$EXPECTED_HEAD' $FLAGS" \
       | tee "$TARGET/vm-verify.log"; then
    echo "VERIFY FAILED — nothing zipped; the VM folder stays for a look: $VM_DIR" >&2; exit 1
  fi
  grep -q '^VERIFY ok' "$TARGET/vm-verify.log" || { echo "VERIFY FAILED (no 'VERIFY ok') — VM folder kept: $VM_DIR" >&2; exit 1; }
else
  echo "  (--no-verify: the §5.1 self-verify was skipped)"
fi

# ---------------------------------------------------------------- back to Linux
say "fetching dist"
scp -q "$VM:$VM_DIR_SCP/dist.tar" "$TARGET/dist.tar"
[ "$(sha256sum "$TARGET/dist.tar" | cut -d' ' -f1)" = "$DIST_SHA" ] \
  || { echo "checksum mismatch on dist.tar — VM folder kept: $VM_DIR" >&2; exit 1; }
mkdir -p "$TARGET/dist"; tar -xf "$TARGET/dist.tar" -C "$TARGET/dist"
TOOLCHAIN="$(tr -d '\r' < "$TARGET/dist/toolchain.txt")"
BUILT_AT="$(date -Iseconds)"
contentShas() { for r in "$@"; do printf "  %-20s %s\n" "$r" "${SHA[$r]}"; done; }

# ---------------------------------------------------------------- the app zip
if [ -n "$DO_APP" ]; then
  NAME="Spectracs-$LABEL-win64"
  mv "$TARGET/dist/app/Spectracs" "$TARGET/$NAME"
  { echo "Spectracs - $LABEL (Windows 10/11, 64-bit)"
    echo "built $BUILT_AT in the build VM"
    echo; echo "contents built from the committed '$TAG' of each repository:"; contentShas $REPOS
    echo "build recipe (may be newer than the contents - SPEC_linux_appimage.md §8f.4):"
    echo "  spectracsPy          $RECIPE_SHA"
    echo; echo "toolchain:"; echo "$TOOLCHAIN" | sed 's/^/  /'
    echo; echo "server:     NOT bundled. The app uses the internet server; Spectracs-Server-$LABEL-win64.zip is the"
    echo "            local server for development and demos (same label)."
    echo "data:       %USERPROFILE%\\spectracsPy\\  (app DB)"
    echo "log:        %USERPROFILE%\\Spectracs\\spectracsPy\\spectracs.log"
    echo "camera:     real camera via MSMF (raw YUY2, own conversion) + its DirectShow controls (W1, SPEC_camera_settings CS3)."
    echo "degraded:   SENAITE, PayPal and plugin PUBLISHING are off (no server-config, no signing key)."
    echo "licence:    QtCharts / QtDataVisualization / QtWebEngine excluded; the build asserts their absence."
    if [ "$INSTALLER" = "1" ]; then
      echo "installer:  Spectracs-Setup-$LABEL.exe installs this same folder per user (no admin) - SPEC §5b."
    fi
  } | crlf > "$TARGET/$NAME/RELEASE_MANIFEST.txt"
  crlf > "$TARGET/$NAME/START_HERE.txt" <<EOF
Spectracs $LABEL for Windows 10/11 (64-bit)
===========================================

1. BEFORE extracting the zip: right-click it -> Properties -> tick "Unblock" -> OK
   (PowerShell: Unblock-File .\\$NAME.zip). The program is not signed yet; without Unblock
   Windows shows "Windows protected your PC" -> "More info" -> "Run anyway".
2. Extract it to a LOCAL folder (not a network share) - where does not matter.
   Start Spectracs.exe.
3. Your data:  %USERPROFILE%\\spectracsPy\\                  (the database)
   The log:    %USERPROFILE%\\Spectracs\\spectracsPy\\spectracs.log
   Both stay where they are when you extract a newer version somewhere else.
4. Demo start with an EMPTY database (never for real measurements): make a shortcut to
   Spectracs.exe and add  --fresh  to its target. Its data: %USERPROFILE%\\spectracsPy-demo\\
5. Lamp plug: the first time the lamp is searched, the Windows Firewall may ask to allow
   Spectracs on private networks - allow it (the plug is found over the local network).
6. The app talks to the internet server. A local server (Spectracs-Server-$LABEL-win64.zip)
   is only for development and demos: start it before the app.

See RELEASE_MANIFEST.txt for exactly what this build contains.
EOF
  ( cd "$TARGET" && zip -q -r -X "$NAME.zip" "$NAME" )
  echo "  -> $NAME.zip $(du -h "$TARGET/$NAME.zip" | cut -f1)"
fi

# ---------------------------------------------------------------- the server zip
if [ -n "$DO_SERVER" ]; then
  NAME="Spectracs-Server-$LABEL-win64"
  mv "$TARGET/dist/server/SpectracsServer" "$TARGET/$NAME"
  { echo "Spectracs SERVER - $LABEL (Windows 10/11, 64-bit)"
    echo "built $BUILT_AT in the build VM"
    echo; echo "contents built from the committed '$TAG' of each repository:"
    contentShas spectracsPy-server spectracsPy-model spectracsPy-base
    echo "build recipe (newer than the contents, by design - SPEC_linux_appimage.md §8f.4):"
    echo "  spectracsPy          $RECIPE_SHA  (spectracsServerAppImage.spec + entry + runtime hook)"
    echo; echo "toolchain:"; echo "$TOOLCHAIN" | sed 's/^/  /'
    echo; echo "pairs with: Spectracs-$LABEL-win64.zip - same label."
    echo "usage:      no arguments -> 127.0.0.1:8091 only, no network needed; refuses if 8091 is taken"
    echo "            any argument -> the stock CLI (--local, --nameserverHost, --daemonPort, ...)"
    echo "data:       %USERPROFILE%\\spectracsPy-server\\spectracsPyServer.db"
    if [ "$INSTALLER" = "1" ]; then
      echo "installer:  Spectracs-Server-Setup-$LABEL.exe installs this same folder per user (no admin) - SPEC §5b."
    fi
  } | crlf > "$TARGET/$NAME/RELEASE_MANIFEST.txt"
  crlf > "$TARGET/$NAME/START_HERE.txt" <<EOF
Spectracs SERVER $LABEL for Windows 10/11 (64-bit)
==================================================

Only for local development and demos - the Spectracs app normally uses the internet server.

1. BEFORE extracting the zip: right-click it -> Properties -> tick "Unblock" -> OK
   (PowerShell: Unblock-File .\\$NAME.zip).
2. Extract it to a local folder and start SpectracsServer.exe. Its console window is the
   sign that it runs; closing the window stops the server.
3. It listens on 127.0.0.1:8091 only (this PC). A second copy refuses to start.
4. Its data: %USERPROFILE%\\spectracsPy-server\\
5. Then start Spectracs.exe: it finds the local server first.

See RELEASE_MANIFEST.txt for exactly what this build contains.
EOF
  ( cd "$TARGET" && zip -q -r -X "$NAME.zip" "$NAME" )
  echo "  -> $NAME.zip $(du -h "$TARGET/$NAME.zip" | cut -f1)"
fi

# ---------------------------------------------------------------- the installers (W2.1, §5b)
if [ "$INSTALLER" = "1" ]; then
  say "installers"
  TEXTS="$TARGET/texts"; rm -rf "$TEXTS"
  # the INSTALLED copy's read-me: nothing to unblock or extract (§5b.4)
  if [ -n "$DO_APP" ]; then
    mkdir -p "$TEXTS/app"; cp "$TARGET/Spectracs-$LABEL-win64/RELEASE_MANIFEST.txt" "$TEXTS/app/"
    crlf > "$TEXTS/app/START_HERE.txt" <<EOF
Spectracs $LABEL for Windows 10/11 (64-bit) - installed
=======================================================

1. Start Spectracs from the Start menu.
2. Your data:  %USERPROFILE%\\spectracsPy\\                  (the database)
   The log:    %USERPROFILE%\\Spectracs\\spectracsPy\\spectracs.log
   Installing a newer version over this one, or uninstalling it, never touches them.
3. Demo with an EMPTY database (never for real measurements): Start menu ->
   "Spectracs (demo, empty database)". Its data: %USERPROFILE%\\spectracsPy-demo\\
4. Lamp plug: the first time the lamp is searched, the Windows Firewall may ask to allow
   Spectracs on private networks - allow it (the plug is found over the local network).
5. The app talks to the internet server. A local server (Spectracs-Server-Setup-$LABEL.exe)
   is only for development and demos: start it before the app.
6. Uninstall: Windows Settings -> Apps -> Spectracs.

See RELEASE_MANIFEST.txt for exactly what this build contains.
EOF
  fi
  if [ -n "$DO_SERVER" ]; then
    mkdir -p "$TEXTS/server"; cp "$TARGET/Spectracs-Server-$LABEL-win64/RELEASE_MANIFEST.txt" "$TEXTS/server/"
    crlf > "$TEXTS/server/START_HERE.txt" <<EOF
Spectracs SERVER $LABEL for Windows 10/11 (64-bit) - installed
==============================================================

Only for local development and demos - the Spectracs app normally uses the internet server.

1. Start it from the Start menu: "Spectracs Server (local)". Its console window is the sign
   that it runs; closing the window stops the server.
2. It listens on 127.0.0.1:8091 only (this PC). A second copy refuses to start.
3. Its data: %USERPROFILE%\\spectracsPy-server\\ - updates and uninstalling never touch it.
4. Then start Spectracs: it finds the local server first.
5. Uninstall: Windows Settings -> Apps -> Spectracs Server.

See RELEASE_MANIFEST.txt for exactly what this build contains.
EOF
  fi
  tar -cf "$TARGET/texts.tar" -C "$TARGET" texts
  scp -q "$TARGET/texts.tar" "$VM:$VM_DIR_SCP/texts.tar"
  ssh "$VM" "tar -xf '$VM_DIR\\texts.tar' -C '$VM_DIR'"
  if ! ssh "$VM" "powershell -NoProfile -ExecutionPolicy Bypass -File '$VM_DIR\\recipe\\tools\\setupInVm.ps1' -BuildDir '$VM_DIR' -Label '$LABEL' -Iscc '$VM_ISCC' $FLAGS" \
       | tee "$TARGET/vm-setup.log"; then
    echo "SETUP BUILD FAILED — logs stay in $VM_DIR (setup-app.log / setup-server.log)" >&2; exit 1
  fi
  if [ "$VERIFY" = "1" ]; then
    if ! ssh "$VM" "powershell -NoProfile -ExecutionPolicy Bypass -File '$VM_DIR\\recipe\\tools\\verifySetupInVm.ps1' -SetupDir '$VM_DIR\\setup' $FLAGS" \
         | tee "$TARGET/vm-setup-verify.log"; then
      echo "SETUP-VERIFY FAILED — the VM folder stays for a look: $VM_DIR" >&2; exit 1
    fi
    grep -q '^SETUP-VERIFY ok' "$TARGET/vm-setup-verify.log" \
      || { echo "SETUP-VERIFY FAILED (no 'SETUP-VERIFY ok') — VM folder kept: $VM_DIR" >&2; exit 1; }
  fi
  while read -r _ _ file sha; do
    scp -q "$VM:$VM_DIR_SCP/setup/$file" "$TARGET/$file"
    [ "$(sha256sum "$TARGET/$file" | cut -d' ' -f1)" = "$sha" ] \
      || { echo "checksum mismatch on $file — VM folder kept: $VM_DIR" >&2; exit 1; }
    echo "  -> $file $(du -h "$TARGET/$file" | cut -f1)"
  done < <(grep '^SETUP ok ' "$TARGET/vm-setup.log" | tr -d '\r')
  rm -rf "$TEXTS" "$TARGET/texts.tar"
fi

# ---------------------------------------------------------------- VM cleanup, prune
ssh "$VM" "Remove-Item -Recurse -Force '$VM_DIR'"
rm -rf "$STAGE" "$TARGET/dist" "$TARGET/upload.tar" "$TARGET/dist.tar"

say "housekeeping"
mapfile -t RUNS < <(find "$BUILD_ROOT" -maxdepth 1 -type d -regextype posix-extended \
                    -regex '.*/[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}-[0-9]{2}-[0-9]{2}$' | sort -r)
i=0; for d in "${RUNS[@]}"; do i=$((i+1)); [ "$i" -gt "$KEEP" ] && { echo "  pruning $(basename "$d")"; rm -rf "$d"; }; done
ln -sfn "$TARGET" "$BUILD_ROOT/latest"
say "done"
ls -lh "$TARGET"/*.zip "$TARGET"/*Setup*.exe 2>/dev/null | sed 's/^/  /'
echo "  latest -> $(readlink -f "$BUILD_ROOT/latest")"
