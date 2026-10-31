"""An empty, blocked or cut-off reply names its reason and model, whatever engine gave it."""
import enum
import json
from types import SimpleNamespace
from typing import Any

import pytest

from tarjim.engines import anthropic_api, ollama
from tarjim.engines.reply_check import (
    ReplyFailed,
    anthropic_reason,
    chat_reason,
    checked,
    gemini_reason,
    ollama_reason,
    program_reason,
)
from tarjim.engines.web import EngineError, reply_text


class FinishReason(enum.Enum):
    MAX_TOKENS = 2


def test_gemini_reasons_are_read_from_the_library_object_and_from_json() -> None:
    response = SimpleNamespace(candidates=[SimpleNamespace(finish_reason=FinishReason.MAX_TOKENS)],
                               prompt_feedback=None)
    assert gemini_reason(response).finish == "MAX_TOKENS"
    blocked = {"candidates": [], "promptFeedback": {"blockReason": "SAFETY"}}
    assert gemini_reason(blocked).block == "SAFETY"


def test_a_cut_off_gemini_reply_fails_with_its_reason_not_a_json_error(
        capsys: pytest.CaptureFixture[str]) -> None:
    response = SimpleNamespace(candidates=[SimpleNamespace(finish_reason=FinishReason.MAX_TOKENS)])
    with pytest.raises(ReplyFailed, match=r"gemini \(m-1\): cut off \[finish_reason=MAX_TOKENS\]"):
        checked("gemini", "m-1", '{"utterances": [{"start": 1', gemini_reason(response))
    assert "reply: gemini (m-1): cut off" in capsys.readouterr().out


def test_a_blocked_reply_says_blocked() -> None:
    with pytest.raises(ReplyFailed, match=r"blocked .*block_reason=PROHIBITED_CONTENT"):
        checked("gemini", "m", None, gemini_reason({"promptFeedback": {
            "blockReason": "PROHIBITED_CONTENT"}}))


def test_the_chat_format_names_length_and_the_model() -> None:
    answer = {"model": "some-model-7b", "choices": [
        {"finish_reason": "length", "message": {"content": '{"result": ['}}]}
    with pytest.raises(EngineError, match=r"openrouter \(some-model-7b\): cut off"):
        reply_text("openrouter", answer)
    empty = {"model": "x", "choices": [{"finish_reason": "stop", "message": {"content": ""}}]}
    with pytest.raises(ReplyFailed, match="empty reply"):
        reply_text("custom", empty)
    assert chat_reason({"choices": [{"message": {"refusal": "no"}}]}).detail == "refusal: no"


def test_a_good_chat_reply_passes() -> None:
    answer = {"choices": [{"finish_reason": "stop", "message": {"content": "{}"}}]}
    assert reply_text("openai", answer) == "{}"


def test_anthropic_names_its_stop_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    assert anthropic_reason({"stop_reason": "max_tokens"}).problem(True) == "cut off"
    reply = {"model": "claude-x", "stop_reason": "end_turn", "content": [{"type": "text"}]}
    monkeypatch.setattr(anthropic_api, "post", lambda *_a, **_k: reply)
    with pytest.raises(ReplyFailed, match=r"anthropic \(claude-x\): empty reply .*end_turn"):
        anthropic_api.AnthropicAsker().ask("hi", None, {"type": "object"})


def test_a_local_server_names_its_done_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    reply: dict[str, Any] = {"message": {"content": '{"result": [1'}, "done_reason": "length"}
    monkeypatch.setattr(ollama, "post", lambda *_a, **_k: reply)
    with pytest.raises(ReplyFailed, match=r"local \(.+\): cut off \[finish_reason=length\]"):
        ollama.OllamaAsker().ask("hi", None, {"type": "object"})
    assert ollama_reason({}).text() == ""


def test_a_program_gives_its_exit_code_and_the_end_of_its_complaint() -> None:
    long_complaint = "x" * 500 + " quota exceeded"
    text = program_reason(3, long_complaint).text()
    assert text.startswith("exit code 3; stderr: ...") and text.endswith("quota exceeded")
    assert program_reason(0, "").text() == "exit code 0"


def test_a_program_failure_is_still_an_engine_error_with_the_model() -> None:
    from tarjim.engines import antigravity

    with pytest.raises(EngineError, match=r"antigravity \(flash-low\): no answer \[exit code 1"):
        antigravity.answer_of(1, json.dumps({"status": "ERROR", "error": "busy"}), "", "flash-low")
