"""Since 2026-11-09 the voice check hears windows of steady talk and groups them into the clip's
voices: one voice the listener heard under two labels of one request joins, two alike voices it
told apart stay apart, a panel keeps all its speakers and a voice no label told apart gets one of
its own, a short reply keeps its label, voices not clearly apart move nothing, an hour of speech
makes no more than MAX_WINDOWS prints, and the same words always give the same speakers."""
import numpy as np
import pytest
from fake_voices import (
    Turn,
    alike_to,
    by_turns,
    end,
    heard,
    people,
    relabelled,
    sound,
    spoken,
    words_of,
)

from tarjim.listen import cluster, turns, whose


def test_one_voice_under_two_labels_of_one_request_joins(
        monkeypatch: pytest.MonkeyPatch) -> None:
    # the host's turns heard as S1 and S3 by turns, the guest as S2: one person, two colours
    talk = by_turns(18, "AB")
    split = relabelled(talk, {k: "S3" for k in range(0, 18, 4)})
    words = heard(monkeypatch, split, people("AB"))
    after = spoken(whose.checked(words, sound(end(talk))), split)
    host = {name for name, t in zip(after, talk, strict=True) if t.voice == "A"}
    assert len(host) == 1 and host <= {"S1", "S3"}
    assert {name for name, t in zip(after, talk, strict=True) if t.voice == "B"} == {"S2"}


def test_two_alike_voices_heard_by_turns_stay_apart(monkeypatch: pytest.MonkeyPatch) -> None:
    # their windows 0.6 alike on average, as two men can be: under APART_JOIN, so two people
    host = people("A")["A"]
    voices = {"A": host, "B": alike_to(host, 0.83, 7)}
    talk = by_turns(16, "AB")
    words = heard(monkeypatch, talk, voices)
    windows, _ = turns.windows(words, sound(end(talk)))
    v = cluster.voices(windows, [w.label for w in windows])
    across = [k for k, w in enumerate(windows) if w.label == "S2"]
    assert 0.55 < cluster.alike(v, [k for k in range(len(windows)) if k not in across],
                                across) < cluster.APART_JOIN
    assert whose.checked(words, sound(end(talk))) == words


def test_a_panel_of_four_keeps_four_speakers_and_its_swap_is_undone(
        monkeypatch: pytest.MonkeyPatch) -> None:
    talk = by_turns(24, "ABCD")
    swapped = relabelled(talk, {k: {"C": "S4", "D": "S3"}.get(t.voice, t.label)
                                for k, t in enumerate(talk) if k >= 12})
    words = heard(monkeypatch, swapped, people("ABCD"))
    after = whose.checked(words, sound(end(talk)))
    assert spoken(after, swapped) == [t.label for t in talk]
    assert {w.speaker for w in after} == {"S1", "S2", "S3", "S4"}


def test_a_voice_no_label_told_apart_gets_a_speaker_of_its_own(
        monkeypatch: pytest.MonkeyPatch) -> None:
    # a third person heard as the host (S1) for three turns in a row: a speaker of their own
    talk = by_turns(16, "AB") + [Turn(74.0 + 4.6 * k, 4.0, "C", "S1") for k in range(3)]
    talk = [*talk, *by_turns(6, "AB")]
    talk = [t._replace(start=k * 4.6) for k, t in enumerate(talk)]
    words = heard(monkeypatch, talk, people("ABC"))
    after = spoken(whose.checked(words, sound(end(talk))), talk)
    third = after[16:19]
    assert len(set(third)) == 1 and third[0] not in {"S1", "S2"}
    assert after[:16] + after[19:] == [t.label for t in talk[:16] + talk[19:]]


def test_a_short_reply_keeps_its_label(monkeypatch: pytest.MonkeyPatch) -> None:
    talk = by_turns(16, "AB")
    replies = [Turn(t.start + 4.1, 0.4, "B" if t.voice == "A" else "A",
                    "S2" if t.voice == "A" else "S1") for t in talk[2:14:3]]
    words = heard(monkeypatch, [*talk, *replies], people("AB"))
    assert whose.checked(words, sound(end(talk))) == words


def test_voices_not_clearly_apart_move_nothing_and_the_log_says_why(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    # every window's print is noise: no voice is told from another
    talk = relabelled(by_turns(16, "AB"), {3: "S1", 6: "S2"})
    words = heard(monkeypatch, talk, {"A": np.zeros(256), "B": np.zeros(256)})
    assert whose.checked(words, sound(end(talk))) == words
    assert "not clearly apart (silhouette" in capsys.readouterr().out


def test_an_hour_of_speech_makes_no_more_than_the_window_cap() -> None:
    talk = by_turns(800, "AB", seconds=4.0, pause=0.5)
    words = words_of(talk)
    spots = turns.spots(turns.owned(words))
    assert sum(t.seconds for t in talk) >= 3200
    assert len(spots) <= turns.MAX_WINDOWS
    assert turns.hop(3200) > turns.HOP


def test_a_line_is_heard_in_windows_only_where_no_other_speaker_talks_over_it() -> None:
    words = words_of([Turn(0.0, 4.0, "A", "S1"), Turn(3.5, 2.0, "B", "S2"),
                      Turn(8.0, 3.0, "B", "S2"), Turn(12.0, 2.0, "A", "S1"),
                      Turn(12.5, 1.0, "B", "S2")])
    assert [(s.start, s.end) for s in turns.owned(words)] == [(0.0, 3.5), (4.0, 5.5),
                                                              (8.0, 11.0)]


def test_the_same_words_give_the_same_speakers(monkeypatch: pytest.MonkeyPatch) -> None:
    talk = by_turns(20, "AB")
    swapped = relabelled(talk, {k: "S2" if t.voice == "A" else "S1"
                                for k, t in enumerate(talk) if k >= 9})
    words = heard(monkeypatch, swapped, people("AB", 3))
    first = whose.checked(words, sound(end(talk)))
    assert all(whose.checked(words, sound(end(talk))) == first for _ in range(3))
