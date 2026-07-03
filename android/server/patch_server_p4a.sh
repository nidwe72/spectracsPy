#!/usr/bin/env bash
# Re-apply the SERVER-app p4a recipe patches to any fresh python-for-android checkout.
#
# The server uses MAINLINE p4a + the default (Python 3.14) interpreter + sdl2 bootstrap — it does NOT
# use the client/spike patches (python 3.11.9, scipy, numpy cross-file). It needs two different fixes:
#
#   1. bcrypt: its build runs `ffi = FFI()` under the HOST python, so cffi + pycparser must be present
#      in the build venv. p4a recreates that venv each run and does NOT add them itself, so bcrypt's
#      FFI() falls back to a setuptools `.eggs` cffi that can't import pycparser -> ModuleNotFoundError.
#      Fix: declare them as hostpython_prerequisites on the bcrypt recipe.
#
#   2. sqlalchemy: the recipe pins 2.0.30, which crashes on Python 3.14 ("Can't replace canonical
#      symbol for '__firstlineno__'" — 3.13/3.14 auto-inject __firstlineno__ into class dicts and the
#      old `symbol` machinery rejects it). 3.13/3.14 support landed in the 2.0.41+ range. Bump to 2.0.43.
#
# Idempotent: safe to run repeatedly. Point P4A at the server's checkout.
set -euo pipefail

P4A="${1:-$(dirname "$0")/.buildozer/android/platform/python-for-android}"
RECIPES="$P4A/pythonforandroid/recipes"
[ -d "$RECIPES" ] || { echo "ERROR: recipes dir not found at $RECIPES" >&2; exit 1; }

# --- 1. bcrypt host prerequisites -------------------------------------------------------------
BCRYPT="$RECIPES/bcrypt/__init__.py"
if grep -q "hostpython_prerequisites" "$BCRYPT"; then
    echo "[skip] bcrypt hostpython_prerequisites already present"
else
    python3 - "$BCRYPT" <<'PY'
import sys, re
p = sys.argv[1]
s = open(p).read()
needle = "    call_hostpython_via_targetpython = False\n"
add = ("    call_hostpython_via_targetpython = False\n"
       "    # bcrypt's build runs `ffi = FFI()` under the HOST python, so cffi + its parser must be in\n"
       "    # the build venv (else setuptools' .eggs cffi can't import pycparser). p4a doesn't add these.\n"
       "    hostpython_prerequisites = ['cffi', 'pycparser']\n")
assert needle in s, "bcrypt recipe shape changed; patch manually"
open(p, "w").write(s.replace(needle, add, 1))
print("[patched] bcrypt hostpython_prerequisites = ['cffi', 'pycparser']")
PY
fi

# --- 2. sqlalchemy version bump (Python 3.14 compat) ------------------------------------------
SA="$RECIPES/sqlalchemy/__init__.py"
if grep -q "version = '2.0.43'" "$SA"; then
    echo "[skip] sqlalchemy already at 2.0.43"
else
    sed -i "s/version = '2\.0\.30'/version = '2.0.43'  # 2.0.30 crashes on Python 3.14 (__firstlineno__); 3.14 support >= 2.0.41/" "$SA"
    echo "[patched] sqlalchemy version -> 2.0.43"
fi

echo "Server p4a patches applied."
