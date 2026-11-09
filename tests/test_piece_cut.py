"""A long clip's piece heard from a little before its cut (2026-11-09): the times its listener
writes are the request's, so an mm:ss misread is read back there; a line said over the cut keeps
the words the piece before did not hold, whichever side of the cut most of it was said; and only
the clip's own names link a piece's speakers."""
from collections import Counter
from collections.abc import Callable

import pytest

from tarjim.listen import links
from tarjim.listen.chunks import listen_in_chunks
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Heard, Piece

TAUGHT = "india juliet kilo lima"
MISREAD = "mike november oscar papa"


class Misreader:
    """Piece two's request writes the line it heard at 1:03 as 103."""

    def __init__(self) -> None:
        self.asked: list[tuple[float, float]] = []

    def __call__(self, start: float, end: float) -> Heard:
        self.asked.append((start, end))
        if not start:
            run = [Utterance(1.0, 4.0, "S1", "alpha bravo charlie delta")]
        else:
            run = [Utterance(30.0, 34.0, "S1", TAUGHT), Utterance(103.0, 106.0, "S1", MISREAD)]
        return Heard("English", run, [run, list(run), list(run)])


@pytest.mark.parametrize(("regions", "lead_s"), [
    ([(0.5, 74.5), (75.5, 150.0)], 7.0),  # speech before the cut: the usual lead
    ([(0.5, 60.0), (75.5, 150.0)], 12.0),  # little speech there: the wide one
])
def test_a_misread_in_a_later_piece_is_read_back_at_its_requests_time(
        regions: list[tuple[float, float]], lead_s: float) -> None:
    listener = Misreader()
    fresh = listen_in_chunks(150.0, regions, listener, target=75.0)
    origin = listener.asked[1][0]
    assert fresh.pieces[1].start - origin == pytest.approx(lead_s)
    line = next(u for u in fresh.utterances if u.text == MISREAD)
    assert (line.start, line.end, line.prior) == pytest.approx((origin + 63.0, origin + 66.0,
                                                                0.5))


Listen = Callable[[float, float], Heard]
WORDS = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]


def sentence(said: tuple[float, float]) -> Listen:
    """A listener that hears what its request's sound holds of one sentence said over `said`,
    with no voice detector's regions, so the clip is cut at 75 s on time, inside the sentence."""
    step = (said[1] - said[0]) / len(WORDS)

    def listen(start: float, end: float) -> Heard:
        inside = [(said[0] + k * step, w) for k, w in enumerate(WORDS)
                  if start <= said[0] + k * step < end]
        run = [Utterance(inside[0][0] - start, inside[-1][0] + step - start, "S1",
                         " ".join(w for _, w in inside))]
        if start:
            run.append(Utterance(100.0 - start, 104.0 - start, "S1", "later words after the cut"))
        return Heard("English", run, [run, list(run), list(run)])

    return listen



def said_words(fresh: Heard) -> list[str]:
    return [w for u in fresh.utterances if u.text != "later words after the cut"
            for w in u.text.split()]


@pytest.mark.parametrize("said", [(72.5, 76.5), (73.0, 77.0)])
def test_a_sentence_over_the_cut_is_shown_once_and_whole(said: tuple[float, float]) -> None:
    # most of it before the cut, or half: the piece before holds its first words either way
    fresh = listen_in_chunks(150.0, [], sentence(said), target=75.0)
    assert said_words(fresh) == WORDS
    rest = fresh.utterances[1]
    held = len(fresh.utterances[0].text.split())
    assert rest.start == pytest.approx(said[0] + held * (said[1] - said[0]) / len(WORDS))
    assert rest.piece == (75.0 - 7.0, 150.0)  # its wall reaches back over the lead


def test_a_line_the_piece_before_holds_inside_a_longer_one_is_dropped() -> None:
    before = Utterance(58.0, 61.0, "S1", "we will be right back after this")

    def listen(start: float, _end: float) -> Heard:
        run = [Utterance(58.5 - start, 60.5 - start, "S2", "we will be right back")] if start \
            else [before]
        return Heard("English", run, [run])

    fresh = listen_in_chunks(120.0, [], listen, target=60.0)
    assert [u.text for u in fresh.utterances] == [before.text]


def test_only_the_clips_own_names_link_a_pieces_speakers() -> None:
    # piece one kept a line only another pass heard ("S2~p3"); piece two's lead hears it as S2
    v0 = [Utterance(10.0, 14.0, "S1", "hello and welcome to the show today"),
          Utterance(70.0, 74.0, "S2~p3", "thank you so much for having me here")]
    lead = [Utterance(2.0, 6.0, "S2", "thank you so much for having me here")]
    own = [Utterance(5.0, 9.0, "S1", "so tell us about your new book please"),
           Utterance(10.0, 16.0, "S2", "well it started as a small idea years ago")]
    pieces = [Piece(0.0, 75.0, [v0]), Piece(75.0, 150.0, [own], "", 7.0, [lead])]
    found = links.evidence(links.at(v0, 0.0), pieces[1], own)
    assert found == Counter()
    out = links.named(pieces, [v0, own])
    assert [u.speaker for u in out[1]] == ["S1", "S2"]


def test_a_pieces_own_unlinked_speaker_still_links_the_next_piece() -> None:
    # "S1~k2" is one person of piece two's: the piece after it that hears them is them too
    assert links.linkable("S1~k2") and links.linkable("S2")
    assert not links.linkable("S2~p3") and not links.linkable("S2~p3~k1")
    assert not links.linkable("S1~x415")
