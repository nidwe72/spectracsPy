"""W0.2 (SPEC_windows_build.md D9, U1–U3, U21): `spectracsMain.py --check-db` is a headless build check.

It migrates the app DB to head, prints `check-db ok: app db <rev> head <rev> at <path>` and leaves through
os._exit — no QApplication, no window. Run in a subprocess with HOME and cwd in tmp_path: from the repo's cwd it
would resolve to the real ~/.spectracsPy archive and migrate it (U21).
"""
import os
import subprocess
import sys

from alembic.config import Config
from alembic.script import ScriptDirectory

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SIBLINGS = ["spectracsPy-core", "spectracsPy-model", "spectracsPy-base", "spectracsPy-server", "spectracs-plugins"]


def _run(tmp_path, pythonPath):
    cwd = tmp_path / "spectracsPy-demo"
    cwd.mkdir()
    env = dict(os.environ, HOME=str(tmp_path), QT_QPA_PLATFORM="offscreen", PYTHONPATH=os.pathsep.join(pythonPath))
    return subprocess.run([sys.executable, os.path.join(REPO, "spectracsMain.py"), "--check-db"],
                          cwd=str(cwd), env=env, capture_output=True, text=True, timeout=90)


def test_check_db_migrates_a_fresh_db_and_reports_the_head(tmp_path):
    pythonPath = [REPO] + [os.path.join(os.path.dirname(REPO), sibling) for sibling in SIBLINGS]
    result = _run(tmp_path, pythonPath)
    assert result.returncode == 0, result.stdout + result.stderr

    modelHead = ScriptDirectory.from_config(Config(os.path.join(
        os.path.dirname(REPO), "spectracsPy-model", "alembic", "app", "alembic.ini"))).get_current_head()
    databasePath = tmp_path / ".spectracsPy-demo" / "spectracsPy.db"
    assert "check-db ok: app db %s head %s at %s" % (modelHead, modelHead, databasePath) in result.stdout
    assert databasePath.is_file()


def test_check_db_fails_with_a_traceback_not_a_hang(tmp_path):
    # Without -model on the path the import inside the check fails: exit 1 and the traceback on stderr.
    result = _run(tmp_path, [REPO])
    assert result.returncode == 1
    assert "Traceback" in result.stderr
