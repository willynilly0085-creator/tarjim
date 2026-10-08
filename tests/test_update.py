"""Updates: knowing a newer release is out, asking at most once a day, and handing over safely."""
from pathlib import Path

import pytest

from tarjim import config, installer, update


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(config, "HOME", tmp_path)
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(update, "__version__", "1.2.3")
    return tmp_path


@pytest.mark.parametrize(("tag", "is_newer"), [
    ("v1.2.4", True), ("1.3.0", True), ("v2.0.0", True), ("v1.10.0", True), ("v1.2.3", False),
    ("v1.2.2", False), ("v0.9.9", False), ("nightly", False), ("", False), ("v1.2", False),
])
def test_only_a_higher_release_number_counts_as_an_update(home: Path, tag: str,
                                                          is_newer: bool) -> None:
    assert update.newer(tag) is is_newer


def test_github_is_asked_at_most_once_a_day_and_an_outage_keeps_the_last_answer(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    answers = iter(["v1.3.0", "", "v1.4.0"])
    asked: list[int] = []

    def ask() -> str:
        asked.append(1)
        return next(answers)

    monkeypatch.setattr(update, "ask_latest", ask)
    assert update.latest(now=1_000_000.0) == "v1.3.0"
    assert update.latest(now=1_000_000.0 + 3600) == "v1.3.0" and len(asked) == 1
    assert update.latest(now=1_000_000.0 + 25 * 3600) == "v1.3.0" and len(asked) == 2
    assert update.latest(now=1_000_000.0 + 50 * 3600) == "v1.4.0" and len(asked) == 3


def test_the_page_is_told_what_is_out_and_whether_this_copy_can_install_it(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(update, "ask_latest", lambda: "v1.3.0")
    monkeypatch.setattr(update, "installed_by_uv", lambda: False)
    state = update.view()
    assert (state["current"], state["latest"], state["available"]) == ("1.2.3", "1.3.0", True)
    assert state["automatic"] and not state["can_install"] and not state["failed"]
    config.save("auto_update", "no")
    assert not update.view()["automatic"]


def test_a_copy_run_from_source_is_never_replaced(home: Path,
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    started: list[list[str]] = []
    monkeypatch.setattr(installer, "start_detached", lambda command, _log: started.append(command))
    monkeypatch.setattr(update, "installed_by_uv", lambda: False)
    assert not update.start("v1.3.0", 17653) and started == []


def test_the_installer_is_handed_the_release_archive_and_this_engines_process(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    started: list[list[str]] = []
    monkeypatch.setattr(installer, "start_detached", lambda command, _log: started.append(command))
    monkeypatch.setattr(installer, "UPDATE_STATE", home / "update.json")
    monkeypatch.setattr(installer, "HOME", home)
    monkeypatch.setattr(update, "installed_by_uv", lambda: True)
    monkeypatch.setattr(update.shutil, "which", lambda _name: "uv")
    assert update.start("v1.3.0", 17700)
    command = started[0]
    assert command[-5:-4] == [update.archive("v1.3.0")] and command[-2:] == ["--port", "17700"]
    assert Path(command[command.index("python") + 1]).read_bytes() == Path(
        installer.__file__).read_bytes()
    assert not update.start("not-a-tag; rm -rf", 17700)


def test_every_part_of_tarjim_carries_the_same_version() -> None:
    import json
    import tomllib

    import tarjim

    root = Path(tarjim.__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    plugin = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    extension = json.loads((root / "tarjim" / "extension" / "manifest.json").read_text(
        encoding="utf-8"))
    versions = {project["project"]["version"], plugin["version"], extension["version"],
                tarjim.__version__}
    assert len(versions) == 1
