from typing import Any

from tarjim.models import Cue, Word
from tarjim.translate.gemini import GeminiTranslator, needs_retry


class FakeClient:
    def __init__(self, answers: list[list[dict[str, Any]]]) -> None:
        self.answers = answers
        self.prompts: list[str] = []

    def ask(self, prompt: str, audio: bytes, schema: dict[str, Any]) -> Any:
        self.prompts.append(prompt)
        return self.answers.pop(0)


def dialogue_cue() -> Cue:
    first, second = [Word("Once.", 27.2, 27.8, "S7")], [Word("Yeah?", 28.2, 28.7, "S1")]
    return Cue(27.2, 28.7, first + second, parts=[first, second])


def test_dialogue_that_lost_a_speaker_is_retranslated() -> None:
    cue = dialogue_cue()
    client = FakeClient([[{"id": 1, "ar": "مرة"}], [{"id": 1, "ar": "مرة || صدق؟"}]])
    GeminiTranslator(client).translate([cue], b"", "saudi")  # type: ignore[arg-type]
    assert cue.text == "مرة || صدق؟"
    assert len(client.prompts) == 2


def test_needs_retry_ignores_pure_noise_cues() -> None:
    assert not needs_retry(Cue(0, 1, [Word("...", 0, 1)]), strict_dialogue=True)
