""""Listen again" forgets the kept hearing of a clip, so a retry really listens once more: from the
command line, the page, the browser extension and chat alike."""
import time
from pathlib import Path

import pytest

from tarjim import assistant, cli, hearing
from tarjim.asr.base import Transcript
from tarjim.job import Job
from tarjim.listen.kept import forget
from tarjim.server.jobs import Board, Order, Task
from tarjim.server.orders import order_from
from tarjim.server.routes import POST_ROUTES

KEPT = ("heard.json", "transcript.json", "cues.ar.json", "cues.fr.json")
WEB = Path(__file__).parent.parent / "tarjim"


def filled(cache: Path) -> Path:
    cache.mkdir(parents=True, exist_ok=True)
    for name in (*KEPT, "cuts.json", "source.json"):
        (cache / name).write_text("{}", encoding="utf-8")
    return cache


def test_forget_clears_the_hearing_and_what_was_made_from_it(tmp_path: Path) -> None:
    cache = filled(tmp_path / "clip")
    forget(cache)
    assert not any((cache / name).exists() for name in KEPT)
    assert (cache / "cuts.json").exists() and (cache / "source.json").exists()


def test_a_listen_again_job_does_not_use_the_kept_transcript(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    job = Job(tmp_path / "clip.mp4", cache_dir=tmp_path / "cache", relisten=True)
    filled(job.cache)
    heard: list[bool] = []

    def hear(_job: Job, _audio: Path, _report: object) -> tuple[Transcript, bool]:
        heard.append((job.cache / "heard.json").exists())
        return Transcript("English", ""), False

    import tarjim.memory

    monkeypatch.setattr(tarjim.memory, "free_for_listening", lambda: None)
    monkeypatch.setattr(hearing.media, "extract_audio", lambda _v, target: target)
    monkeypatch.setattr(hearing, "hear", hear)
    hearing.transcript_for(job, lambda _stage: None)
    assert heard == [False]


def test_the_command_line_has_listen_again() -> None:
    assert cli.parse(["clip.mp4", "--listen-again"]).listen_again is True
    assert cli.parse(["clip.mp4"]).listen_again is False


def test_an_order_asks_for_it_only_when_told() -> None:
    assert order_from("v.mp4", {"relisten": True}).relisten is True
    assert order_from("v.mp4", {"relisten": "yes"}).relisten is False
    assert order_from("v.mp4", {}).relisten is False


def test_a_finished_job_can_be_listened_to_again() -> None:
    board = Board(lambda _task: None)
    task = board.submit(Order("https://example.com/v", target="en"))
    for _ in range(50):
        if task.finished:
            break
        time.sleep(0.02)
    again = board.relisten(task.id)
    assert again is not None and again.order.relisten and again.order.target == "en"
    assert board.relisten("000000000000") is None


def test_a_running_job_is_not_listened_to_again() -> None:
    running = Task(Order("https://example.com/v"))
    board = Board(lambda _task: time.sleep(1))
    board.tasks[running.id] = running
    assert board.relisten(running.id) is None


def test_the_page_extension_and_chat_reach_the_route(monkeypatch: pytest.MonkeyPatch) -> None:
    assert any(name == "relisten" for _pattern, name in POST_ROUTES)
    sent: list[str] = []
    monkeypatch.setattr(assistant, "call", lambda path, _body: sent.append(path) or {})
    assistant.control_translation("abc123abc123", "listen_again")
    assert sent == ["/relisten/abc123abc123"]
    for page in ("web/jobs.js", "extension/jobs.js"):
        assert "/relisten/" in (WEB / page).read_text(encoding="utf-8")


@pytest.mark.parametrize("code", ["ar", "en"])
def test_the_button_is_worded(code: str) -> None:
    import json

    page = json.loads((WEB / "web" / "i18n" / f"{code}.json").read_text(encoding="utf-8"))
    extension = json.loads((WEB / "extension" / "_locales" / code / "messages.json")
                           .read_text(encoding="utf-8"))
    assert page["listenAgain"] and extension["listenAgain"]["message"]
