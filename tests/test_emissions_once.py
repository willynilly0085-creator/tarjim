"""The aligner hears a clip's letters once: lines timed again in a stretch of the clip and the
check after timing read them from the whole clip's letters, never from hearing a slice again
(2026-11-08: a slice pushed the whole clip out of the cache, and the check then heard all of it
once more, up to four whole-clip passes on a computer without a graphics card)."""
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import soundfile

from tarjim.asr import align, vad
from tarjim.asr.align import AlignEngine
from tarjim.asr.ctc import FRAME
from tarjim.asr.letters import Letters, piece
from tarjim.listen.clipmap import Clip, clip_map, regions_of
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.timing import Timer

RATE = 16000
HOP = int(RATE * FRAME)
SECONDS = 40.0
LETTERS = "abcdefghijklmnopqrstuvwxyz"
VOCAB = {"<pad>": 0, "<s>": 1, "</s>": 2, "<unk>": 3} | {ch: 4 + k for k, ch in enumerate(LETTERS)}
SAID = {"alpha": 3.0, "bravo": 25.0}


def clip() -> np.ndarray:
    """Each frame's samples hold the letter said in it, so a slice is heard like the whole."""
    labels = np.zeros(int(SECONDS / FRAME), dtype=np.float32)
    for word, at in SAID.items():
        for k, ch in enumerate(word):
            first = int(at / FRAME) + 3 * k
            labels[first:first + 3] = VOCAB[ch]
    return np.repeat(labels, HOP)


class Hearing:
    def __init__(self) -> None:
        self.passes: list[float] = []

    def __call__(self, wav: Any) -> np.ndarray:
        self.passes.append(len(wav) / RATE)
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
def hearing(monkeypatch: pytest.MonkeyPatch) -> Hearing:
    heard = Hearing()
    engine = AlignEngine.__new__(AlignEngine)
    engine.emitter, engine.roman = Emitter(heard), Roman()  # type: ignore[assignment]
    monkeypatch.setattr(align, "shared_aligner", lambda: engine)
    monkeypatch.setattr(vad, "speech_regions", lambda _wav: [(0.0, SECONDS)])
    return heard


def test_a_stretch_and_the_check_read_the_letters_heard_once(hearing: Hearing) -> None:
    lines = [Utterance(2.5, 4.5, "S1", "alpha"), Utterance(24.5, 26.5, "S1", "bravo")]
    timer = Timer(clip(), RATE, "English", [])
    whole = timer.whole(lines)
    again = timer.part([lines[1]])
    assert abs(again[0].start - 25.0) < 0.1 and abs(again[0].end - 25.3) < 0.1
    assert timer.agreement(whole) == 1.0
    assert Timer(timer.wav, RATE, "English", []).agreement(again) == 1.0
    assert hearing.passes == [SECONDS] and timer.passes() == 1


def test_a_stretch_starts_on_a_frame_of_the_whole_clip() -> None:
    sound = clip()
    stretch = piece(sound, RATE, 19.507, 31.5)
    assert stretch.start == pytest.approx(19.5)
    assert len(stretch) == round((31.5 - 19.5) * RATE)
    assert float(stretch[0]) == float(sound[round(19.5 * RATE)])
    heard = Hearing()
    letters = Letters(heard)
    assert np.array_equal(letters(stretch), letters(sound)[975:1575])
    assert heard.passes == [SECONDS]


def test_only_the_last_clip_is_kept() -> None:
    """A weak computer keeps one clip's letters, not one for every sound it was asked about."""
    heard = Hearing()
    letters = Letters(heard)
    first, second = clip(), clip()[: 10 * RATE]
    letters(first)
    letters(second)
    letters(first)
    assert heard.passes == [SECONDS, 10.0, SECONDS]
    assert letters.count(first) == 3 and letters.count(second) == 2  # every pass since it came
    assert letters.count(clip()) == 0


def test_the_passes_are_told_once_a_run_even_when_it_is_timed_twice(
        capsys: pytest.CaptureFixture[str]) -> None:
    """On 2026-11-08 the count was told after every timing, twice when a run timed again."""
    from tarjim.asr.base import Transcript
    from tarjim.listen import settle

    def made(agreement: float, passes: int) -> settle.Timed:
        return settle.Timed(Transcript("Somali", "x"), True, agreement, passes=passes)

    settle.better(made(0.1, 1), lambda: made(0.2, 2), second_opinion=True)
    told = [line for line in capsys.readouterr().out.splitlines() if "clip's letters" in line]
    assert told == ["timing: the aligner heard the clip's letters 2 time(s)"]


def test_one_map_one_detector_run_and_one_pass_for_the_whole_job(
        hearing: Hearing, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The map, both timings, a stretch and the check read the letters heard once, and the voice
    detector runs once for the job: before 2026-11-09 it ran again inside every alignment."""
    runs: list[float] = []

    def detected(wav: Any) -> list[tuple[float, float]]:
        runs.append(len(wav) / RATE)
        return [(0.0, SECONDS)]

    monkeypatch.setattr(vad, "speech_regions", detected)
    audio = tmp_path / "audio.wav"
    sound = clip()
    soundfile.write(audio, sound, RATE, subtype="FLOAT")
    lines = [Utterance(2.5, 4.5, "S1", "alpha"), Utterance(24.5, 26.5, "S1", "bravo")]
    made = clip_map(tmp_path, Clip(audio, sound, RATE), [(u.start, u.end) for u in lines])
    assert regions_of(audio) == [(0.0, SECONDS)]  # the cut reads the same run
    timer = Timer(sound, RATE, "English", [], made)
    whole = timer.whole(lines)
    again = timer.part([lines[1]])
    assert abs(again[0].start - 25.0) < 0.1
    assert timer.agreement(whole) == 1.0
    assert hearing.passes == [SECONDS] and timer.passes() == 1
    assert runs == [SECONDS]
