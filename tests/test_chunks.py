from tarjim.listen.chunks import listen_in_chunks, spans
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Heard


def test_short_video_is_one_piece() -> None:
    assert spans(200.0, []) == [(0.0, 200.0)]


def test_long_video_is_cut_in_the_middle_of_a_silence_near_five_minutes() -> None:
    regions = [(0.0, 290.0), (294.0, 600.0), (606.0, 1000.0)]
    pieces = spans(1000.0, regions)
    assert pieces[0] == (0.0, 292.0)
    assert pieces[1] == (292.0, 603.0)
    assert pieces[-1][1] == 1000.0


def test_no_silence_nearby_cuts_at_five_minutes() -> None:
    assert spans(700.0, [(0.0, 700.0)])[0] == (0.0, 300.0)


def test_pieces_are_moved_to_video_time_and_speakers_stay_apart() -> None:
    def listen_span(start: float, _end: float) -> Heard:
        line = [Utterance(2.0, 3.0, "S1", f"from {start:.0f}")]
        return Heard("English", line, [line, line])

    heard = listen_in_chunks(700.0, [(0.0, 700.0)], listen_span)
    assert [(u.start, u.speaker, u.text) for u in heard.utterances] == [
        (2.0, "c0.S1", "from 0"), (302.0, "c1.S1", "from 300"), (602.0, "c2.S1", "from 600")]
    assert len(heard.passes) == 2 and len(heard.passes[0]) == 3
