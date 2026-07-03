#!/usr/bin/env bash
# P4a — re-apply the four python-for-android fixes that make the Spectracs stack cross-compile.
# Idempotent. Run against a p4a checkout after `buildozer` clones it (or a clean clone).
#
#   ./patch_p4a.sh [<path-to-python-for-android checkout>]
#
# Default path = the buildozer-managed checkout under android/spike/.buildozer.
# These are documented in docs/SPEC_android_port.md §7. Upstream-reportable (kivy/python-for-android).
set -euo pipefail

P4A="${1:-$(dirname "$0")/spike/.buildozer/android/platform/python-for-android}"
REC="$P4A/pythonforandroid/recipes"
[ -d "$REC" ] || { echo "recipes dir not found: $REC"; exit 1; }

python3 - "$REC" <<'PY'
import sys, re, pathlib
rec = pathlib.Path(sys.argv[1])

def sub(path, pattern, repl, why):
    p = rec / path
    s = p.read_text()
    new = re.sub(pattern, repl, s, count=1)
    if new == s:
        print(f"  = {path}: already patched / no change ({why})")
    else:
        p.write_text(new); print(f"  ✓ {path}: {why}")

# 1 & 2: Python 3.11.9 to match the PySide6 cp311 abi3 wheels (host + target must match).
sub("python3/__init__.py",     r"version = '3\.14\.\d+'", "version = '3.11.9'", "python3 -> 3.11.9")
sub("hostpython3/__init__.py", r'version = "3\.14\.\d+"', 'version = "3.11.9"', "hostpython3 -> 3.11.9")

# 3: scipy needs a Cython new enough for numpy 2.3's trimmed C-API.
sub("scipy/__init__.py", r'"Cython>=3\.0\.\d+"', '"Cython>=3.1.2"', "scipy Cython>=3.1.2")

# 4: numpy get_recipe_env must PRESERVE --cross-file (not clobber it with '=') for the
#    OpenBLAS-linked variant, or meson does a native build -> Exec format error.
np = rec / "numpy/__init__.py"
s = np.read_text()
if '"-Dblas=" not in a' in s:   # the filter-comprehension signature = already preserving the cross-file
    print("  = numpy/__init__.py: already patched (cross-file preserve)")
else:
    old = (
        "        if 'libopenblas' in self.ctx.recipe_build_order:\n"
        "            self.extra_build_args = [\n"
        '                "-Csetup-args=-Dblas=auto",\n'
        '                "-Csetup-args=-Dlapack=auto",\n'
        '                "-Csetup-args=-Dallow-noblas=False",\n'
        "            ]\n"
    )
    new = (
        "        if 'libopenblas' in self.ctx.recipe_build_order:\n"
        "            # PRESERVE the cross-file added by MesonRecipe.build_arch (don't clobber with '=').\n"
        "            self.extra_build_args = [\n"
        "                a for a in self.extra_build_args\n"
        '                if "-Dblas=" not in a and "-Dlapack=" not in a and "-Dallow-noblas=" not in a\n'
        "            ] + [\n"
        '                "-Csetup-args=-Dblas=auto",\n'
        '                "-Csetup-args=-Dlapack=auto",\n'
        '                "-Csetup-args=-Dallow-noblas=False",\n'
        "            ]\n"
    )
    if old not in s:
        print("  ! numpy/__init__.py: expected block not found — patch manually (see spec §7)")
    else:
        np.write_text(s.replace(old, new)); print("  ✓ numpy/__init__.py: cross-file preserve")
PY

# --- P4e: build-venv pip guard --------------------------------------------------
# p4a builds a host "build venv" and pip-installs the pure-python requirements into
# it. A half-completed `pip install -U pip` there leaves a MISMATCHED vendored
# resolvelib (newer resolver code, older structs), which breaks ALL dependency
# resolution mid-build:
#     ImportError: cannot import name 'RequirementInformation'
#                  from 'pip._vendor.resolvelib.structs'
# (Hit on 2026-07-04.) Re-extract a clean, consistent pip via ensurepip. Idempotent;
# only touches build-venvs that already exist (a fresh clean build makes its own).
# NOTE: derived from the default spike storage dir; if you pass a custom p4a path as
# $1, the build-venv still lives under spike/.buildozer — adjust if you relocate it.
STORAGE="$(cd "$(dirname "$0")" && pwd)/spike/.buildozer/android/platform"
shopt -s nullglob
for VENV in "$STORAGE"/build-*/build/venv; do
    [ -x "$VENV/bin/python" ] || continue
    for SP in "$VENV"/lib/python3.*/site-packages; do
        rm -rf "$SP"/pip "$SP"/pip-*.dist-info
    done
    if "$VENV/bin/python" -m ensurepip --upgrade >/dev/null 2>&1; then
        echo "  ✓ build-venv pip re-extracted clean: ${VENV#"$STORAGE"/}"
    else
        echo "  ! build-venv pip repair FAILED (re-extract manually): $VENV"
    fi
done
shopt -u nullglob

echo "done. (also ensure buildozer.spec: p4a.bootstrap=qt, android.ndk=28c, android.minapi=26, JDK 17)"
echo "note: rgbxy is NOT a requirement — it is vendored as app_src/rgbxy (pure-python; no py3.11 wheel on PyPI)."
