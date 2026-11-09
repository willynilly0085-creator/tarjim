"""Who is who across a long clip's pieces (2026-11-09). Every piece is its own request and a
listener numbers its speakers in the order it hears them, so piece two's "S1" may be piece one's
"S2". Each request after the first also hears the end of the piece before it (its lead); the
lines both heard there link the labels, one to one, and the lead's lines are never shown."""
import json
from collections import Counter
from pathlib import Path

import pytest

from tarjim import guards, speakers
from tarjim.listen import links
from tarjim.listen.chunks import joined, listen_in_chunks
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.kept import keep_heard, load_heard
from tarjim.listen.lead import LEAD_SHARE, LINK_LEAD, WIDE_LEAD, lead_of
from tarjim.listen.merge import Heard, Piece
from tarjim.listen.whose import by_voice
from tarjim.models import Word

CUT = 60.0
PERSON = ("A", "B")  # who says each line, by turns


def text(k: int) -> str:
    return " ".join(f"w{k}{letter}" for letter in "abcde")


def clip_lines() -> list[tuple[float, float, str, str]]:
    """Two people by turns over two minutes: (start, end, person, words)."""
    return [(6.0 * k + 0.5, 6.0 * k + 5.0, PERSON[k % 2], text(k)) for k in range(20)]


def heard(low: float, high: float, names: dict[str, str]) -> list[Utterance]:
    """What a request over [low, high] hears, at its own times, naming people its way."""
    return [Utterance(s - low, e - low, names[p], t) for s, e, p, t in clip_lines()
            if low <= (s + e) / 2 < high]


FIRST = {"A": "S1", "B": "S2"}
SWAPPED = {"A": "S2", "B": "S1"}


def two_pieces(lead_s: float = LINK_LEAD) -> list[Piece]:
    """Piece two's request names A "S2" and B "S1"; with a lead it heard [CUT - lead_s, CUT)."""
    own = [heard(0.0, CUT, FIRST)] * 3
    second = [[Utterance(u.start - CUT, u.end - CUT, u.speaker, u.text)
               for u in heard(0.0, 120.0, SWAPPED) if u.start >= CUT]] * 3
    lead = [heard(CUT - lead_s, CUT, SWAPPED)] * 3 if lead_s else []
    return [Piece(0.0, CUT, own), Piece(CUT, 120.0, second, "", lead_s, lead)]


def by_person(lines: list[Utterance]) -> dict[str, set[str]]:
    people = {t: p for _, _, p, t in clip_lines()}
    found: dict[str, set[str]] = {}
    for u in lines:
        found.setdefault(people[u.text], set()).add(u.speaker)
    return found


def test_labels_permuted_between_requests_are_linked_through_the_lead() -> None:
    lines, _ = joined(two_pieces())
    assert by_person(lines) == {"A": {"S1"}, "B": {"S2"}}


def test_the_leads_lines_never_appear_in_the_hearing() -> None:
    lines, passes = joined(two_pieces())
    assert len(lines) == 20 and sorted(u.start for u in lines) == [u[0] for u in clip_lines()]
    assert all(len(run) == 20 for run in passes)


def test_without_a_lead_each_label_keeps_its_raw_name_and_the_guard_counts_it() -> None:
    guards.reset()
    lines, _ = joined(two_pieces(lead_s=0.0))
    assert by_person(lines) == {"A": {"S1", "S2"}, "B": {"S1", "S2"}}  # today's collision
    assert guards.counts()["speaker.unlinked_piece"] == 2


def test_conflicting_evidence_keeps_two_labels_apart() -> None:
    found = Counter({("S1", "S1"): 5, ("S2", "S1"): 4})
    assert links.assigned(found, ["S1", "S2"], ["S1", "S2"], 1) == {"S1": "S1", "S2": "S2"}
    found = Counter({("S2", "S1"): 5, ("S1", "S1"): 4})
    chosen = links.assigned(found, ["S1", "S2"], ["S1", "S2", "S3"], 1)
    assert chosen == {"S2": "S1", "S1": "S4~k1"} and speakers.unlinked(chosen["S1"])


def test_a_label_left_over_in_a_request_linked_otherwise_is_left_to_the_voice_check() -> None:
    # its request's numbering is not the clip's: its own name is no better than a guess
    found = Counter({("S1", "S2"): 6})
    chosen = links.assigned(found, ["S1", "S2", "S3"], ["S1", "S2", "S3"], 3)
    assert chosen == {"S1": "S2", "S2": "S4~k3", "S3": "S3~k3"}
    words = [*said(0.0, "S2"), *said(4.0, "S4~k3"), *said(8.0, "S3~k3")]
    assert [w.speaker for w in by_voice(words, None, rate=1)] == ["S2"] * 2 + ["S4"] * 2 + \
        ["S3"] * 2


def test_the_last_label_left_pairs_with_the_last_name_left() -> None:
    found = Counter({("S3", "S1"): 6, ("S1", "S2"): 4})
    chosen = links.assigned(found, ["S1", "S2", "S3"], ["S1", "S2", "S3"], 2)
    assert chosen == {"S3": "S1", "S1": "S2", "S2": "S3"}


def test_a_lead_over_silence_widens_and_never_passes_its_share() -> None:
    pieces = [(0.0, 75.0), (75.0, 150.0)]
    assert lead_of(pieces, 0, [(0.0, 150.0)], 75.0) == 0.0
    assert lead_of(pieces, 1, [(0.0, 150.0)], 75.0) == LINK_LEAD
    assert lead_of(pieces, 1, [(0.0, 60.0), (80.0, 150.0)], 75.0) == WIDE_LEAD
    assert lead_of(pieces, 1, [], 75.0) == LINK_LEAD  # no voice detector: nothing to judge by
    assert lead_of(pieces, 1, [(0.0, 60.0), (80.0, 150.0)], 50.0) == LEAD_SHARE * 50.0
    assert lead_of([(0.0, 5.0), (5.0, 80.0)], 1, [], 75.0) == 5.0


class Listener:
    """A cloud listener over clip_lines, naming people in a new order in every request."""

    def __init__(self) -> None:
        self.asked: list[tuple[float, float]] = []

    def __call__(self, start: float, end: float) -> Heard:
        self.asked.append((start, end))
        run = heard(start, end, FIRST if len(self.asked) % 2 else SWAPPED)
        return Heard("English", run, [run, list(run), list(run)])


def test_a_fresh_hearing_asks_as_often_and_hears_at_most_its_share_more() -> None:
    listener = Listener()
    fresh = listen_in_chunks(120.0, [(0.0, 120.0)], listener, target=CUT)
    assert len(listener.asked) == 2 and listener.asked[1] == (CUT - LINK_LEAD, 120.0)
    assert sum(b - a for a, b in listener.asked) <= (1 + LEAD_SHARE) * 120.0
    assert by_person(fresh.utterances) == {"A": {"S1"}, "B": {"S2"}}
    assert len(fresh.utterances) == 20


def test_a_line_over_the_cut_is_dropped_when_the_piece_before_heard_it() -> None:
    said = Utterance(58.0, 59.9, "S1", "we will be right back")
    late = Utterance(58.8 - (CUT - LINK_LEAD), 61.6 - (CUT - LINK_LEAD), "S2",
                     "we will be right back")
    novel = Utterance(59.5 - (CUT - LINK_LEAD), 61.5 - (CUT - LINK_LEAD), "S1",
                      "something nobody said before")

    def listen(start: float, _end: float) -> Heard:
        run = [late, novel] if start else [said]
        return Heard("English", run, [run])

    fresh = listen_in_chunks(120.0, [], listen, target=CUT)
    starts = {u.text: u.start for u in fresh.utterances}
    assert starts == {"we will be right back": 58.0, "something nobody said before": CUT}


def test_a_kept_hearing_and_passes_in_another_order_give_the_same_names(
        tmp_path: Path) -> None:
    pieces = two_pieces()
    lines, _ = joined(pieces)
    keep_heard(tmp_path, Heard("English", lines, [], provider="gemini", pieces=pieces))
    loaded = load_heard(tmp_path)
    assert loaded is not None and loaded.pieces == pieces
    assert [u.speaker for u in loaded.utterances] == [u.speaker for u in lines]
    turned = [Piece(p.start, p.end, p.passes[::-1], p.language, p.lead_s, p.lead[::-1])
              for p in pieces]
    assert [u.speaker for u in joined(turned)[0]] == [u.speaker for u in lines]


def test_a_hearing_kept_before_leads_loads_with_none(tmp_path: Path) -> None:
    rows = [{"start": p.start, "end": p.end, "passes": [[vars(u) for u in run] for run in p.passes]}
            for p in two_pieces(lead_s=0.0)]
    data = {"language": "English", "utterances": [], "passes": [], "pieces": rows}
    (tmp_path / "heard.json").write_text(json.dumps(data), encoding="utf-8")
    loaded = load_heard(tmp_path)
    assert loaded is not None and [(p.lead_s, p.lead) for p in loaded.pieces] == [(0.0, [])] * 2
    assert loaded.pieces == two_pieces(lead_s=0.0)


def said(start: float, speaker: str) -> list[Word]:
    return [Word("one", start, start + 1.0, speaker), Word("two", start + 1.0, start + 2.0,
                                                           speaker)]


def test_lines_heard_again_take_the_turn_they_overlap_and_no_label_is_left_open() -> None:
    again = Word("again", 4.6, 5.4, "S1~x45")  # a request's own "S1", said over S2's turn
    words = [*said(0.0, "S1"), *said(4.0, "S2"), again, *said(8.0, ""), *said(12.0, "S3~k1")]
    out = by_voice(sorted(words, key=lambda w: w.start), None, rate=1)
    assert {w.text: w.speaker for w in out}["again"] == "S2"
    assert all(w.speaker and not speakers.unlinked(w.speaker) for w in out)
    assert out[-1].speaker == "S3"  # a piece's unlinked speaker takes the name links.py chose


def test_the_voice_check_sees_a_pieces_unlinked_label_as_unlinked() -> None:
    assert speakers.unlinked("S1~k3") and speakers.unlinked("S2~p3~k1")
    assert speakers.unlinked("S1~x120") and not speakers.unlinked("S1")


def test_lines_heard_again_carry_their_requests_mark(tmp_path: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim import hearing, media
    from tarjim.listen.asked import Asked
    from tarjim.listen.check import relistener

    line = Utterance(0.5, 1.5, "S1", "a reply")
    monkeypatch.setattr(media, "audio_bytes", lambda _video, start, end: f"{start}")
    monkeypatch.setattr(hearing, "cloud_listener", lambda _provider: lambda sound: Heard(
        "English", [line], [[line]]))
    again = relistener("gemini", tmp_path / "clip.mp4", Asked(tmp_path / "asked.json", []))
    assert again is not None
    found = again(40.0, 42.0)
    assert [u.speaker for u in found] == [f"S1~x{round(10 * found[0].start - 5)}"]
    assert speakers.unlinked(found[0].speaker)


def test_a_line_heard_again_far_from_any_turn_keeps_its_requests_name() -> None:
    # the turns either side are both one person's; nothing in time says it is theirs
    words = [*said(0.0, "S1"), *said(4.0, "S2"), *said(10.0, "S2~x95"), *said(16.0, "S1")]
    out = by_voice(words, None, rate=1)
    assert [w.speaker for w in out][4:6] == ["S2", "S2"]
    touching = [*said(0.0, "S1"), *said(2.1, "S2~x20"), *said(10.0, "S2")]
    assert [w.speaker for w in by_voice(touching, None, rate=1)][2:4] == ["S1", "S1"]
