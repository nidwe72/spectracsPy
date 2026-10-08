"""W0.3 (SPEC_windows_build.md D4, D5, U7, U14–U18): the Windows runtime hooks, tested on Linux.

A runtime hook acts the moment it is loaded, but only in a frozen build — so loading the file here is inert, and
the tests drive its pure _plan and its _apply against tmp_path and a stand-in `sys`.
"""
import importlib.util
import os
import socket
from types import SimpleNamespace

import pytest

TOOLS = os.path.join(os.path.dirname(__file__), "..", "tools")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(TOOLS, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


appHook = _load("rthook_win_app")
serverHook = _load("rthook_win_server")


@pytest.fixture
def keepCwd():
    cwd = os.getcwd()
    yield
    os.chdir(cwd)


# ---------------------------------------------------------------------------------------------- the app hook

def test_app_plan_default_root_and_argv_untouched():
    cwd, argv, log = appHook._plan(["Spectracs.exe", "--phone"], {}, "/home/u")
    assert cwd == os.path.join("/home/u", "Spectracs", "spectracsPy")
    assert argv == ["Spectracs.exe", "--phone"]
    assert log == os.path.join(cwd, "spectracs.log")


def test_app_plan_fresh_anywhere_selects_demo_and_is_stripped():
    cwd, argv, _ = appHook._plan(["Spectracs.exe", "--check-db", "--fresh"], {}, "/home/u")
    assert cwd == os.path.join("/home/u", "Spectracs", "spectracsPy-demo")
    assert argv == ["Spectracs.exe", "--check-db"]


def test_app_plan_cwd_root_from_environment():
    cwd, _, _ = appHook._plan(["Spectracs.exe"], {"SPECTRACS_CWD_ROOT": "/elsewhere"}, "/home/u")
    assert cwd == os.path.join("/elsewhere", "spectracsPy")


def test_app_apply_moves_in_and_logs_utf8_without_a_manifest(tmp_path, keepCwd):
    plan = appHook._plan(["Spectracs.exe", "--fresh"], {}, str(tmp_path))
    fakeSys = SimpleNamespace(argv=["Spectracs.exe", "--fresh"], stdout=None, stderr=None,
                              executable=str(tmp_path / "zip" / "Spectracs.exe"))
    log = appHook._apply(plan, fakeSys, os)
    try:
        assert os.getcwd() == str(tmp_path / "Spectracs" / "spectracsPy-demo")
        assert fakeSys.argv == ["Spectracs.exe"]
        assert fakeSys.stdout is log and fakeSys.stderr is log
        print("capture → reference ●", file=fakeSys.stdout)  # cp1252 could not encode this (U7)
    finally:
        log.close()
    text = (tmp_path / "Spectracs" / "spectracsPy-demo" / "spectracs.log").read_text(encoding="utf-8")
    assert "==== Spectracs start" in text
    assert "executable: " in text  # no RELEASE_MANIFEST.txt next to the exe (U18)
    assert "capture → reference ●" in text


def test_app_apply_banner_carries_the_manifest(tmp_path, keepCwd):
    (tmp_path / "zip").mkdir()
    (tmp_path / "zip" / "RELEASE_MANIFEST.txt").write_text("Spectracs — W0-test\n", encoding="utf-8")
    plan = appHook._plan(["Spectracs.exe"], {}, str(tmp_path))
    fakeSys = SimpleNamespace(argv=["Spectracs.exe"], stdout=None, stderr=None,
                              executable=str(tmp_path / "zip" / "Spectracs.exe"))
    appHook._apply(plan, fakeSys, os).close()
    assert "Spectracs — W0-test" in (tmp_path / "Spectracs" / "spectracsPy" / "spectracs.log").read_text(encoding="utf-8")


def test_hooks_are_inert_when_not_frozen():
    # loading did not chdir or redirect anything, and kept the helpers for the tests
    assert hasattr(appHook, "_plan") and hasattr(serverHook, "_apply")


# ------------------------------------------------------------------------------------------- the server hook

def test_server_plan():
    assert serverHook._plan({}, "/home/u") == os.path.join("/home/u", "Spectracs", "spectracsPy-server")
    assert serverHook._plan({"SPECTRACS_CWD_ROOT": "/x"}, "/home/u") == os.path.join("/x", "spectracsPy-server")


def _freePort():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def test_server_apply_moves_in_disables_sock_reuse_and_never_touches_argv(tmp_path, keepCwd):
    argv = ["SpectracsServer.exe", "--local"]
    environ = {}
    fakeSys = SimpleNamespace(stdout=None)
    cwd = str(tmp_path / "spectracsPy-server")
    assert serverHook._apply(cwd, argv, environ, fakeSys, os, port=_freePort()) is True
    assert os.getcwd() == cwd
    assert environ["PYRO_SOCK_REUSE"] == "false"
    assert argv == ["SpectracsServer.exe", "--local"]


def test_server_refuses_a_taken_loopback_port(tmp_path, keepCwd, capsys):
    import sys
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        fakeSys = SimpleNamespace(stdout=sys.stdout)
        assert serverHook._apply(str(tmp_path / "s"), ["SpectracsServer.exe"], {}, fakeSys, os, port=port) is False
        # with arguments (the stock CLI) the check is not this hook's business
        assert serverHook._apply(str(tmp_path / "s"), ["SpectracsServer.exe", "--local"], {}, fakeSys, os,
                                 port=port) is True
    assert "already in use" in capsys.readouterr().out
