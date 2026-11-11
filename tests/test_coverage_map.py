"""The coverage check reads the clip's speech map (2026-11-09), so a stretch is judged the same
with or without the listener on this computer: a stretch of the map's own speech is speech, and
stays open when nothing filled it whoever ran; a stretch only the local words call speech is given
up, still listed and never asked about, when the sound holds no speech there; and a stretch no
listener heard words in is listed, never dropped from the job."""
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from tarjim.asr.base import Transcript
from tarjim.asr.ctc import FRAME
from tarjim.asr.speechmap import HARD, SOFT, SPEECH, SpeechMap
from tarjim.job import Job
from tarjim.listen import check, settle
from tarjim.listen.bysound import UNCHECKED
from tarjim.listen.coverage import NOT_REPAIRED, Gap, Hearing, gaps, speech_of
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Heard
from tarjim.listen.novel import Again
from tarjim.listen.repair import Mended, mend
from tarjim.models import Word

LINE = Utterance(0.0, 10.0, "S1", "one two three four five")
TALK = [(0.0, 10.0), (20.0, 25.0)]  # the speech the map holds
FAR = [Word("far", 50.0, 50.3)]  # the local listener ran, and heard nothing near the gap
MURMUR = [Word(f"m{k}", 30.0 + 0.5 * k, 30.4 + 0.5 * k) for k in range(8)]  # 30-34 s, local only


def sound_map(speech: list[tuple[float, float]], source: str = "vad+ctc",
              pad: float = 0.0) -> SpeechMap:
    """The detector's speech `speech`, padded by `pad` in the map's frames as asr/vad pads it."""
    frames = int(60.0 / FRAME)
    vad = np.zeros(frames, dtype=bool)
    for start, end in speech:
        vad[round((start - pad) / FRAME):round((end + pad) / FRAME)] = True
    tier = np.where(vad, SPEECH, HARD).astype(np.int8)
    return SpeechMap(vad, tier, 0.1, source, tuple(speech))


class Asked:
    """A cloud listener asked about a stretch that hears nothing there."""

    def __init__(self) -> None:
        self.calls: list[tuple[float, float]] = []

    def __call__(self, start: float, end: float) -> list[Utterance]:
        self.calls.append((start, end))
        return []


def hearing(local: list[Word], speech_map: SpeechMap | None = None) -> Hearing:
    regions = [] if speech_map is None else list(speech_map.regions)
    return Hearing([LINE], local, regions, map=speech_map)


def test_without_local_words_a_gap_of_the_maps_speech_stays_open() -> None:
    mended = mend(hearing([], sound_map(TALK)), Asked(), "x")
    [gap] = mended.left
    assert (gap.start, gap.end, gap.given_up, gap.sound) == (20.0, 25.0, False, "")
    assert not mended.whole


def test_with_the_local_listener_on_it_stays_open_too(capsys: pytest.CaptureFixture[str]) -> None:
    """Before 2026-11-09 the local listener hearing nothing here closed it after one answer;
    with it off the same stretch stayed open and was asked again."""
    mended = mend(hearing(FAR, sound_map(TALK)), Asked(), "x")
    assert [g.given_up for g in mended.left] == [False] and not mended.whole
    assert f"-> {NOT_REPAIRED}" in capsys.readouterr().out


def test_local_words_where_the_sound_holds_no_speech_are_given_up_and_listed(
        capsys: pytest.CaptureFixture[str]) -> None:
    asked = Asked()
    mended = mend(hearing(MURMUR, sound_map(TALK)), asked, "x")
    [murmur] = [g for g in mended.left if g.start >= 29.0]
    assert murmur.given_up and murmur.words == MURMUR and mended.added == []
    assert all(start < 29.0 for start, _end in asked.calls)  # never asked about
    log = capsys.readouterr().out
    assert "the sound holds no speech (0% of it not silent)" in log
    assert "no speech here by the sound; not asked again" in log


def test_local_words_are_judged_only_when_the_letters_were_heard(
        capsys: pytest.CaptureFixture[str]) -> None:
    """A map with no letters is the detector's alone, which takes a chant for silence."""
    [_talk, murmur] = gaps(hearing(MURMUR, sound_map(TALK, source="none")))
    assert murmur.sound == UNCHECKED and not murmur.unspoken
    mended = mend(hearing(MURMUR, sound_map(TALK, source="none")), Asked(), "x")
    assert [u.text.split()[0] for u in mended.added] == ["m0"]
    assert UNCHECKED in capsys.readouterr().out


def test_quiet_speech_the_letters_partly_heard_is_filled_from_the_local_words() -> None:
    """Of a stretch only the local words call speech the map's own speech is never part, so it is
    judged by how much of it the letters call silent (review of 2026-11-09): judged by the share
    the map called speech, every such stretch was given up, quiet speech too."""
    speech_map = sound_map(TALK)
    speech_map.tier[round(30.0 / FRAME):round(34.0 / FRAME)] = SOFT
    [murmur] = [g for g in gaps(hearing(MURMUR, speech_map)) if g.start >= 29.0]
    assert not murmur.unspoken and murmur.sound.startswith("the sound holds speech (100%")
    mended = mend(hearing(MURMUR, speech_map), Asked(), "x")
    assert [u.text.split()[0] for u in mended.added] == ["m0"]
    assert all(not g.given_up for g in mended.left)


SHORT = [(0.0, 10.0), (20.0, 21.9)]  # 1.9 s found by the detector, 2.1 s with the map's padding
NEAR = [Word(f"n{k}", 20.0 + 0.3 * k, 20.3 + 0.3 * k) for k in range(7)]  # 20.0-22.1 s


def test_a_gap_is_the_same_with_or_without_the_local_listener() -> None:
    """On 2026-11-09 a 1.9 s stretch of the detector's speech was a gap only with the local words,
    which stretched it to 2.0 s: the map's own speech, padded as the aligner reads it, decides."""
    off = gaps(hearing([], sound_map(SHORT, pad=0.1)))
    on = gaps(hearing(NEAR, sound_map(SHORT, pad=0.1)))
    assert [(g.start, round(g.speech, 2), g.sound) for g in off] == [(20.0, 1.9, "")]
    assert [(g.start, g.sound) for g in on] == [(20.0, "")]


def test_local_words_a_little_past_short_speech_do_not_make_it_a_gap() -> None:
    """Local words timed past the map's speech by no more than a line's times are rough do not
    lengthen it into a gap the stretch is not with the local listener off."""
    short = [(0.0, 10.0), (20.0, 21.6)]  # 1.8 s padded; the local words end 0.3 s past it
    assert gaps(hearing([], sound_map(short, pad=0.1))) == []
    assert gaps(hearing(NEAR, sound_map(short, pad=0.1))) == []


def test_local_words_beside_the_maps_speech_are_its_speech() -> None:
    beside = [Word(f"b{k}", 24.0 + 0.5 * k, 24.4 + 0.5 * k) for k in range(6)]  # 24-27 s
    [gap] = gaps(hearing(beside, sound_map(TALK)))
    assert (gap.start, gap.end, gap.sound) == (20.0, 26.9, "")


def test_a_stretch_no_listener_heard_words_in_is_listed_never_dropped() -> None:
    mended = mend(Hearing([LINE], FAR, [(0.0, 10.0), (20.0, 25.0)]), Asked(), "x")
    [gap] = mended.left
    assert gap.given_up and (gap.start, gap.end) == (20.0, 25.0) and mended.whole


def test_the_map_is_the_speech_when_given() -> None:
    assert speech_of(Hearing([], [], [(1.0, 2.0)], map=sound_map(TALK))) == TALK
    assert speech_of(Hearing([], [], [(1.0, 2.0)])) == [(1.0, 2.0)]


def test_a_gap_with_no_map_says_nothing_of_the_sound() -> None:
    [gap] = gaps(hearing(MURMUR))
    assert gap.sound == "" and gap == Gap(gap.start, gap.end, gap.speech, MURMUR)


class Seen(Exception):
    pass


def test_every_hearing_the_settle_step_builds_reads_the_map(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    told: list[Hearing] = []
    speech_map = sound_map(TALK)

    def repaired(_job: Job, _heard: Heard, hearing_: Hearing, _asked: Any) -> check.Repair:
        told.append(hearing_)
        return check.Repair("English", Again(None, "x", []), Mended([], [], []))

    def timed(_repair: Any, hearing_: Hearing, _sound: Any) -> settle.Timed:
        told.append(hearing_)
        return settle.Timed(Transcript("English", ""), True, 0.1)

    monkeypatch.setattr(check, "repaired", repaired)
    monkeypatch.setattr(check, "keep", lambda *_a: None)
    monkeypatch.setattr(settle, "timed", timed)
    quiet = np.zeros(8000 * 60, dtype=np.float32)
    sound = settle.Sound(quiet, 8000, TALK, [], speech_map=speech_map)
    settle.settled(Job(tmp_path / "v.mp4"), Heard("English", [], []), sound, FAR)
    assert len(told) == 3 and all(h.map is speech_map for h in told)


def test_with_no_voice_detector_the_log_names_what_is_missing(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    from tarjim.asr import vad

    def broken(_wav: Any) -> list[tuple[float, float]]:
        raise ImportError("no onnxruntime")

    monkeypatch.setattr(vad, "speech_regions", broken)
    assert check.regions_in(np.zeros(800, dtype=np.float32)) == []
    log = capsys.readouterr().out
    assert "no voice detector (ImportError)" in log and "letters" in log
