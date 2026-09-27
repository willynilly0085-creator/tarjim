from typing import Any

from tarjim.languages import language
from tarjim.models import Cue, Word
from tarjim.translate.gemini import GeminiTranslator, batches, needs_retry
from tarjim.translate.prompt import Brief, build_prompt


class FakeClient:
    hears = True

    def __init__(self, answers: list[list[dict[str, Any]]]) -> None:
        self.answers = answers
        self.prompts: list[str] = []

    def ask(self, prompt: str, audio: bytes, schema: dict[str, Any]) -> Any:
        self.prompts.append(prompt)
        return self.answers.pop(0)


def silence(_start: float, _end: float) -> bytes:
    return b""


def dialogue_cue() -> Cue:
    first, second = [Word("Once.", 27.2, 27.8, "S7")], [Word("Yeah?", 28.2, 28.7, "S1")]
    return Cue(27.2, 28.7, first + second, parts=[first, second])


def test_dialogue_that_lost_a_speaker_is_retranslated() -> None:
    cue = dialogue_cue()
    client = FakeClient([[{"id": 1, "text": "مرة"}], [{"id": 1, "text": "مرة || صدق؟"}]])
    GeminiTranslator(client).translate([cue], silence, Brief())  # type: ignore[arg-type]
    assert cue.text == "مرة || صدق؟"
    assert len(client.prompts) == 2


def test_needs_retry_ignores_pure_noise_cues() -> None:
    assert not needs_retry(Cue(0, 1, [Word("...", 0, 1)]), strict_dialogue=True)


def test_long_videos_are_translated_in_five_minute_batches_with_their_own_audio() -> None:
    cues = [Cue(t, t + 2, [Word("hi", t, t + 2)]) for t in range(0, 700, 100)]
    assert [len(b) for b in batches(cues)] == [3, 3, 1]
    asked: list[tuple[float, float]] = []

    def audio(start: float, end: float) -> bytes:
        asked.append((start, end))
        return b""

    answers = [[{"id": i, "text": "مرحبا"} for i in range(1, 4)]] * 2 + [[{"id": 1, "text": "x"}]]
    GeminiTranslator(FakeClient(answers)).translate(cues, audio, Brief())  # type: ignore[arg-type]
    assert asked[1] == (299.0, 503.0)


def test_other_languages_get_their_own_prompt_and_times_relative_to_the_audio_slice() -> None:
    cue = Cue(301.0, 303.0, [Word("hello", 301.0, 303.0)])
    prompt = build_prompt([cue], Brief(language("fr"), offset=300.0))
    assert "French" in prompt and "[1.0-3.0s" in prompt
