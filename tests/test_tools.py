import time

import pytest

from tarjim import tools


def test_a_tool_downloads_in_the_background_and_reports_failure_plainly(
        monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_fetch(tool: tools.Tool) -> None:
        calls.append(tool.id)
        if tool.id == "dubbing":
            raise OSError("disk full")

    monkeypatch.setattr(tools, "fetch", fake_fetch)
    monkeypatch.setattr(tools, "installed", lambda _tool: False)
    shelf = tools.Shelf()
    assert shelf.start("timing") == "started"
    assert shelf.start("dubbing") == "started"
    assert shelf.start("unknown-tool") == "unknown"
    for _ in range(50):
        if all(shelf.progress[k].state != "downloading" for k in ("timing", "dubbing")):
            break
        time.sleep(0.02)
    view = {row["id"]: row for row in shelf.view()}
    assert view["timing"]["state"] == "done"
    assert view["dubbing"]["state"] == "failed" and "disk full" in str(view["dubbing"]["detail"])
    assert sorted(calls) == ["dubbing", "timing"]


def test_every_tool_says_its_license_and_non_commercial_ones_are_marked() -> None:
    views = {t.id: t.license for t in tools.TOOLS}
    assert views["dubbing"].commercial and not views["dubbing"].consent
    assert not views["timing"].commercial and not views["local_translation"].commercial
    assert views["accuracy"].commercial


SYSTEMS = [("win32", False), ("darwin", True), ("linux", True)]


@pytest.mark.parametrize(("system", "manual"), SYSTEMS)
def test_ffmpeg_is_downloaded_on_windows_and_installed_by_the_person_elsewhere(
        system: str, manual: bool, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tools.sys, "platform", system)
    monkeypatch.setattr(tools, "installed", lambda _tool: False)
    monkeypatch.setattr(tools, "fetch", lambda _tool: None)
    shelf = tools.Shelf()
    assert {row["id"]: row["manual"] for row in shelf.view()}["ffmpeg"] is manual
    assert (shelf.start("ffmpeg") == "manual") is manual
