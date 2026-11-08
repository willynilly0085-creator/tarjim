"""Each line's speaker is checked against the voice heard in it: a line clearly in another
speaker's voice goes to that speaker; a close call, a short line or one speaker stays as heard."""
from typing import Any

import numpy as np
import pytest

from tarjim.asr import voiceprint
from tarjim.listen import whose
from tarjim.models import Word

HOST, GUEST = np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0])
RATE = voiceprint.RATE


def line(start: float, speaker: str) -> list[Word]:
    return [Word("one", start, start + 1.0, speaker), Word("two", start + 1.0, start + 2.0,
                                                           speaker)]


def voices_at(timeline: dict[float, np.ndarray]) -> Any:
    def print_of(clip: np.ndarray) -> np.ndarray:
        return timeline[round(float(clip[0]), 1)]

    return print_of


def sound(seconds: float) -> np.ndarray:
    """Each sample holds its own time, so a stretch tells where it starts."""
    return np.arange(int(seconds * RATE)) / RATE


@pytest.fixture
def heard(monkeypatch: pytest.MonkeyPatch) -> list[Word]:
    # the listener swapped the two after the pause at 12 s, as on 2026-11-06
    words = [*line(0, "S1"), *line(4, "S2"), *line(8, "S1"), *line(12, "S1"), *line(16, "S2")]
    timeline = {0.0: HOST, 4.0: GUEST, 8.0: HOST, 12.0: GUEST, 16.0: HOST}
    monkeypatch.setattr(voiceprint, "print_of", voices_at(timeline))
    return words


def test_a_line_in_the_other_speakers_voice_goes_to_that_speaker(heard: list[Word]) -> None:
    checked = whose.checked(heard, sound(20))
    assert [w.speaker for w in checked[::2]] == ["S1", "S2", "S1", "S2", "S1"]


def test_voices_too_alike_to_tell_leave_the_labels_as_heard(
        monkeypatch: pytest.MonkeyPatch, heard: list[Word]) -> None:
    alike = np.array([0.7, 0.71, 0.0]) / np.linalg.norm([0.7, 0.71, 0.0])
    monkeypatch.setattr(voiceprint, "print_of", lambda _clip: alike)
    assert whose.checked(heard, sound(20)) == heard


def test_one_speaker_or_no_model_leaves_the_words_alone(
        monkeypatch: pytest.MonkeyPatch, heard: list[Word]) -> None:
    alone = [*line(0, "S1"), *line(4, "S1")]
    assert whose.by_voice(alone, sound(8)) == alone
    monkeypatch.setattr(voiceprint, "fetched", lambda: False)
    assert whose.by_voice(heard, sound(20)) == heard


def test_lines_too_short_to_know_a_voice_by_keep_their_label(heard: list[Word]) -> None:
    short = [Word("yes", 20.0, 20.5, "S2")]
    assert whose.checked([*heard, *short], sound(21))[-1].speaker == "S2"


def test_every_speaker_of_the_clip_is_compared_and_one_with_no_other_line_stays() -> None:
    # pieces share the listener's labels since 2026-10-31, so there is no piece to keep apart
    assert whose.nearer(GUEST, "S1", {"S1": HOST, "S2": GUEST}) == "S2"
    assert whose.nearer(GUEST, "S1", {"S2": GUEST}) == "S1"


def test_a_model_that_cannot_be_fetched_is_tried_again_only_an_hour_later(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim import model_pins

    tries: list[str] = []

    def fail(repo: str) -> None:
        tries.append(repo)
        raise OSError("offline")

    monkeypatch.setattr(model_pins, "ready", lambda _repo: False)
    monkeypatch.setattr(model_pins, "download", fail)
    monkeypatch.setattr(voiceprint, "TRIED", [])
    assert not voiceprint.fetched() and not voiceprint.fetched()
    assert len(tries) == 1
