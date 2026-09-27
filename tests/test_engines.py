from typing import Any

import pytest

from tarjim.engines import anthropic_api, choice, ollama, openai_api, web
from tarjim.engines.local_listen import utterances_from
from tarjim.models import Cue, Word
from tarjim.translate.gemini import Translator
from tarjim.translate.prompt import Brief, build_prompt


def capture(monkeypatch: pytest.MonkeyPatch, module: Any, answer: Any) -> list[dict[str, Any]]:
    seen: list[dict[str, Any]] = []

    def fake_post(provider: str, url: str, headers: dict[str, str], **payload: Any) -> Any:
        seen.append({"provider": provider, "url": url, "headers": headers, **payload})
        return answer

    monkeypatch.setattr(module, "post", fake_post)
    monkeypatch.setattr(module, "setting", lambda name: "sk-test" if name.endswith("key") else "")
    return seen


def test_openai_translation_asks_for_json_and_unwraps_it(monkeypatch: pytest.MonkeyPatch) -> None:
    content = '{"result": [{"id": 1, "text": "Hola"}]}'
    seen = capture(monkeypatch, openai_api, {"choices": [{"message": {"content": content}}]})
    assert openai_api.OpenAIAsker().ask("p", None, {"type": "array"}) == [{"id": 1, "text": "Hola"}]
    assert seen[0]["headers"]["Authorization"] == "Bearer sk-test"
    assert seen[0]["json"]["response_format"]["type"] == "json_schema"


def test_openai_listening_keeps_speakers_and_times(monkeypatch: pytest.MonkeyPatch) -> None:
    segments = {"segments": [{"speaker": "B", "start": 2.0, "end": 3.0, "text": "Nice."},
                             {"speaker": "A", "start": 0.5, "end": 1.8, "text": "Once a month."}]}
    capture(monkeypatch, openai_api, segments)
    _, heard = openai_api.listen(b"mp3")
    assert [(u.speaker, u.text) for u in heard] == [("A", "Once a month."), ("B", "Nice.")]


def test_claude_answers_through_a_forced_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    reply = {"content": [{"type": "tool_use", "input": {"result": [{"id": 1, "text": "Hi"}]}}]}
    seen = capture(monkeypatch, anthropic_api, reply)
    assert anthropic_api.AnthropicAsker().ask("p", None, {}) == [{"id": 1, "text": "Hi"}]
    assert seen[0]["json"]["tool_choice"] == {"type": "tool", "name": "answer"}


def test_local_model_gets_the_schema_as_format(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = capture(monkeypatch, ollama, {"message": {"content": '{"result": []}'}})
    assert ollama.OllamaAsker().ask("p", None, {"type": "array"}) == []
    assert seen[0]["json"]["format"] == web.wrap({"type": "array"})


def test_engines_that_cannot_hear_get_no_audio_and_are_not_told_to_listen() -> None:
    class Deaf:
        hears = False

        def __init__(self) -> None:
            self.calls: list[Any] = []

        def ask(self, prompt: str, audio: bytes | None, schema: dict[str, Any]) -> Any:
            self.calls.append((prompt, audio))
            return [{"id": 1, "text": "Bonjour"}]

    cue = Cue(0.0, 1.0, [Word("Hello", 0.0, 1.0)])
    deaf = Deaf()
    Translator(deaf).translate([cue], lambda _a, _b: b"audio", Brief())  # type: ignore[arg-type]
    prompt, audio = deaf.calls[0]
    assert audio is None and "اسمع الصوت" not in prompt and cue.text == "Bonjour"
    assert "اسمع الصوت" in build_prompt([cue], Brief())


def test_local_listening_groups_words_into_sentences_at_pauses() -> None:
    words = [Word("Once", 0.0, 0.3), Word("a", 0.3, 0.4), Word("month.", 0.4, 0.8),
             Word("Nice", 0.9, 1.1), Word("one", 2.5, 2.8)]
    assert [u.text for u in utterances_from(words)] == ["Once a month.", "Nice", "one"]


def test_the_local_engine_backs_up_the_chosen_one(monkeypatch: pytest.MonkeyPatch) -> None:
    values = {"translate_provider": "anthropic", "anthropic_api_key": "k"}
    monkeypatch.setattr(choice, "setting", lambda name: values.get(name, ""))
    monkeypatch.setattr(choice, "local_translation_ready", lambda: True)
    assert choice.chain("translate") == ["anthropic", "local"]
    assert choice.chain("listen") == ["local"]
