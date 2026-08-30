import os

import pytest

from sciens.spectracs.logic.spectral.workflow.PrepProtocolResolver import PrepProtocolResolver, ENV_NAME


@pytest.fixture(autouse=True)
def _noEnvironment(monkeypatch):
    monkeypatch.delenv(ENV_NAME, raising=False)


def test_falls_back_to_the_plugin_declaration(monkeypatch, tmp_path):
    monkeypatch.setattr(PrepProtocolResolver, "overridePath", staticmethod(lambda: str(tmp_path / "none.txt")))
    assert PrepProtocolResolver.resolve("declared-by-plugin") == "declared-by-plugin"


def test_environment_wins(monkeypatch, tmp_path):
    monkeypatch.setattr(PrepProtocolResolver, "overridePath", staticmethod(lambda: str(tmp_path / "none.txt")))
    monkeypatch.setenv(ENV_NAME, "  from-the-environment  ")
    assert PrepProtocolResolver.resolve("declared") == "from-the-environment"


def test_file_overrides_the_declaration_and_skips_comments(monkeypatch, tmp_path):
    target = tmp_path / "prepProtocol.txt"
    target.write_text("# the recipe of the evening\n\n  vortex30-sonic60-box6  \nignored second line\n",
                      encoding="utf-8")
    monkeypatch.setattr(PrepProtocolResolver, "overridePath", staticmethod(lambda: str(target)))
    assert PrepProtocolResolver.resolve("declared") == "vortex30-sonic60-box6"


def test_a_comments_only_file_is_not_an_override(monkeypatch, tmp_path):
    target = tmp_path / "prepProtocol.txt"
    target.write_text("# nothing but comments\n\n", encoding="utf-8")
    monkeypatch.setattr(PrepProtocolResolver, "overridePath", staticmethod(lambda: str(target)))
    assert PrepProtocolResolver.resolve("declared") == "declared"


def test_provenance_never_breaks_a_capture(monkeypatch):
    # ⛔ An unreadable data directory must NOT raise out of a run that is about to capture.
    def boom():
        raise OSError("no data directory")
    monkeypatch.setattr(PrepProtocolResolver, "overridePath", staticmethod(boom))
    with pytest.raises(OSError):
        PrepProtocolResolver.overridePath()
    assert PrepProtocolResolver.resolve("declared") == "declared"
