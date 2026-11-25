"""2026-11-25: the owner's dub of Mark and Joanna Stern came out at -26.7 LUFS, 4.4 dB under its
own original and far under a normal post, so it sounded faint beside every video in the feed."""
from pathlib import Path

import numpy as np
import pytest

from tarjim.dub import audio, loud, mix

MEASURED = """[Parsed_loudnorm_0 @ 0x1]
{
	"input_i" : "-26.70",
	"input_tp" : "-3.10",
	"input_lra" : "14.00",
	"input_thresh" : "-37.20",
	"output_i" : "-14.10",
	"output_tp" : "-1.50",
	"output_lra" : "9.80",
	"output_thresh" : "-24.60",
	"normalization_type" : "dynamic",
	"target_offset" : "0.10"
}
"""


def test_what_ffmpeg_measured_is_read_from_its_report() -> None:
    assert loud.report(MEASURED) == -26.7


def test_silence_measured_as_minus_infinity_is_no_measure() -> None:
    assert loud.report(MEASURED.replace('"-26.70"', '"-inf"')) is None


def test_the_whole_sound_is_raised_by_one_gain_and_only_its_peaks_held(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Not loudnorm's own levelling: it rode the volume and lifted breaths and pauses about 7 dB
    nearer the voice, heard as whispering (2026-11-25)."""
    monkeypatch.setattr(loud, "measured", lambda _sound: -26.7)
    assert loud.level(Path("dub.wav")) == "volume=12.70dB,alimiter=limit=0.841:level=false"


def test_a_nearly_silent_sound_is_not_raised_into_its_own_hiss(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(loud, "measured", lambda _sound: -60.0)
    assert loud.level(Path("dub.wav")).startswith("volume=15.00dB,")


def test_a_sound_that_could_not_be_measured_is_left_as_it_is(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(loud, "measured", lambda _sound: None)
    assert loud.level(Path("dub.wav")) == "anull"


def test_the_dubbed_video_is_written_at_that_level(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[list[str]] = []

    def ffmpeg(args: list[str]) -> bytes:
        asked.append(args)
        Path(args[-1]).write_bytes(b"video")
        return b""

    monkeypatch.setattr(mix, "ffmpeg", ffmpeg)
    monkeypatch.setattr(mix, "level", lambda _sound: "loudnorm=I=-14.0")
    mix.mux(tmp_path / "picture.mp4", tmp_path / "dub.wav", tmp_path / "talk.ar.dub.mp4")
    args = asked[0]
    assert args[args.index("-af") + 1] == "loudnorm=I=-14.0,apad"
    assert args[args.index("-ar") + 1] == str(audio.RATE)


def test_a_voice_that_can_be_asked_again_keeps_a_natural_pace(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """A paid voice, said once, keeps the old cap (cut sooner, it would lose its last words) and
    is never slowed; a voice refit.py shortens is slowed a little when it ends too soon."""
    asked: list[list[str]] = []

    def ffmpeg(args: list[str], _data: bytes | None = None) -> bytes:
        asked.append(args)
        return b""

    monkeypatch.setattr(audio, "ffmpeg", ffmpeg)
    wav = np.zeros(audio.RATE, dtype=np.float32)
    audio.speed_up(wav, 2.0, pace=audio.REFITTED_PACE)
    audio.speed_up(wav, 2.0)
    audio.speed_up(wav, 0.5, pace=audio.REFITTED_PACE)
    audio.speed_up(wav, 0.5)
    assert ["atempo=1.300" in asked[0], "atempo=1.800" in asked[1], "atempo=0.850" in asked[2],
            len(asked)] == [True, True, True, 3]


def test_a_voice_ending_before_its_speaker_stops_is_slowed_toward_their_time() -> None:
    from tarjim.dub.lines import Line

    talking = Line(4.0, 9.0, "voice2", "يشرفني", "", 8.0)
    assert mix.tempo(talking, 3.2) == pytest.approx(0.8)
    assert mix.tempo(talking, 4.5) == 1.0 and mix.tempo(talking, 10.0) == 2.0
