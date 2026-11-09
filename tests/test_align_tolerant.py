"""The aligner's tolerant mode in timing (listen.aligner, asr/tolerated.py, 2026-11-09): a line
written twice with one copy said keeps one copy, a refrain said twice keeps both, a line never
said is spread over its own time and marked, and the clip's prices are measured once."""
import random
from collections.abc import Iterator
from dataclasses import replace
from typing import Any

import numpy as np
import pytest

from tarjim.asr import align, vad
from tarjim.asr.agree import FOUND
from tarjim.asr.align import AlignEngine
from tarjim.asr.ctc import FRAME
from tarjim.asr.letters import Letters
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.timing import Timer, run_scored
from tarjim.models import SOURCES, Word

RATE = 16000
HOP = int(RATE * FRAME)
SECONDS = 70.0
LETTERS = "abcdefghijklmnopqrstuvwxyz"
VOCAB = {"<pad>": 0, "<s>": 1, "</s>": 2, "<unk>": 3} | {ch: 4 + k for k, ch in enumerate(LETTERS)}
EVERY = 1.5  # seconds from one line to the next
FIRST = 1.0
COPY = 30  # the line that is written twice, or said twice, at its time + LATER
LATER = 3.0
GONE = 34  # ...and the line slots left silent for it (the sound holds no line there)


def made_words() -> list[str]:
    pick = random.Random(7)
    return ["".join(pick.choice("bcdfghjklmnprstvwxz") for _ in range(5)) for _ in range(120)]


WORDS = made_words()


def line(k: int, at: float | None = None) -> Utterance:
    start = FIRST + EVERY * k if at is None else at
    return Utterance(start, start + 0.7, "S1", f"{WORDS[2 * k]} {WORDS[2 * k + 1]}")


def said_at(k: int, at: float) -> dict[float, str]:
    return {at: WORDS[2 * k], at + 0.4: WORDS[2 * k + 1]}


def clip(said: dict[float, str]) -> np.ndarray:
    """Each frame's samples hold the letter said in it (tests/test_emissions_once.py)."""
    labels = np.zeros(int(SECONDS / FRAME), dtype=np.float32)
    for at, word in said.items():
        for k, ch in enumerate(word):
            first = round(at / FRAME) + 3 * k
            labels[first:first + 3] = VOCAB[ch]
    return np.repeat(labels, HOP)


class Hearing:
    def __init__(self) -> None:
        self.passes = 0

    def __call__(self, wav: Any) -> np.ndarray:
        self.passes += 1
        labels = np.asarray(wav, dtype=np.float32)[::HOP].astype(np.int64)
        probs = np.full((len(labels), len(VOCAB)), 0.02 / len(VOCAB))
        probs[np.arange(len(labels)), labels] = 0.98
        return np.log(probs)


class Emitter:
    vocab = VOCAB

    def __init__(self, hearing: Hearing) -> None:
        self.emissions = Letters(hearing)


class Roman:
    def romanize_string(self, text: str) -> str:
        return text


@pytest.fixture
def engine(monkeypatch: pytest.MonkeyPatch) -> Iterator[AlignEngine]:
    built = AlignEngine.__new__(AlignEngine)
    built.emitter, built.roman = Emitter(Hearing()), Roman()  # type: ignore[assignment]
    monkeypatch.setattr(align, "shared_aligner", lambda: built)
    monkeypatch.setattr(vad, "speech_regions", lambda _wav: [(0.0, SECONDS)])
    monkeypatch.setenv("TARJIM_ALIGNER_MODE", "tolerant")
    yield built


def scene(extra: Utterance | None, said_twice: bool) -> tuple[np.ndarray, list[Utterance]]:
    """Lines every EVERY seconds, a few left silent after COPY; the line COPY said again
    LATER seconds on when `said_twice`, and `extra` put in the text."""
    kept = [k for k in range(40) if not COPY < k < GONE]
    said: dict[float, str] = {}
    for k in kept:
        said |= said_at(k, line(k).start)
    if said_twice:
        said |= said_at(COPY, line(COPY).start + LATER)
    lines = [line(k) for k in kept] + ([extra] if extra else [])
    return clip(said), sorted(lines, key=lambda u: u.start)


def copies(words: list[Word]) -> list[float]:
    return [round(w.start, 1) for w in words if w.text == WORDS[2 * COPY]]


def test_a_line_written_twice_and_said_once_keeps_one_copy(engine: AlignEngine) -> None:
    copy = line(COPY, line(COPY).start + LATER)
    wav, lines = scene(copy, said_twice=False)
    words = Timer(wav, RATE, "English", []).whole(lines)
    assert copies(words) == [round(line(COPY).start, 1)]
    assert engine.calibration is not None and engine.calibration.costs is not None
    assert len(words) == 2 * (len(lines) - 1)


def test_the_strict_aligner_squeezes_the_copy_in(
        engine: AlignEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """The contrast: strict, every written word is given a place."""
    monkeypatch.setenv("TARJIM_ALIGNER_MODE", "strict")
    copy = line(COPY, line(COPY).start + LATER)
    wav, lines = scene(copy, said_twice=False)
    words = Timer(wav, RATE, "English", []).whole(lines)
    assert len(copies(words)) == 2 and engine.calibration is None


def test_a_refrain_said_twice_keeps_both(engine: AlignEngine) -> None:
    copy = line(COPY, line(COPY).start + LATER)
    wav, lines = scene(copy, said_twice=True)
    words = Timer(wav, RATE, "English", []).whole(lines)
    assert copies(words) == [round(line(COPY).start, 1), round(line(COPY).start + LATER, 1)]
    assert {w.source for w in words} == {"aligned"}


def test_a_line_never_said_is_spread_over_its_time_and_marked(engine: AlignEngine) -> None:
    invented = Utterance(line(COPY).start + LATER, line(COPY).start + LATER + 1.0, "S1",
                         "quiqq quizz")
    wav, lines = scene(invented, said_twice=False)
    words = Timer(wav, RATE, "English", []).whole(lines)
    made_up = [w for w in words if w.text.startswith("qui")]
    assert [w.source for w in made_up] == ["estimated", "estimated"]
    assert invented.start <= made_up[0].start and made_up[-1].end <= invented.end + 1e-6
    assert [r.kind for r in engine.unplaced] == ["unplaced"]
    assert engine.unplaced[0].start == pytest.approx(invented.start)


def test_every_word_has_a_source_and_every_run_a_score(engine: AlignEngine) -> None:
    wav, lines = scene(line(COPY, line(COPY).start + LATER), said_twice=False)
    words = run_scored(wav, Timer(wav, RATE, "English", []).whole(lines))
    assert words is not None and all(w.source in SOURCES[:4] for w in words)
    assert all(w.score is not None and w.score >= FOUND for w in words)


def test_the_prices_are_measured_once_a_clip(engine: AlignEngine) -> None:
    wav, lines = scene(None, said_twice=False)
    timer = Timer(wav, RATE, "English", [])
    timer.whole(lines)
    timer.part(lines[5:7])
    timer.agreement(timer.whole(lines))
    assert engine.calibrations.made == 1 and timer.passes() == 1
    assert engine.emitter.emissions.total == 1  # type: ignore[attr-defined]


def test_a_loop_of_one_voice_never_takes_another_voice_s_line(engine: AlignEngine) -> None:
    """The bench, 2026-11-09 (en_refrain_twice x loop_all): S2 says a line, S1 says it after,
    and the listener loops S1's line. S2's real line was dropped as a copy of S1's and one of
    S1's copies was timed onto S2's speech. A copy is only ever of its own speaker's words."""
    at = line(COPY).start
    said: dict[float, str] = {}
    for k in (k for k in range(40) if not COPY <= k < GONE):
        said |= said_at(k, line(k).start)
    said |= said_at(COPY, at) | said_at(COPY, at + 1.5)
    other = Utterance(at, at + 0.7, "S2", line(COPY).text)
    mine = [Utterance(at + 1.5 * n, at + 1.5 * n + 0.7, "S1", line(COPY).text) for n in (1, 2)]
    lines = sorted([line(k) for k in range(40) if not COPY <= k < GONE] + [other, *mine],
                   key=lambda u: u.start)
    lines = [replace(u, request="k0.v") for u in lines]  # one request: its labels compare
    words = Timer(clip(said), RATE, "English", []).whole(lines)
    found = [(round(w.start, 1), w.speaker) for w in words if w.text == WORDS[2 * COPY]]
    assert found == [(round(at, 1), "S2"), (round(at + 1.5, 1), "S1")]


def test_a_clip_heard_mostly_by_its_letters_alone_stays_strict(
        engine: AlignEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """The review of 2026-11-09 (en_chant_bed): where the voice detector hears no voice and the
    letters do (a chant, singing, a vocal bed), the star fed on that sound and moved a word of
    a text said exactly. Such a clip (asr/speechmap.ctc_only, 35% of the chant's speech, none
    on any other clip) is read strictly."""
    monkeypatch.setattr(vad, "speech_regions", lambda _wav: [])
    wav, lines = scene(None, said_twice=False)
    Timer(wav, RATE, "English", []).whole(lines)
    assert engine.calibration is not None and engine.calibration.costs is None


def test_a_clip_read_strictly_for_its_chant_spends_no_reading_on_prices(
        engine: AlignEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """2026-11-09: a clip read strictly because its letters alone hear much of its speech
    reads no stretch to measure prices it will not use (the cpu tier)."""
    monkeypatch.setattr(vad, "speech_regions", lambda _wav: [])
    wav, lines = scene(None, said_twice=False)
    calls: list[int] = []
    group = engine.align_group
    monkeypatch.setattr(engine, "align_group", lambda logp, g: calls.append(1) or group(logp, g))
    Timer(wav, RATE, "English", []).whole(lines)
    strict = len(calls)
    monkeypatch.setenv("TARJIM_ALIGNER_MODE", "strict")
    calls.clear()
    Timer(wav, RATE, "English", []).whole(lines)
    assert strict == len(calls)
