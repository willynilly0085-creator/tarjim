"""Since 2026-11-08 a line the vote could not link to the base pass's speakers ("S2~p3",
listen/vote.relabel) is never left a speaker of its own: by voice it goes to the base speaker whose
voice is nearest, and where no voice is checked to the base speaker it overlaps most in time, else
the nearer base turn. Left as it was, it got a third colour and a third dub voice."""
from typing import Any

import numpy as np
import pytest

from tarjim import speakers
from tarjim.asr import voiceprint
from tarjim.listen import whose
from tarjim.models import Word

HOST, GUEST = np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0])
RATE = voiceprint.RATE


def said(start: float, speaker: str, seconds: float = 2.0) -> list[Word]:
    half = seconds / 2
    return [Word("one", start, start + half, speaker),
            Word("two", start + half, start + seconds, speaker)]


def sound(seconds: float) -> np.ndarray:
    """Each sample holds its own time, so a stretch tells where it starts."""
    return np.arange(int(seconds * RATE)) / RATE


def voices_at(timeline: dict[float, np.ndarray]) -> Any:
    def print_of(clip: np.ndarray) -> np.ndarray:
        return timeline[round(float(clip[0]), 1)]

    return print_of


def interview(monkeypatch: pytest.MonkeyPatch, lone: np.ndarray) -> list[Word]:
    """Host and guest by turns, and one line only pass 3 heard, in the voice lone."""
    words = [*said(0, "S1"), *said(4, "S2"), *said(8, "S1"), *said(12, "S2"), *said(16, "S1"),
             *said(20, "S2~p3")]
    timeline = {0.0: HOST, 4.0: GUEST, 8.0: HOST, 12.0: GUEST, 16.0: HOST, 20.0: lone}
    monkeypatch.setattr(voiceprint, "print_of", voices_at(timeline))
    monkeypatch.setattr(voiceprint, "fetched", lambda: True)
    return words


def test_an_unlinked_line_in_the_guests_voice_is_the_guests(
        monkeypatch: pytest.MonkeyPatch) -> None:
    # the probe: it stayed "S2~p3", a third speaker, since no other line shared its label
    heard = interview(monkeypatch, GUEST)
    assert {w.speaker for w in whose.by_voice(heard, sound(24))} == {"S1", "S2"}
    assert whose.by_voice(heard, sound(24))[-1].speaker == "S2"


def test_an_unlinked_line_goes_by_voice_not_by_its_pass_number(
        monkeypatch: pytest.MonkeyPatch) -> None:
    # pass 3 numbers its speakers in its own order: its S2 may be the base's S1
    heard = interview(monkeypatch, HOST)
    assert whose.by_voice(heard, sound(24))[-1].speaker == "S1"


def test_without_voice_prints_an_unlinked_line_takes_the_speaker_it_overlaps(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(voiceprint, "fetched", lambda: False)
    heard = [*said(0, "S1", 6), *said(7, "S2", 4), *said(9.5, "S1~p2", 2.5)]
    after = whose.by_voice(heard, sound(14))
    assert [w.speaker for w in after[-2:]] == ["S2", "S2"]


def test_without_voice_prints_an_unlinked_line_off_every_turn_takes_the_nearer(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(voiceprint, "fetched", lambda: False)
    heard = [*said(0, "S1", 3), *said(3.5, "S1~p2"), *said(8, "S2", 3)]
    assert whose.by_voice(heard, sound(12))[2].speaker == "S1"
    # sound not at the voice model's rate is not checked by voice either
    assert whose.by_voice(heard, sound(12), 44100)[2].speaker == "S1"


def test_an_unlinked_line_too_short_to_print_still_finds_a_base_speaker(
        monkeypatch: pytest.MonkeyPatch) -> None:
    heard = interview(monkeypatch, GUEST)
    short = [Word("yes", 18.1, 18.5, "S1~p2")]
    after = whose.by_voice([*heard[:-2], *short], sound(24))
    assert after[-1].speaker == "S1"


def test_a_clip_heard_only_by_unlinked_labels_keeps_their_names() -> None:
    words = [*said(0, "S1~p2"), *said(3, "S2~p2")]
    assert [w.speaker for w in speakers.linked_by_time(words)[::2]] == ["S1", "S2"]


def test_a_distinct_voice_the_base_missed_stays_a_speaker_of_its_own(
        monkeypatch: pytest.MonkeyPatch) -> None:
    # 2026-11-08 review: the base heard only the host, other passes heard the guest ("S2~p2");
    # forcing the guest's voice onto the one base speaker drew the guest in the host's colour
    words = [*said(0, "S1"), *said(4, "S2~p2"), *said(8, "S1"), *said(12, "S2~p2"), *said(16, "S1")]
    timeline = {0.0: HOST, 4.0: GUEST, 8.0: HOST, 12.0: GUEST, 16.0: HOST}
    monkeypatch.setattr(voiceprint, "print_of", voices_at(timeline))
    monkeypatch.setattr(voiceprint, "fetched", lambda: True)
    after = whose.by_voice(words, sound(20))
    assert [w.speaker for w in after[::2]] == ["S1", "S2", "S1", "S2", "S1"]


def test_a_distinct_unlinked_voice_never_takes_a_base_speakers_name(
        monkeypatch: pytest.MonkeyPatch) -> None:
    third = np.array([0.0, 0.0, 1.0])
    heard = interview(monkeypatch, third)
    after = whose.by_voice(heard, sound(24))
    assert after[-1].speaker not in {"S1", "S2", "S2~p3"}
    assert {w.speaker for w in after[:-2]} == {"S1", "S2"}


def test_two_unlinked_labels_in_one_new_voice_are_one_speaker() -> None:
    from tarjim.listen.follow import adopted

    voices = {"S1": HOST, "S1~p2": np.array([0.0, 1.0, 0.0]), "S3~p3": np.array([0.1, 1.0, 0.0])}
    names = adopted(voices, {"S1"})
    assert names["S1~p2"] == names["S3~p3"] not in {"S1", ""}
