"""Each guard fires at its own site, in a fixture taken from the test that covers that layer
(tarjim/guards.py, 2026-11-08)."""
import json
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
import pytest

from tarjim import guards
from tarjim.asr.base import Transcript
from tarjim.listen.coverage import Hearing
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word

U = Utterance


def count(name: str) -> int:
    return guards.counts()[name]


@pytest.fixture(autouse=True)
def fresh(monkeypatch: pytest.MonkeyPatch) -> None:
    guards.reset()
    for name, value in (("COVERAGE_GAP_SECONDS", "2"), ("LISTEN_CHUNK_SECONDS", "75"),
                        ("ALIGNER_MODE", "strict")):
        monkeypatch.setenv(f"TARJIM_{name}", value)  # never the person's own settings


def heard_at(text: str, start: float, step: float = 0.4) -> list[Word]:
    return [Word(w, start + k * step, start + k * step + 0.3) for k, w in enumerate(text.split())]


def test_a_drifted_line_moved_and_words_retimed_are_counted() -> None:
    from tarjim.asr.anchor import anchor
    from tarjim.asr.fuse import fuse

    said = "So I think the level of human intervention was vast"
    anchor([U(227.0, 231.0, "S1", said)], heard_at(said, 236.0), 250.0)
    assert count("anchor.moved") == 1
    lines = [U(15.0, 17.0, "S4", "Once a month."), U(17.0, 18.0, "S1", "Nice."),
             U(18.0, 21.5, "S5", "Oh my gosh.")]
    aligned = [Word("Once", 16.68, 16.84, "S4"), Word("a", 16.84, 16.86, "S4"),
               Word("month.", 16.9, 17.16, "S4"), Word("Nice.", 18.92, 19.0, "S1"),
               Word("Oh", 19.0, 19.08, "S5"), Word("my", 19.12, 19.22, "S5"),
               Word("gosh.", 19.26, 19.88, "S5")]
    fuse(aligned, lines, [Word("Nice.", 17.92, 18.24), Word("Oh", 18.96, 19.04)])
    assert count("fuse.retimed") == 1


class Emitter:
    vocab: ClassVar[dict[str, int]] = {"<pad>": 0, "<s>": 1, "</s>": 2, "<unk>": 3, "a": 4}

    def emissions(self, _wav: Any) -> np.ndarray:
        return np.log(np.full((2000, 5), 0.2))


def test_replies_said_over_a_turn_are_counted_once_per_alignment(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim.asr import vad
    from tarjim.asr.align import AlignEngine

    monkeypatch.setattr(vad, "speech_regions", lambda _wav: [(0.0, 40.0)])
    engine = AlignEngine.__new__(AlignEngine)
    engine.emitter = Emitter()  # type: ignore[assignment]
    engine.roman = type("Roman", (), {"romanize_string": lambda _self, text: text})()
    lines = [U(0.0, 9.0, "S1", "♪ ♪ ♪ ♪ ♪ ♪"), U(3.0, 4.0, "S2", "♪"), U(5.0, 6.0, "S2", "♪")]
    engine.align(np.zeros(16), lines, "English")
    assert count("align.said_over") == 2
    assert count("align.evened") == 3  # text with no letters is spread evenly


def test_lines_far_apart_and_lines_past_their_piece_are_counted() -> None:
    from tarjim.listen.chunks import shift
    from tarjim.listen.timing import apart

    apart([U(0.0, 1.0, "S1", "a"), U(60.0, 61.0, "S1", "b")])
    apart([U(0.0, 1.0, "S1", "a"), U(2.0, 3.0, "S1", "b")])
    assert count("timing.apart") == 1
    shift([U(1.0, 2.0, "S1", "in"), U(80.0, 81.0, "S1", "past"), U(82.0, 83.0, "S1", "in")],
          (0.0, 75.0))
    assert count("shift.clamped") == 1 and count("shift.hallucinated") == 1


def test_speech_known_only_from_the_local_words_is_counted() -> None:
    from tarjim.listen.coverage import speech_of

    speech_of(Hearing([], heard_at("one two three four", 20.0), [(0.0, 10.0)]))
    speech_of(Hearing([], heard_at("one two", 2.0), [(0.0, 10.0)]))  # inside the speech found
    speech_of(Hearing([], heard_at("a b c d e f", 9.0), [(0.0, 10.0), (30.0, 31.0)]))
    assert count("coverage.local_only") == 2


def test_lines_heard_again_that_are_not_new_are_counted() -> None:
    from tarjim.listen.novel import Again, WordMender
    from tarjim.listen.repair import Mender

    lines = [U(10.0, 14.0, "S1", "we went to the market on sunday")]
    mender = Mender(Hearing(lines, [], []), None, "")
    mender.novel(U(11.0, 13.0, "S1", "something else"), lines)
    mender.novel(U(15.0, 16.0, "S1", "the market on sunday"), lines)
    assert (count("repair.overlaps"), count("repair.repeats")) == (1, 1)
    words = heard_at("we went to the market on sunday", 10.0, 0.5)
    again = WordMender(Hearing(lines, [], []), Again(None, "", []), words)
    again.novel(U(14.0, 15.0, "S1", "went to the market"), lines)
    again.novel(U(10.5, 13.0, "S1", "brand new words here"), [])
    again.novel(U(14.0, 14.4, "S1", "sunday"), [])
    assert [count(f"novel.{n}") for n in ("said_before", "timed_over", "echoes")] == [1, 1, 1]


class Timer:
    def part(self, lines: list[Utterance]) -> list[Word]:
        from tarjim.asr.align import proportional

        return [w for u in lines for w in proportional(u)]


def test_a_pile_by_a_gap_and_the_words_check_fills_are_counted() -> None:
    from tarjim.asr.piles import spread
    from tarjim.listen.novel import Again
    from tarjim.listen.wordcover import recheck

    before = [Word(f"w{i}", 0.4 * i, 0.4 * i + 0.3, "S1") for i in range(10)]
    pile = [Word(f"p{i}", 12.0, 12.0, "S1") for i in range(6)]
    lines = [U(0.0, 12.0, "S1", " ".join(w.text for w in [*before, *pile]))]
    local = heard_at("one two three four five six seven", 5.0, 0.8)
    hearing = Hearing(lines, local, [(0.0, 12.5)])
    recheck(hearing, [*before, *pile], Timer(), Again(None, "", []))  # type: ignore[arg-type]
    assert (count("wordcover.unpiled"), count("wordcover.realigned")) == (1, 1)
    spread(pile, (0.0, 1.0), [])
    assert count("piles.spread") == 1
    gap_at = heard_at("seven words said in a gap here", 20.0)
    recheck(Hearing(lines[:0], gap_at, [(19.0, 23.0)]), [], Timer(),  # type: ignore[arg-type]
            Again(None, "", []))
    assert count("wordcover.fills") == 1


def test_the_lines_check_fills_are_counted(tmp_path: Path) -> None:
    from tarjim.job import Job
    from tarjim.listen.check import repaired
    from tarjim.listen.merge import Heard

    job = Job(tmp_path / "v.mp4", cache_dir=tmp_path)
    local = heard_at("seven words said in a gap here", 20.0)
    repaired(job, Heard("English", [], [], provider=""), Hearing([], local, [(19.0, 23.0)]),
             None)  # type: ignore[arg-type]
    assert count("repair.fills") == 1


def test_a_kept_transcript_made_again_is_counted(tmp_path: Path) -> None:
    from tarjim.listen import kept
    from tarjim.listen.merge import Heard, Piece

    squeezed = [Word(f"w{k}", 65.6 + k * 0.01, 65.605 + k * 0.01) for k in range(40)]
    Transcript("English", "x", squeezed).save(tmp_path / kept.TRANSCRIPT)
    assert kept.reusable(tmp_path) is None and count("kept.implausible") == 1
    Transcript("English", "x", heard_at("a b c", 0.0)).save(tmp_path / kept.TRANSCRIPT)
    piece = Piece(0.0, 5.0, [[U(0.0, 1.0, "S1", "a b c")]])
    kept.keep_heard(tmp_path, Heard("English", [], [], pieces=[piece]))
    assert kept.reusable(tmp_path) is None and count("kept.rederived") == 1
    assert kept.load_heard(tmp_path) is not None and count("kept.revoted") == 1
    assert json.loads((tmp_path / kept.HEARD).read_text(encoding="utf-8"))["pieces"]
