"""A computer that listened with the earlier Qwen3-ASR pair keeps listening with it while the
native pair downloads in the background; once that is fully here the next job uses it and the
earlier pair is removed. Nobody is left without local listening, and a new install only ever
gets the native pair."""
from typing import Any

import pytest

from tarjim import listen_upgrade, memory, model_pins, tools

NATIVE = set(listen_upgrade.NATIVE)
EARLIER = set(listen_upgrade.EARLIER)
NOW = 1_000_000.0


class Shelf:
    def __init__(self, state: str = "idle") -> None:
        self.progress = {tool.id: tools.Progress() for tool in tools.TOOLS}
        self.progress["accuracy"] = tools.Progress(state)
        self.started: list[str] = []

    def start(self, tool_id: str, accepted: bool = False) -> str:
        self.started.append(tool_id)
        self.progress[tool_id] = tools.Progress("downloading")
        return "started"


@pytest.fixture
def here(monkeypatch: pytest.MonkeyPatch) -> set[str]:
    found: set[str] = set()
    monkeypatch.setattr(model_pins, "ready", lambda repo: repo in found)
    monkeypatch.setattr(listen_upgrade, "TRIED", [])
    monkeypatch.setattr(listen_upgrade, "room_for_download", lambda: True)
    monkeypatch.setattr("tarjim.update.automatic", lambda: True)
    return found


def test_with_only_the_earlier_pair_it_listens_and_the_native_pair_starts_downloading(
        here: set[str]) -> None:
    here |= EARLIER
    shelf = Shelf()
    assert listen_upgrade.state() == "earlier" and listen_upgrade.listening_ready()
    assert tools.installed(tools.BY_ID["accuracy"])
    assert listen_upgrade.step(shelf, idle=True, now=NOW) == "started"
    assert shelf.started == ["accuracy"]


def test_nothing_starts_while_a_job_runs_or_while_it_is_already_downloading(
        here: set[str]) -> None:
    here |= EARLIER
    assert listen_upgrade.step(Shelf(), idle=False, now=NOW) == "earlier"
    busy = Shelf("downloading")
    assert listen_upgrade.step(busy, idle=True, now=NOW) == "downloading" and not busy.started


def test_a_failed_download_keeps_the_earlier_pair_and_is_tried_again_an_hour_later(
        here: set[str]) -> None:
    here |= EARLIER
    first = Shelf()
    listen_upgrade.step(first, idle=True, now=NOW)
    failed = Shelf("failed")
    assert listen_upgrade.step(failed, idle=True, now=NOW + 600) == "waiting"
    assert listen_upgrade.listening_ready() and listen_upgrade.upgrade_view(failed) == {
        "upgrade": "failed"}
    assert listen_upgrade.step(failed, idle=True, now=NOW + 3601) == "started"


def test_it_waits_for_disk_space(here: set[str], monkeypatch: pytest.MonkeyPatch) -> None:
    here |= EARLIER
    monkeypatch.setattr(listen_upgrade, "room_for_download", lambda: False)
    shelf = Shelf()
    assert listen_upgrade.step(shelf, idle=True, now=NOW) == "waiting for disk space"
    assert not shelf.started


def test_with_automatic_updates_off_settings_offers_the_download_instead(
        here: set[str], monkeypatch: pytest.MonkeyPatch) -> None:
    here |= EARLIER
    monkeypatch.setattr("tarjim.update.automatic", lambda: False)
    shelf = Shelf()
    assert listen_upgrade.step(shelf, idle=True, now=NOW) == "earlier" and not shelf.started
    assert listen_upgrade.upgrade_view(shelf) == {"upgrade": "manual"}


@pytest.fixture
def removed(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    gone: list[str] = []
    monkeypatch.setattr(model_pins, "remove", lambda repo: gone.append(repo) or True)
    monkeypatch.setattr(listen_upgrade, "earlier_left", lambda: not gone)
    return gone


def test_once_the_native_pair_is_here_the_engine_lets_go_and_the_earlier_pair_is_removed(
        here: set[str], removed: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    released: list[bool] = []
    monkeypatch.setattr(memory, "release_listening", lambda: released.append(True))
    here |= NATIVE | EARLIER
    assert listen_upgrade.step(Shelf(), idle=True, now=NOW) == "removed earlier"
    assert set(removed) == EARLIER and released == [True]
    assert listen_upgrade.step(Shelf(), idle=True, now=NOW) == "native" and released == [True]
    assert listen_upgrade.upgrade_view(Shelf()) == {}


def test_the_earlier_pair_stays_while_a_job_still_holds_a_model(
        here: set[str], removed: list[str]) -> None:
    here |= NATIVE | EARLIER
    assert memory.HEAVY.acquire(blocking=False)
    try:
        import threading

        result: list[str] = []
        worker = threading.Thread(target=lambda: result.append(
            listen_upgrade.step(Shelf(), idle=True, now=NOW)))
        worker.start()
        worker.join()
    finally:
        memory.HEAVY.release()
    assert result == ["native"] and not removed


def test_a_removal_that_fails_leaves_the_native_pair_listening(
        here: set[str], monkeypatch: pytest.MonkeyPatch) -> None:
    def locked(_repo: str) -> bool:
        raise PermissionError("in use")

    here |= NATIVE | EARLIER
    monkeypatch.setattr(model_pins, "remove", locked)
    monkeypatch.setattr(listen_upgrade, "earlier_left", lambda: True)
    assert listen_upgrade.step(Shelf(), idle=True, now=NOW) == "native"
    assert listen_upgrade.listening_ready()


def test_a_new_install_has_nothing_to_move_and_downloads_only_the_native_pair(
        here: set[str]) -> None:
    shelf = Shelf()
    assert listen_upgrade.step(shelf, idle=True, now=NOW) == "none" and not shelf.started
    assert not tools.installed(tools.BY_ID["accuracy"])
    assert set(tools.BY_ID["accuracy"].sources) == NATIVE


def test_the_listening_row_and_setup_status_show_the_download(
        here: set[str], monkeypatch: pytest.MonkeyPatch) -> None:
    import tarjim.assistant_http
    from tarjim import assistant_setup

    here |= EARLIER
    shelf = Shelf("downloading")
    monkeypatch.setattr(tools, "ollama_ready", lambda _model: False)
    row = next(t for t in tools.Shelf.view(shelf) if t["id"] == "accuracy")  # type: ignore[arg-type]
    assert row["installed"] and row["upgrade"] == "downloading" and row["size_gb"] == 5.9
    reply: Any = [row]
    monkeypatch.setattr(assistant_setup, "running", lambda: True)
    monkeypatch.setattr(tarjim.assistant_http, "call",
                        lambda path: reply if path == "/tools" else {})
    status = assistant_setup.status()
    assert status["listening_models_update"] == "downloading"
    assert "takes over by itself" in status["listening_models_note"]
