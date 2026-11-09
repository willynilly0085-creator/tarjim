"""Code moved out of full files changes nothing a clip gets (2026-11-08): the hearing path runs on
a made-up clip, through the real aligner with a stand-in for its ears, a cloud engine that leaves
a line out and is asked again, and the words this computer heard; its words and subtitles match,
byte for byte, what the code gave before the move (tests/data/room_made.json)."""
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import soundfile

from tarjim import config, hearing, media
from tarjim.asr import align, qwen, vad, voiceprint
from tarjim.asr.align import AlignEngine
from tarjim.asr.base import Transcript
from tarjim.asr.ctc import FRAME
from tarjim.asr.letters import Letters
from tarjim.job import Job
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Heard
from tarjim.models import Word
from tarjim.segment import build_cues

GOLDEN = Path(__file__).parent / "data" / "room_made.json"
RATE = 16000
HOP = int(RATE * FRAME)
SECONDS = 40.0
LETTERS = "abcdefghijklmnopqrstuvwxyz"
VOCAB = {"<pad>": 0, "<s>": 1, "</s>": 2, "<unk>": 3} | {ch: 4 + k for k, ch in enumerate(LETTERS)}
SPOKEN = [Utterance(2.0, 4.0, "S1", "alpha bravo"), Utterance(8.0, 10.0, "S2", "charlie"),
          Utterance(14.0, 16.0, "S1", "delta echo"),
          Utterance(22.0, 26.0, "S2", "foxtrot golf hotel"),
          Utterance(30.0, 33.0, "S1", "india & juliet")]
FIRST = [u for u in SPOKEN if u.text != "foxtrot golf hotel"]  # the cloud left this line out


def clip() -> np.ndarray:
    """Each frame's samples hold the letter said in it; a line's words follow one another."""
    labels = np.zeros(int(SECONDS / FRAME), dtype=np.float32)
    for line in SPOKEN:
        frame = int((line.start + 0.2) / FRAME)
        for word in line.text.split():
            for ch in word:  # "&" has no letters: the aligner places it between its neighbours
                labels[frame:frame + 3] = VOCAB.get(ch, 0)
                frame += 3
            frame += 5
    return np.repeat(labels, HOP)


def ears(wav: Any) -> np.ndarray:
    labels = np.asarray(wav, dtype=np.float32)[::HOP].astype(np.int64)
    probs = np.full((len(labels), len(VOCAB)), 0.02 / len(VOCAB))
    probs[np.arange(len(labels)), labels] = 0.98
    return np.log(probs)


class Emitter:
    vocab = VOCAB

    def __init__(self) -> None:
        self.emissions = Letters(ears)


class Roman:
    def romanize_string(self, text: str) -> str:
        return text


def slice_heard(sound: bytes) -> Heard:
    start, end = map(float, sound.decode().split(","))
    lines = [Utterance(u.start - start, u.end - start, u.speaker, u.text) for u in SPOKEN
             if u.start >= start and u.end <= end]
    return Heard("English", lines, [lines])


def local_words() -> list[Word]:
    """The words this computer heard, a little late, with no speaker."""
    return [Word(w.text, w.start + 0.3, w.end + 0.3) for u in SPOKEN
            for w in align.proportional(u)]


def setup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Job:
    import tarjim.memory

    engine = AlignEngine.__new__(AlignEngine)
    engine.emitter, engine.roman = Emitter(), Roman()  # type: ignore[assignment]

    def extract(_video: Path, target: Path) -> Path:
        soundfile.write(target, clip(), RATE, subtype="FLOAT")
        return target

    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(tarjim.memory, "free_for_listening", lambda: None)
    monkeypatch.setattr(media, "extract_audio", extract)
    monkeypatch.setattr(media, "audio_bytes", lambda _v, s, e: f"{s},{e}".encode())
    monkeypatch.setattr(vad, "speech_regions", lambda _wav: [(u.start, u.end) for u in SPOKEN])
    monkeypatch.setattr(voiceprint, "fetched", lambda: False)
    monkeypatch.setattr(align, "shared_aligner", lambda: engine)
    monkeypatch.setattr(qwen, "shared_engine", lambda: pytest.fail("not asked"))
    monkeypatch.setattr(hearing, "qwen_transcript",
                        lambda _a: Transcript("English", "", local_words()))
    monkeypatch.setattr(hearing, "listen_video",
                        lambda _v, _a: Heard("English", FIRST, [FIRST], provider="fakecloud"))
    monkeypatch.setattr(hearing, "cloud_listener", lambda _provider: slice_heard)
    return Job(tmp_path / "clip.mp4", cache_dir=tmp_path / "cache")


def timing(found: Any) -> Any:
    """What a clip gets, less each word's source and score (2026-11-08), which say how it got
    its time and change none of it."""
    if isinstance(found, dict):
        return {k: timing(v) for k, v in found.items() if k not in ("score", "source")}
    return [timing(v) for v in found] if isinstance(found, list) else found


def made(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> str:
    """The words and subtitles of a first run, and the words derived again from the kept
    hearing once the kept transcript is gone."""
    job = setup(monkeypatch, tmp_path)
    first = hearing.transcript_for(job, lambda _stage: None)
    (job.cache / "transcript.json").unlink(missing_ok=True)
    monkeypatch.setattr(hearing, "listen_video", lambda _v, _a: pytest.fail("listened again"))
    again = hearing.transcript_for(job, lambda _stage: None)
    found = {"words": [asdict(w) for w in first.words],
             "cues": [asdict(c) for c in build_cues(first.words, [])],
             "again": [asdict(w) for w in again.words]}
    return json.dumps(timing(found), ensure_ascii=False, indent=1) + "\n"


def test_the_hearing_path_gives_the_same_words_and_subtitles(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    assert made(monkeypatch, tmp_path) == GOLDEN.read_text(encoding="utf-8")


def test_a_mode_setting_is_in_the_derive_key(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """2026-11-08: the key held only the code, the piece length and the gap length, so a clip
    timed by one aligner mode would have been served as the other's."""
    from tarjim.listen import kept

    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    before = kept.derive_key()
    monkeypatch.setenv("TARJIM_ALIGNER_MODE", "tolerant")
    assert "listen.aligner" in kept.MODES and kept.derive_key() != before


def test_the_moved_names_are_still_found_where_they_were() -> None:
    from tarjim.asr import spread
    from tarjim.listen import coverage, heard_align, placed, repair, settle

    assert hearing.listen_and_align is heard_align.listen_and_align
    assert (repair.described, repair.still_left) == (coverage.described, coverage.still_left)
    assert (repair.NOT_REPAIRED, repair.NOT_ASKED) == (coverage.NOT_REPAIRED, coverage.NOT_ASKED)
    assert settle.placed is placed.placed and settle.Placed is placed.Placed
    moved = ("Slot", "proportional", "longest", "runs", "share", "fill_gaps", "GAP_FALLBACK")
    assert all(getattr(align, name) is getattr(spread, name) for name in moved)
