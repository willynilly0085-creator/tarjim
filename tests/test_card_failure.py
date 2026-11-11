"""A graphics-card failure never fails a job (2026-11-10): the step runs again on the card once,
then on the processor, and the engine starts again when idle so the next job gets the card back."""
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from tarjim import card, device, memory, same_code
from tarjim.server import renew, update_routes
from tarjim.server.jobs import Order, Task

# What five jobs in a row failed with on 2026-11-10, the card nearly empty all the while.
SEEN = ("CUDA out of memory. Tried to allocate 2.00 MiB. GPU 0 has a total capacity of 15.89 GiB "
        "of which 0 bytes is free. Process 1816 has 17179869184.00 GiB memory in use.")


class OutOfMemoryError(RuntimeError):
    """Named as torch names its own."""


@pytest.fixture(autouse=True)
def with_a_card(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    freed: list[str] = []
    monkeypatch.setattr(device, "card_present", lambda: True)
    monkeypatch.setattr(memory, "drop_models", lambda: freed.append(device.best_device()))
    device.CARD_FAILED.clear()
    yield freed
    device.CARD_FAILED.clear()


def step(failures: list[Exception]) -> Callable[[], str]:
    def run() -> str:
        if failures:
            raise failures.pop(0)
        return device.best_device()
    return run


def test_the_failure_the_owner_saw_is_the_cards() -> None:
    assert card.card_failure(RuntimeError(SEEN))
    assert card.card_failure(OutOfMemoryError("no room"))
    assert card.card_failure(RuntimeError("cuDNN error: CUDNN_STATUS_EXECUTION_FAILED"))
    assert card.card_failure(RuntimeError("device-side assert triggered"))
    assert card.card_failure(RuntimeError("CUDA error: unknown error"))


def test_other_failures_are_not_the_cards() -> None:
    assert not card.card_failure(RuntimeError("the sound has no speech"))
    assert not card.card_failure(ValueError("CUDA is a word in a video's title"))
    assert not card.card_failure(MemoryError())


def test_a_card_that_fails_once_is_tried_again_on_the_card(
        with_a_card: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert card.survive(step([RuntimeError(SEEN)]), "timing") == "cuda:0"
    assert with_a_card == ["cuda:0"] and not device.CARD_FAILED.is_set()
    assert capsys.readouterr().out.count("\n") == 1


def test_a_card_that_fails_twice_gives_the_step_to_the_processor(
        with_a_card: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert card.survive(step([RuntimeError(SEEN), OutOfMemoryError("x")]), "timing") == "cpu"
    assert device.best_device() == "cpu" and with_a_card == ["cuda:0", "cpu"]
    said = capsys.readouterr().out
    assert said.count("\n") == 2 and "processor" in said


def test_at_most_card_card_processor() -> None:
    always = [RuntimeError(SEEN)] * 5
    with pytest.raises(RuntimeError, match="CUDA"):
        card.survive(step(always), "timing")
    assert len(always) == 2


def test_another_failure_passes_straight_through(with_a_card: list[str]) -> None:
    with pytest.raises(RuntimeError, match="no speech"):
        card.survive(step([RuntimeError("the sound has no speech")]), "timing")
    assert with_a_card == [] and not device.CARD_FAILED.is_set()


def test_a_failure_on_the_processor_is_not_tried_again(with_a_card: list[str]) -> None:
    device.CARD_FAILED.set()
    with pytest.raises(RuntimeError, match="CUDA"):
        card.survive(step([RuntimeError(SEEN)]), "timing")
    assert with_a_card == []


def test_a_cancel_takes_effect_between_the_tries(monkeypatch: pytest.MonkeyPatch) -> None:
    class Stopped(Exception):
        pass

    def stop() -> None:
        raise Stopped

    monkeypatch.setattr(card, "checkpoint", stop)
    with pytest.raises(Stopped):
        card.survive(step([RuntimeError(SEEN)]), "timing")


def test_a_broken_card_does_not_stop_the_models_being_freed(
        monkeypatch: pytest.MonkeyPatch) -> None:
    import torch

    def broken() -> None:
        raise RuntimeError("CUDA error: unknown error")

    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "empty_cache", broken)
    memory.empty_card()


class Busy:
    def __init__(self, finished: bool) -> None:
        self.task = Task(Order("https://example.com/v"), stage="done" if finished else "hearing")

    def recent(self) -> list[Task]:
        return [self.task]


@pytest.fixture
def started(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    calls: list[list[str]] = []
    monkeypatch.setattr(renew, "HOME", tmp_path)
    monkeypatch.setattr(renew, "start_detached", lambda command, _log, here: calls.append(
        command) or True)
    monkeypatch.setattr(update_routes, "close_soon", lambda started, _board=None: started)
    monkeypatch.setattr(update_routes, "look", lambda *_args: None)
    monkeypatch.setattr(update_routes, "upgrade_listening", lambda _board: None)
    return calls


def test_the_engine_starts_again_for_the_card_only_when_idle_and_only_once(
        tmp_path: Path, started: list[list[str]], capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "code").mkdir()
    renewal = renew.Renewal(same_code.Snapshot(tmp_path / "code", "code"))
    update_routes.tick(Busy(finished=True), 17701, renewal, 1)  # type: ignore[arg-type]
    assert started == []  # the card is well
    device.CARD_FAILED.set()
    update_routes.tick(Busy(finished=False), 17701, renewal, 2)  # type: ignore[arg-type]
    assert started == []  # a job is running
    for count in (3, 4):
        update_routes.tick(Busy(finished=True), 17701, renewal, count)  # type: ignore[arg-type]
    assert len(started) == 1 and "--after" in started[0]
    assert "graphics card" in capsys.readouterr().out


def test_the_timing_step_finishes_on_the_processor_when_the_card_is_broken(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim.asr import align
    from tarjim.listen.timing import Timer

    built: list[str] = []

    class Aligner:
        def __init__(self) -> None:
            self.device = device.best_device()
            built.append(self.device)

        def align(self, *_args: object) -> list[str]:
            if self.device != "cpu":
                raise RuntimeError(SEEN)
            return ["timed"]

    monkeypatch.setattr(align, "shared_aligner", Aligner)
    assert Timer(None, 16000, "en", []).aligned(None, []) == (["timed"], set())
    assert built == ["cuda:0", "cuda:0", "cpu"]
