"""A selected text gets a second request when the first is held (tarjim/hedge.py, 2026-11-25)."""
import threading
import time

import pytest

from tarjim import config, text
from tarjim.hedge import hedged


def test_a_quick_answer_is_asked_once() -> None:
    calls: list[int] = []
    assert hedged(lambda: calls.append(1) or "quick", after=1.0) == "quick"
    assert calls == [1]


def test_a_held_request_is_overtaken_by_a_second_one() -> None:
    first = threading.Event()

    def ask() -> str:
        if not first.is_set():
            first.set()
            time.sleep(3)  # Google held one request a minute; here three seconds
            return "late"
        return "second"

    started = time.monotonic()
    assert hedged(ask, after=0.2) == "second"
    assert time.monotonic() - started < 2


def test_one_failing_still_waits_for_the_other() -> None:
    first = threading.Event()

    def ask() -> str:
        if not first.is_set():
            first.set()
            time.sleep(0.4)
            raise RuntimeError("503")
        time.sleep(0.6)
        return "kept"

    assert hedged(ask, after=0.1) == "kept"


def test_both_failing_raise_the_first_error() -> None:
    def ask() -> str:
        time.sleep(0.3)
        raise ValueError("bad key")

    with pytest.raises(ValueError, match="bad key"):
        hedged(ask, after=0.1)


def test_the_second_request_runs_under_the_same_settings() -> None:
    seen: list[str] = []

    def ask() -> str:
        seen.append(config.setting("gemini_model"))
        time.sleep(0.3 if len(seen) == 1 else 0)
        return "x"

    with config.using({"gemini_model": "light-one"}):
        hedged(ask, after=0.1)
    assert seen == ["light-one", "light-one"]


def test_only_engines_asked_over_the_web_with_a_key_get_a_second_request() -> None:
    assert text.keyed("gemini") and text.keyed("openai")
    assert not text.keyed("claude") and not text.keyed("antigravity")  # a program to start
    assert not text.keyed("local")  # a model on this computer
