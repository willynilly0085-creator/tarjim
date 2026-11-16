"""A selected text is answered soon: a program already waiting, and the soonest engine first."""
import json
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from tarjim import text, text_engine
from tarjim.engines import antigravity, choice, waiting
from tarjim.engines.web import EngineError

PROGRAM = str(Path(__file__).with_name("waiting_program.py"))


def kind(light: str = "light", plain: str = "picked") -> waiting.Kind:
    return waiting.Kind(lambda is_light: [sys.executable, PROGRAM, light if is_light else plain],
                        lambda prompt: json.dumps({"message": {"content": prompt}}),
                        antigravity.spoken)


def until(true: Any) -> bool:
    deadline = time.monotonic() + 10
    while not true() and time.monotonic() < deadline:
        time.sleep(0.02)
    return bool(true())


@pytest.fixture
def held() -> Any:
    one = waiting.Waiting()
    yield one
    one.retire()


def test_the_waiting_program_answers_and_another_takes_its_place(held: waiting.Waiting) -> None:
    held.ready(kind().command(False))
    first = held.held
    assert first is not None
    assert held.ask(kind(), "hello", False) == {"translation": "picked: hello"}
    assert until(lambda: held.held is not None and held.held is not first)
    assert until(lambda: first.program.poll() is not None)  # asked once, then ended
    assert until(lambda: not Path(first.folder.name).exists())


def test_a_program_started_for_another_model_is_ended_and_not_asked(
        held: waiting.Waiting) -> None:
    held.ready(kind().command(False))
    other = held.held
    assert other is not None
    assert held.ask(kind(), "hello", True) == {"translation": "light: hello"}
    assert until(lambda: other.program.poll() is not None)


def test_a_waiting_program_that_ended_by_itself_is_replaced(held: waiting.Waiting) -> None:
    held.ready(kind().command(False))
    assert held.held is not None
    held.held.program.kill()
    held.held.program.wait()
    assert held.ask(kind(), "again", False) == {"translation": "picked: again"}


def test_one_nobody_asked_in_time_is_ended_and_no_other(held: waiting.Waiting) -> None:
    held.ready(kind().command(False))
    stale, held.held = held.held, None
    held.ready(kind().command(False))
    current = held.held
    assert stale is not None and current is not None and current.idle is not None
    held.retire(stale)  # its time came after another had taken its place
    assert held.held is current and current.program.poll() is None
    waiting.ended(stale)
    held.retire(current)
    assert held.held is None and current.program.poll() is not None


def test_a_waiting_program_that_fails_is_not_the_answer_and_logs_no_text(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    for how in ("dies", "refuses"):
        monkeypatch.setattr(waiting, "kinds", lambda how=how: {"agy": kind(plain=how)})
        assert waiting.answer("agy", "secret words", False) is None
    assert waiting.answer("gemini", "secret words", False) is None  # no program waits for it
    said = capsys.readouterr().out
    assert "the waiting agy gave no answer" in said and "secret words" not in said
    waiting.WAITING.retire()


class Says:
    hears = False

    def __init__(self) -> None:
        self.asked = 0

    def ask(self, _prompt: str, _audio: bytes | None, _schema: dict[str, Any]) -> Any:
        self.asked += 1
        return {"translation": "the usual way"}


def test_the_engine_is_asked_the_usual_way_only_when_its_waiting_program_fails(
        monkeypatch: pytest.MonkeyPatch) -> None:
    usual = Says()
    monkeypatch.setattr(text_engine, "over", dict)
    monkeypatch.setattr(choice, "soonest", lambda: ["agy"])
    monkeypatch.setattr(choice, "backed", iter)
    monkeypatch.setattr(choice, "asker", lambda _provider: usual)
    monkeypatch.setattr(waiting, "kinds", lambda: {"agy": kind()})
    said, by = text.translated("hello", "ar")
    assert said.startswith("light: ") and by == "agy" and usual.asked == 0
    monkeypatch.setattr(waiting, "kinds", lambda: {"agy": kind(light="dies")})
    assert text.translated("hello", "ar") == ("the usual way", "agy") and usual.asked == 1
    waiting.WAITING.retire()


def test_antigravity_waits_sandboxed_with_the_picked_model_or_its_low_variant(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(antigravity, "launcher", lambda _name: ["agy"])
    monkeypatch.setattr(antigravity, "setting", lambda _name: "gemini-4-hydrogen-high")
    monkeypatch.setattr(antigravity, "known_rows", lambda: [("gemini-4-hydrogen-low", "", "")])
    picked, light = antigravity.waiting_command(False), antigravity.waiting_command(True)
    assert picked[-2:] == ["--model", "gemini-4-hydrogen-high"]
    assert light[-2:] == ["--model", "gemini-4-hydrogen-low"]
    assert {"--sandbox", "--disable-slash-commands", "stream-json"} <= set(picked)
    assert "--json-schema" not in picked
    monkeypatch.setattr(antigravity, "launcher", lambda _name: [])
    assert antigravity.waiting_command(False) == []


def test_antigravitys_answer_is_its_result_line_and_nothing_before_it() -> None:
    asked = json.loads(antigravity.question("translate this"))
    assert asked == {"event": "user", "message": {"content": antigravity.DIRECT + "translate this"}}
    assert antigravity.spoken("not json") is None and antigravity.spoken("[1]") is None
    assert antigravity.spoken('{"event":"step_update","step_update":{}}') is None
    done = {"event": "result", "result": {"status": "SUCCESS",
                                          "response": '{"translation": "تم"}\n'}}
    assert antigravity.spoken(json.dumps(done)) == {"translation": "تم"}
    done["result"] = {"status": "ERROR", "error": "sign in"}
    with pytest.raises(EngineError, match="sign in"):
        antigravity.spoken(json.dumps(done))


def test_an_engine_with_a_key_is_asked_before_a_subscription_program(
        monkeypatch: pytest.MonkeyPatch) -> None:
    keys, usual = {"openai", "gemini", "custom"}, ["antigravity"]
    monkeypatch.setattr(choice, "has_key", lambda provider: provider in keys)
    monkeypatch.setattr(choice, "chosen", lambda _role: usual[0])
    assert choice.soonest() == ["gemini", "openai", "antigravity"]
    usual[0] = "openai"
    assert choice.soonest() == ["openai", "gemini"]
    keys.clear()
    assert choice.soonest() == ["openai"]


def test_a_person_who_translates_on_their_own_computer_sends_nothing_out(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(choice, "has_key", lambda _provider: True)
    monkeypatch.setattr(choice, "chosen", lambda _role: "local")
    assert choice.soonest() == ["local"]


def test_the_backup_on_this_computer_is_looked_for_only_once_the_others_failed(
        monkeypatch: pytest.MonkeyPatch) -> None:
    looked: list[str] = []
    monkeypatch.setattr(choice, "usable", lambda provider, _role: not looked.append(provider))
    turns = choice.backed(["gemini", "antigravity"])
    assert [next(turns), next(turns)] == ["gemini", "antigravity"] and looked == []
    assert list(turns) == ["local"] and looked == ["local"]
    assert list(choice.backed(["local"])) == ["local"] and looked == ["local"]
