"""A stretch heard again is one request of its own, and the listener names its speakers in it
afresh: "S1" there is whoever speaks first in that stretch, not the clip's S1 (2026-11-09). On the
bench's Arabic dialogue three lines of the second speaker, each asked alone, came back as "S1"
and were shown in the first speaker's colour; the voice check could not see it, as each ran on
into the first speaker's next line under one label. Such a line now carries its request's own
name ("S1~r426"), like a pass the vote could not link: the voice check gives it the speaker whose
voice it is, and where it cannot, it keeps the request's name, as before."""
from pathlib import Path

import pytest

from tarjim import hearing, media
from tarjim.listen.asked import Asked
from tarjim.listen.check import relistener
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Heard
from tarjim.models import Word
from tarjim.speakers import asked_again, linked_by_time, unlinked


def test_a_line_heard_again_carries_its_request_s_own_name() -> None:
    assert asked_again("S1", 42.6) == "S1~r426"
    assert unlinked(asked_again("S1", 42.6))


def test_a_line_with_no_speaker_keeps_none() -> None:
    assert asked_again("", 42.6) == ""


def test_the_lines_heard_again_carry_the_request_s_names(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(media, "audio_bytes", lambda *_a: b"sound")
    answer = [Utterance(0.5, 2.0, "S1", "one two"), Utterance(2.2, 3.0, "S2", "three")]
    monkeypatch.setattr(hearing, "cloud_listener",
                        lambda _provider: lambda _sound: Heard("en", answer, [answer]))
    again = relistener("gemini", tmp_path / "v.mp4", Asked.load(tmp_path))
    assert again is not None
    first, second = again(43.0, 46.0)
    tag = first.speaker.removeprefix("S1")
    assert unlinked(first.speaker) and second.speaker == f"S2{tag}"


def test_with_no_voice_to_go_by_the_line_keeps_its_request_s_name() -> None:
    words = [Word("a", 0.0, 1.0, "S1"), Word("b", 1.2, 2.0, "S2"),
             Word("c", 2.05, 3.0, "S1~r21"), Word("d", 3.1, 4.0, "S1")]
    assert [w.speaker for w in linked_by_time(words)] == ["S1", "S2", "S1", "S1"]


def test_a_pass_the_vote_could_not_link_still_takes_the_nearer_turn() -> None:
    words = [Word("a", 0.0, 1.0, "S1"), Word("b", 1.2, 2.0, "S2"),
             Word("c", 2.05, 3.0, "S1~p2"), Word("d", 3.1, 4.0, "S1")]
    assert [w.speaker for w in linked_by_time(words)] == ["S1", "S2", "S2", "S1"]
