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
    assert shelf.start("timing") and shelf.start("dubbing")
    assert not shelf.start("unknown-tool")
    for _ in range(50):
        if all(shelf.progress[k].state != "downloading" for k in ("timing", "dubbing")):
            break
        time.sleep(0.02)
    view = {row["id"]: row for row in shelf.view()}
    assert view["timing"]["state"] == "done"
    assert view["dubbing"]["state"] == "failed" and "disk full" in str(view["dubbing"]["detail"])
    assert sorted(calls) == ["dubbing", "timing"]
