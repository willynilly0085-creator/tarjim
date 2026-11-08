"""The clip's speech map is made once per job, the voice detector run once per sound file, and
kept as speech.json with the key the transcript is derived with (2026-11-09)."""
import os
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import soundfile

from tarjim.asr import vad
from tarjim.asr.speechmap import HARD, SOFT
from tarjim.listen import clipmap, kept
from tarjim.listen.clipmap import Clip, clip_map, regions_of
from tests.test_emissions_once import RATE, SECONDS, clip, hearing  # noqa: F401

TALK = [(2.0, 8.0), (20.0, 30.0)]


@pytest.fixture
def runs(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    made: list[int] = []

    def detected(wav: Any) -> list[tuple[float, float]]:
        made.append(len(wav))
        return TALK

    monkeypatch.setattr(vad, "speech_regions", detected)
    return made


def written(folder: Path) -> Clip:
    audio = folder / "audio.wav"
    sound = clip()
    soundfile.write(audio, sound, RATE, subtype="FLOAT")
    return Clip(audio, sound, RATE)


def test_the_detector_runs_once_per_sound_file(tmp_path: Path, runs: list[int]) -> None:
    sound = written(tmp_path)
    assert regions_of(sound.audio) == regions_of(sound.audio, sound.wav) == TALK
    assert len(runs) == 1
    later = os.stat(sound.audio).st_mtime_ns + 10**9
    os.utime(sound.audio, ns=(later, later))  # a new file in the same place
    regions_of(sound.audio)
    assert len(runs) == 2


def test_the_map_is_kept_and_read_back(
        tmp_path: Path, hearing: Any, runs: list[int]) -> None:  # noqa: F811
    """`hearing` first: its own detector stand-in is replaced by `runs`."""
    sound = written(tmp_path)
    first = clip_map(tmp_path, sound, [])
    clipmap.DETECTED.clear()  # the next run of the job: a new sound file
    again = clip_map(tmp_path, sound, [(10.0, 15.0)])
    assert len(runs) == 1 and (tmp_path / kept.SPEECH).exists()
    assert np.array_equal(again.vad, first.vad)
    assert (first.tier[550:700] == HARD).all() and (again.tier[550:700] == SOFT).all()


def test_a_map_kept_by_other_code_is_made_again_and_listen_again_clears_it(
        tmp_path: Path, hearing: Any, runs: list[int],  # noqa: F811
        monkeypatch: pytest.MonkeyPatch) -> None:
    sound = written(tmp_path)
    clip_map(tmp_path, sound, [])
    clipmap.DETECTED.clear()
    monkeypatch.setattr(clipmap, "derive_key", lambda: "other code")
    clip_map(tmp_path, sound, [])
    assert len(runs) == 2
    kept.forget(tmp_path)
    assert not (tmp_path / kept.SPEECH).exists()


def test_a_stand_in_aligner_still_gets_a_map(
        tmp_path: Path, runs: list[int], monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim.asr import align

    monkeypatch.setattr(align, "shared_aligner", object)
    made = clip_map(tmp_path, written(tmp_path), [])
    assert made.source == "none" and made.frames == int(SECONDS / 0.02)
    assert made.speech() == TALK
