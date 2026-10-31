"""Long sound is heard in pieces of about 75 seconds, each cut in a pause (listen/chunks.py)."""
from itertools import pairwise

import pytest

from tarjim.listen import chunks
from tarjim.listen.chunks import chunk_seconds, is_long, listen_in_chunks, spans
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Heard


def test_short_video_is_one_piece() -> None:
    assert spans(80.0, []) == [(0.0, 80.0)]
    assert spans(200.0, [], target=300.0) == [(0.0, 200.0)]


def test_long_video_is_cut_in_the_middle_of_a_silence_near_the_target() -> None:
    regions = [(0.0, 290.0), (294.0, 600.0), (606.0, 1000.0)]
    pieces = spans(1000.0, regions, target=300.0)
    assert pieces[0] == (0.0, 292.0)
    assert pieces[1] == (292.0, 603.0)
    assert pieces[-1][1] == 1000.0


def test_no_silence_nearby_cuts_at_the_target() -> None:
    assert spans(700.0, [(0.0, 700.0)], target=300.0)[0] == (0.0, 300.0)


def test_a_four_minute_clip_is_heard_in_pieces_of_about_75_seconds_cut_at_pauses() -> None:
    regions = [(float(s), s + 3.6) for s in range(0, 250, 4)]  # a breath every 4 seconds
    regions[17] = (68.0, 70.0)  # a longer pause at 70-72 s, near the first target
    pieces = spans(250.0, regions)
    assert len(pieces) == 4 and pieces[0] == (0.0, 71.0)
    assert all(60.0 <= end - start <= 90.0 for start, end in pieces[:-1])
    pauses = [(a[1], b[0]) for a, b in pairwise(regions)]
    assert all(any(low < cut < high for low, high in pauses) for _, cut in pieces[:-1])


def test_a_short_tail_joins_the_piece_before_it() -> None:
    assert spans(160.0, [])[-1] == (75.0, 160.0)


def test_the_size_is_a_setting_and_zero_hears_the_clip_in_one_request(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TARJIM_LISTEN_CHUNK_SECONDS", "0")
    assert chunk_seconds() == 0.0 and not is_long(3600.0)
    assert spans(3600.0, []) == [(0.0, 3600.0)]
    monkeypatch.setenv("TARJIM_LISTEN_CHUNK_SECONDS", "120")
    assert spans(300.0, [])[0] == (0.0, 120.0)
    monkeypatch.setenv("TARJIM_LISTEN_CHUNK_SECONDS", "soon")
    assert chunk_seconds() == chunks.CHUNK_SECONDS


def test_pieces_are_moved_to_video_time_and_keep_the_listener_speakers() -> None:
    def listen_span(start: float, _end: float) -> Heard:
        line = [Utterance(2.0, 3.0, "S1", f"from {start:.0f}")]
        return Heard("English", line, [line, line, line])

    heard = listen_in_chunks(700.0, [(0.0, 700.0)], listen_span, target=300.0)
    assert [(u.start, u.speaker, u.text) for u in heard.utterances] == [
        (2.0, "S1", "from 0"), (302.0, "S1", "from 300"), (602.0, "S1", "from 600")]
    assert len(heard.passes) == 3 and len(heard.passes[0]) == 3
