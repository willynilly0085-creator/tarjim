"""Speech no timed word reaches is found after alignment, for any engine: a made-up cloud engine
here writes one long line stretched over a sentence it left out, or a line whose words the aligner
piles onto one instant. The aligner is made up too: it puts each word where it was said."""
import json
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import soundfile

from tarjim import hearing, media
from tarjim.asr import align, qwen, vad
from tarjim.asr.base import Transcript
from tarjim.job import Job
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Heard
from tarjim.models import Word
from tarjim.scripts import split_words

LENGTH, RATE, SCALE = 250.0, 8000, 1000.0  # each sample holds its own time / SCALE
SPOKEN = [Utterance(6.0 * k, 6.0 * k + 5.0, "S1", " ".join(f"w{k}x{i}" for i in range(10)))
          for k in range(40)]
LOCAL = [w for u in SPOKEN for w in align.proportional(u)]
TRUE = {w.text: w for w in LOCAL}
REGIONS = [(u.start, u.end) for u in SPOKEN]
PILED = {f"w{k}x{i}" for k in (10, 11) for i in range(10)}
PILE_AT = 72.0


def joined(first: int, last: int, skip: int = -1) -> Utterance:
    text = " ".join(SPOKEN[k].text for k in range(first, last + 1) if k != skip)
    return Utterance(SPOKEN[first].start, SPOKEN[last].end, "S1", text)


def without(first: int, last: int, line: Utterance) -> list[Utterance]:
    return sorted([*(u for k, u in enumerate(SPOKEN) if not first <= k <= last), line],
                  key=lambda u: u.start)


STRETCHED = without(10, 14, joined(10, 14, skip=12))  # 60-89 s, leaves out 72-77 s
WHOLE_LINE = without(10, 12, joined(10, 12))  # 60-77 s, every word there


class Aligner:
    """Words where they were said; the words of PILED land on one instant when `piles` says so."""

    def __init__(self, piles: str = "") -> None:
        self.piles = piles  # "": never, "first": in the first alignment, "always"

    def align(self, wav: Any, utterances: list[Utterance], _language: str) -> list[Word]:
        offset = float(wav[0]) * SCALE
        return [self.word(t, u, offset) for u in utterances for t in split_words(u.text)]

    def word(self, text: str, line: Utterance, offset: float) -> Word:
        pile = self.piles == "always" or (self.piles == "first" and "w12x0" in line.text)
        if pile and text in PILED:
            return Word(text, PILE_AT - 0.01 - offset, PILE_AT - offset, "S1")
        return Word(text, TRUE[text].start - offset, TRUE[text].end - offset, "S1")


class Engine:
    def __init__(self, first: list[Utterance], again_fails: bool = False) -> None:
        self.first, self.again_fails, self.asked = first, again_fails, 0

    def listen_video(self, _video: Path, _audio: Path) -> Heard:
        return Heard("English", self.first, [self.first], provider="fakecloud")

    def cloud_listener(self, _provider: str) -> Any:
        return self.hear_slice

    def hear_slice(self, sound: bytes) -> Heard:
        self.asked += 1
        if self.again_fails:
            raise RuntimeError("fakecloud 500: busy")
        start, end = map(float, sound.decode().split(","))
        lines = [Utterance(u.start - start, u.end - start, u.speaker, u.text) for u in SPOKEN
                 if u.start >= start and u.end <= end]
        return Heard("English", lines, [lines])


def run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, engine: Engine,
        aligner: Aligner) -> tuple[Transcript, Job]:
    import tarjim.memory

    def extract(_video: Path, target: Path) -> Path:
        ramp = (np.arange(int(LENGTH * RATE)) / RATE / SCALE).astype(np.float32)
        soundfile.write(target, ramp, RATE, subtype="FLOAT")
        return target

    monkeypatch.setattr(tarjim.memory, "free_for_listening", lambda: None)
    monkeypatch.setattr(media, "extract_audio", extract)
    monkeypatch.setattr(media, "audio_bytes", lambda _v, s, e: f"{s},{e}".encode())
    monkeypatch.setattr(vad, "speech_regions", lambda _wav: REGIONS)
    monkeypatch.setattr(hearing, "qwen_transcript", lambda _a: Transcript("English", "", LOCAL))
    monkeypatch.setattr(hearing, "listen_video", engine.listen_video)
    monkeypatch.setattr(hearing, "cloud_listener", engine.cloud_listener)
    monkeypatch.setattr(align, "shared_aligner", lambda: aligner)
    monkeypatch.setattr(qwen, "shared_engine", lambda: pytest.fail("not asked"))
    job = Job(tmp_path / "clip.mp4", cache_dir=tmp_path / "cache")
    return hearing.transcript_for(job, lambda _stage: None), job


def texts(transcript: Transcript) -> list[str]:
    return sorted(w.text for w in transcript.words)


def on_time(transcript: Transcript) -> bool:
    return all(abs(w.start - TRUE[w.text].start) < 0.01 for w in transcript.words)


def test_a_sentence_left_out_inside_a_stretched_line_is_heard_again(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    engine = Engine(STRETCHED)
    transcript, job = run(monkeypatch, tmp_path, engine, Aligner())
    log = capsys.readouterr().out
    assert "coverage: gap" not in log  # the line check is fooled by the stretched line
    assert "coverage: words gap 72.0-77.0 s" in log
    assert "re-listened with fakecloud: 1 lines" in log and engine.asked == 1
    assert texts(transcript) == sorted(TRUE) and on_time(transcript)
    starts = [w.start for w in transcript.words]
    assert starts == sorted(starts)
    kept = json.loads((job.cache / "heard.json").read_text(encoding="utf-8"))
    assert [u["text"] for u in kept["added"]] == [SPOKEN[12].text]


def test_when_hearing_again_fails_the_local_words_fill_it(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    engine = Engine(STRETCHED, again_fails=True)
    transcript, job = run(monkeypatch, tmp_path, engine, Aligner())
    log = capsys.readouterr().out
    assert "coverage: words gap 72.0-77.0 s" in log
    assert "filled from local words: 10 words" in log
    assert texts(transcript) == sorted(TRUE) and on_time(transcript)
    assert (job.cache / "heard.json").exists() and (job.cache / "transcript.json").exists()


def test_piled_words_are_aligned_again_in_their_own_stretch(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    engine = Engine(WHOLE_LINE)
    transcript, _job = run(monkeypatch, tmp_path, engine, Aligner(piles="first"))
    log = capsys.readouterr().out
    assert "coverage: words gap 60.0-71.0 s" in log
    assert "timing collapsed: re-timed 20 words into 60.0-72.0 s" in log
    assert engine.asked == 0 and "re-listened" not in log
    assert texts(transcript) == sorted(TRUE) and on_time(transcript)


def test_piled_words_the_aligner_piles_again_share_the_speech(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    engine = Engine(WHOLE_LINE)
    transcript, _job = run(monkeypatch, tmp_path, engine, Aligner(piles="always"))
    log = capsys.readouterr().out
    assert "re-timed 20 words" in log and engine.asked == 0
    assert texts(transcript) == sorted(TRUE)  # nothing dropped, nothing twice
    spread = [w for w in transcript.words if w.text in PILED]
    assert spread[0].start >= 60.0 and spread[-1].end <= 71.01
    assert all(b.start - a.end < 1.1 for a, b in pairwise(spread))
    assert log.count("coverage: words") == 1  # no stretch is left without words


def test_a_clip_with_every_word_in_place_is_left_alone(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    engine = Engine(list(SPOKEN))
    transcript, job = run(monkeypatch, tmp_path, engine, Aligner())
    assert "coverage:" not in capsys.readouterr().out and engine.asked == 0
    assert [w.text for w in transcript.words] == [w.text for w in LOCAL] and on_time(transcript)
    kept = json.loads((job.cache / "heard.json").read_text(encoding="utf-8"))
    assert kept["added"] == []
