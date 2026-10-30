"""A translation that slid down the slots is caught and asked for again.

The data is a real answer (2026-10-30) for a U.S. Central Command statement, a U.S. government
work: each Arabic line holds the previous English line's meaning from slot 2 on."""
import json
from pathlib import Path

from tarjim.models import Cue, Word
from tarjim.translate.drift import slid
from tarjim.translate.gemini import Translator
from tarjim.translate.prompt import Brief

ANSWER = json.loads((Path(__file__).parent / "data" / "centcom_slid_answer.json")
                    .read_text(encoding="utf-8"))


def cues_for(rows: list[list[str]]) -> list[Cue]:
    made = []
    for k, (source, text) in enumerate(rows):
        words = [Word(w, k * 3.0, k * 3.0 + 2.5) for w in source.split()]
        made.append(Cue(k * 3.0, k * 3.0 + 2.5, words, text=text))
    return made


def in_place(rows: list[list[str]]) -> list[list[str]]:
    """The same lines, each translated in its own slot: as long as its source, roughly."""
    return [[source, "ب" * max(3, round(len(source) * 0.8))] for source, _text in rows]


def test_the_slid_answer_is_caught_and_a_matching_one_is_not() -> None:
    assert slid(cues_for(ANSWER))
    assert not slid(cues_for(in_place(ANSWER)))
    assert not slid(cues_for(ANSWER[:5]))  # too few lines to tell


class Twice:
    hears = False

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def ask(self, prompt: str, _audio: bytes | None, _schema: dict[str, object]) -> object:
        self.prompts.append(prompt)
        rows = ANSWER if len(self.prompts) == 1 else in_place(ANSWER)
        return [{"id": k, "text": text} for k, (_s, text) in enumerate(rows, start=1)]


def test_a_slid_answer_is_asked_again_and_the_better_one_kept() -> None:
    client = Twice()
    cues = cues_for([[source, ""] for source, _text in ANSWER])
    Translator(client).translate(cues, lambda _a, _b: b"", Brief())
    assert len(client.prompts) == 2 and "زحلقت" in client.prompts[1]
    assert not slid(cues)


def test_a_slide_in_one_stretch_of_a_long_answer_is_caught() -> None:
    good = in_place(ANSWER) * 3  # a long answer in place everywhere...
    middle = [[s, t] for s, t in ANSWER[10:26]]  # ...except a slid stretch in the middle
    rows = good[:30] + middle + good[30:60]
    assert not slid(cues_for(good))
    assert slid(cues_for(rows))
