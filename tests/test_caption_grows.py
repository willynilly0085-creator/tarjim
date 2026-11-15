"""A video that carries captions of its own keeps the subtitle lifted above them, and those
captions sometimes take a second line for a sentence: the line said then goes above both, and
no other line moves. The rows are the ones measured on 2026-11-15 on a 17-second trailer,
640x640, whose caption stood at 90-96% of the height and took a second line at 84-90% for 1.7 s,
with no key frame inside the line said over it."""
from pathlib import Path

import pytest

from tarjim.job import Job
from tarjim.models import Cue
from tarjim.render import moments, timeline
from tarjim.render.ass import Canvas

OWN = (0.8992, 0.9592)
SECOND = (0.836, 0.9)
TITLE = (0.495, 0.6)  # the film's name in the middle of the picture, up with the second line
TWO_LINES = [TITLE, SECOND, (0.902, 0.958)]
LIFTED = Canvas(640, 640, margin=76, bands=(OWN,))
SAID = [Cue(10.2, 12.18, text="x"), Cue(13.38, 14.92, text="x")]
KEY_FRAMES = {11.97: [OWN], 14.973: TWO_LINES, 17.976: []}
LOOKS = {10.3: [OWN], 12.08: [OWN], 13.48: TWO_LINES, 14.82: TWO_LINES}


def test_both_ends_of_a_line_beside_text_are_looked_at() -> None:
    """Text up for about as long as the line shows in one key frame at most; only the line's
    own two ends can show it twice, a second apart."""
    assert moments.wanted(KEY_FRAMES, SAID[1:], LIFTED) == [13.48, 14.82]


def test_the_line_said_under_a_second_caption_line_goes_above_it() -> None:
    moved = moments.decide(KEY_FRAMES | LOOKS, SAID, LIFTED, None)
    assert [(start, end) for start, end, _margin, _top in moved] == [(13.38, 14.92)]
    _start, _end, margin, top = moved[0]
    assert not top and 640 - margin <= SECOND[0] * 640


def test_a_lifted_video_looks_for_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(timeline, "scan", lambda *_args: dict(KEY_FRAMES))
    monkeypatch.setattr(moments, "looked", lambda _video, times: {t: LOOKS[t] for t in times})
    canvas = moments.moved(Job(tmp_path / "v.mp4", cache_dir=tmp_path), SAID, LIFTED, None)
    assert canvas.margin_v == LIFTED.margin_v  # the video keeps its place
    assert [start for start, *_rest in canvas.moves] == [13.38]


def test_words_on_the_wall_of_a_lifted_video_move_no_line() -> None:
    """2026-10-30, a news clip lifted over its channel's bar: the words on the wall behind the
    speaker came back at the same rows each time the camera did, and lines hopped. They do not
    stand on the bar, so they are not its text with a line more."""
    bar, wall = (0.82, 0.97), (0.7, 0.75)
    lifted = Canvas(1280, 720, margin=150, bands=(bar,))
    seen = {1.0: [wall, bar], 2.5: [wall, bar]}
    said = [Cue(0.5, 3.0, text="x")]
    assert moments.hit([wall], lifted)
    assert moments.decide(seen, said, lifted, None) == ()
    assert moments.decide(seen, said, Canvas(1280, 720), None) != ()  # elsewhere it is passing text


def test_text_shown_from_a_short_line_s_start_to_its_end_counts() -> None:
    """A line under a second long has no two looks a second apart; text at the same rows at
    both its ends is over it for all of its time."""
    note = (0.86, 0.93)
    seen = {2.0: [], 3.1: [note], 3.7: [note], 6.0: []}
    moved = moments.decide(seen, [Cue(3.0, 3.8, text="x")], Canvas(1920, 1080), None)
    assert [(start, end) for start, end, _margin, _top in moved] == [(3.0, 3.8)]
