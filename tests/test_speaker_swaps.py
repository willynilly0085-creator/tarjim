"""Since 2026-11-08 a line is judged against the speakers' voices without itself in them, again
until no line moves, so a swap of labels from some point on is undone; voices too alike to be two
people move nothing; a line with no speaker takes the nearer turn, never the main voice by
accident; and a short line goes where its label's long lines went, else keeps its own label."""
from typing import Any

import numpy as np
import pytest

from tarjim.asr import voiceprint
from tarjim.listen import whose
from tarjim.models import Word

RATE = voiceprint.RATE
SIZE = 32  # numbers in a test print; the model's 256 behave the same


def unit(vector: np.ndarray) -> np.ndarray:
    found: np.ndarray = vector / np.linalg.norm(vector)
    return found


def sound(seconds: float) -> np.ndarray:
    """Each sample holds its own time, so a stretch tells where it starts."""
    return np.arange(int(seconds * RATE)) / RATE


def voices_at(timeline: dict[float, np.ndarray]) -> Any:
    def print_of(clip: np.ndarray) -> np.ndarray:
        return timeline[round(float(clip[0]), 1)]

    return print_of


def said(start: float, speaker: str, seconds: float = 2.0) -> list[Word]:
    half = seconds / 2
    return [Word("one", start, start + half, speaker),
            Word("two", start + half, start + seconds, speaker)]


def noisy_voices(seed: int) -> tuple[np.ndarray, np.ndarray, np.random.Generator]:
    """Two people whose voices are a little alike, as two men or two women are."""
    rng = np.random.default_rng(seed)
    host = unit(rng.normal(size=SIZE))
    guest = unit(0.45 * host + unit(rng.normal(size=SIZE)))
    return host, guest, rng


def interview(monkeypatch: pytest.MonkeyPatch, seed: int, swapped_from: int) -> list[Word]:
    """Sixteen turns, host and guest by turns with pauses between, each print the voice with the
    noise of one line, and the listener's labels swapped from turn swapped_from on."""
    host, guest, rng = noisy_voices(seed)
    words: list[Word] = []
    timeline: dict[float, np.ndarray] = {}
    for turn in range(16):
        start, is_host = turn * 3.5, turn % 2 == 0
        voice = host if is_host else guest
        timeline[start] = unit(voice + 0.9 * unit(rng.normal(size=SIZE)))
        label = "S1" if is_host == (turn < swapped_from) else "S2"
        words += said(start, label)
    monkeypatch.setattr(voiceprint, "print_of", voices_at(timeline))
    return words


def truth(words: list[Word]) -> list[str]:
    return ["S1" if k % 2 == 0 else "S2" for k in range(len(words) // 2)]


def test_labels_swapped_from_some_point_on_are_put_back(monkeypatch: pytest.MonkeyPatch) -> None:
    # the old check, with each line inside its own average, put back none of these twelve
    put_back = 0
    for seed in range(1, 13):
        heard = interview(monkeypatch, seed, swapped_from=10)
        got = [w.speaker for w in whose.checked(heard, sound(60))[::2]]
        # put right, or, where the two voices are too alike to tell, left exactly as heard
        assert got in (truth(heard), [w.speaker for w in heard[::2]])
        put_back += got == truth(heard)
    assert put_back >= 11


def test_labels_already_right_are_never_moved(monkeypatch: pytest.MonkeyPatch) -> None:
    for seed in range(1, 13):
        heard = interview(monkeypatch, seed, swapped_from=99)
        assert whose.checked(heard, sound(60)) == heard


def test_a_clip_with_one_voice_is_never_split_into_two_colours(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    # one person, the listener called one of their lines S2; the prints differ only by the
    # noise of each line, and they would pull one more line over to S2 if they were trusted
    turn = [unit(np.array([np.cos(a), np.sin(a), 0.0])) for a in np.radians([18, -18, -16, 18])]
    heard = [*said(0, "S1"), *said(4, "S1"), *said(8, "S1"), *said(12, "S2")]
    monkeypatch.setattr(voiceprint, "print_of", voices_at(dict(zip([0.0, 4.0, 8.0, 12.0], turn,
                                                                    strict=True))))
    assert whose.checked(heard, sound(16)) == heard
    assert "too alike" in capsys.readouterr().out


def test_a_short_line_without_a_speaker_takes_the_turn_it_touches(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(voiceprint, "fetched", lambda: False)
    host, guest = said(0, "S1"), said(2.6, "S2")
    reply = [Word("yeah", 4.8, 5.2, "")]  # a fill heard on this computer, 0.2 s after the guest
    after = whose.by_voice([*host, *guest, *reply], sound(6))
    assert after[-1].speaker == "S2"


def test_a_line_without_a_speaker_far_from_every_turn_takes_the_nearer_one(
        monkeypatch: pytest.MonkeyPatch) -> None:
    # S1 talks most and has the main colour; left without a speaker, the fill 0.6 s after the
    # guest would be drawn in it, though the guest is the nearer voice
    monkeypatch.setattr(voiceprint, "fetched", lambda: False)
    lone = [Word("hm", 9.6, 10.0, "")]
    heard = [*said(0, "S1", 6), *said(7, "S2"), lone[0], *said(11.5, "S1", 6)]
    assert whose.by_voice(heard, sound(18))[4].speaker == "S2"


def test_a_line_without_a_speaker_inside_one_persons_talk_is_theirs(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(voiceprint, "fetched", lambda: False)
    lone = Word("so", 4.0, 4.4, "")  # a second from S2 on each side, S1 nowhere near
    heard = [*said(1, "S2"), lone, *said(5.4, "S2"), *said(9, "S1", 6)]
    assert whose.by_voice(heard, sound(16))[2].speaker == "S2"


def test_a_line_without_a_speaker_follows_the_turn_after_its_voice_is_put_right(
        monkeypatch: pytest.MonkeyPatch) -> None:
    heard = interview(monkeypatch, 1, swapped_from=9)
    fill = [Word("right", heard[-1].end + 0.1, heard[-1].end + 0.5, "")]
    monkeypatch.setattr(voiceprint, "fetched", lambda: True)
    after = whose.by_voice([*heard, *fill], sound(60))
    assert after[-1].speaker == after[-2].speaker == "S2"


def test_a_short_reply_keeps_its_own_label_and_is_not_printed(
        monkeypatch: pytest.MonkeyPatch) -> None:
    # "Right" said by the host straight after the guest: too short to know a voice by, and
    # the listener knew whose it was, so neither its print nor the guest's turn takes it
    heard = interview(monkeypatch, 2, swapped_from=99)
    reply = [Word("right", heard[-1].end + 0.1, heard[-1].end + 0.5, "S1")]
    after = whose.by_voice([*heard, *reply], sound(60))
    assert after[-1].speaker == "S1"


def test_a_short_line_in_a_swapped_stretch_is_put_right_with_it(
        monkeypatch: pytest.MonkeyPatch) -> None:
    # the guest's "right" 0.1 s after the host's turn 12, labelled S1 like every guest line from
    # turn 10 on: the guest lines on both sides of it go back to S2, so it goes with them; taking
    # the host's touching turn would give the guest's word the host's colour
    heard = interview(monkeypatch, 1, swapped_from=10)
    reply = Word("right", 44.1, 44.4, "S1")
    after = whose.checked([*heard[:26], reply, *heard[26:]], sound(60))
    assert [w.speaker for w in after[:26:2]] == truth(heard)[:13]
    assert after[26].speaker == "S2"


def test_a_short_line_follows_its_label_only_where_both_sides_moved() -> None:
    words = [*said(0, "S1"), *said(3, "S2"), Word("ok", 5.1, 5.4, "S1"), *said(7, "S1")]
    heard = {(0, 2): "S1", (2, 4): "S2", (5, 7): "S1"}
    assert whose.followed(words, heard, {**heard, (5, 7): "S2"}) == {}
    assert whose.followed(words, heard, {**heard, (0, 2): "S2", (5, 7): "S2"}) == {(4, 5): "S2"}


def test_a_line_without_a_speaker_takes_a_turn_even_where_no_voice_is_checked(
        monkeypatch: pytest.MonkeyPatch) -> None:
    # sound not at the voice model's rate is not checked by voice, but its fills still need a turn
    monkeypatch.setattr(voiceprint, "fetched", lambda: True)
    heard = [*said(0, "S1", 6), *said(7, "S2"), Word("yeah", 9.1, 9.4, "")]
    assert whose.by_voice(heard, sound(10), 44100)[-1].speaker == "S2"
