"""What the picture and the sound really are, not what a file's first numbers say: a phone clip
stored on its side, sound that starts after the picture, a dub shorter than the picture, and a
picture or a sound that phones and browsers do not play."""
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np
import pytest

from tarjim import media
from tarjim.dub import audio, mix
from tarjim.render import burn
from tarjim.render.ass import Canvas, render_ass
from tarjim.render.mark import Mark

real_tools = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
                                reason="needs ffmpeg and ffprobe")
PICTURE = ["-f", "lavfi", "-i", "testsrc=size=64x36:rate=10:duration=3"]
BEEP = ["-f", "lavfi", "-i", "sine=frequency=1000:duration=1"]


def make(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def told(path: Path, streams: str, entry: str) -> str:
    done = subprocess.run(["ffprobe", "-v", "error", "-select_streams", streams, "-show_entries",
                           entry, "-of", "csv=p=0", str(path)], capture_output=True, text=True,
                          check=True)
    return done.stdout.strip()


def first_loud(samples: np.ndarray, rate: int) -> float:
    return float(np.flatnonzero(np.abs(samples) > 0.1)[0]) / rate


@pytest.mark.parametrize("stream", [{"side_data_list": [{"rotation": 90}]},
                                    {"side_data_list": [{"rotation": -270}]},
                                    {"tags": {"rotate": "270"}}])
def test_a_quarter_turn_from_either_place_the_file_keeps_it_counts(
        stream: dict[str, object]) -> None:
    assert media.on_its_side(stream)


@pytest.mark.parametrize("stream", [{}, {"side_data_list": [{"rotation": 180}]},
                                    {"tags": {"rotate": "0"}}, {"tags": {"rotate": "x"}}])
def test_no_turn_or_a_half_turn_keeps_the_picture_as_it_is(stream: dict[str, object]) -> None:
    assert not media.on_its_side(stream)


@real_tools
def test_a_phone_clip_stored_on_its_side_is_measured_standing(tmp_path: Path) -> None:
    flat, turned = tmp_path / "flat.mp4", tmp_path / "turned.mp4"
    make(*PICTURE, "-c:v", "mpeg4", str(flat))
    make("-display_rotation", "90", "-i", str(flat), "-c", "copy", str(turned))
    assert (media.probe(flat).width, media.probe(flat).height) == (64, 36)
    assert (media.probe(turned).width, media.probe(turned).height) == (36, 64)


def late_sound(folder: Path) -> Path:
    """The picture from 0 s, the sound (a beep) from 1 s."""
    clip = folder / "late.mp4"
    make(*PICTURE, "-itsoffset", "1", *BEEP, "-map", "0:v", "-map", "1:a", "-c:v", "mpeg4",
         "-c:a", "aac", str(clip))
    return clip


@real_tools
def test_sound_that_starts_after_the_picture_keeps_its_place(tmp_path: Path) -> None:
    clip = late_sound(tmp_path)
    wav = media.extract_audio(clip, tmp_path / "sound.wav")
    with wave.open(str(wav), "rb") as sound:
        pcm = np.frombuffer(sound.readframes(sound.getnframes()), np.int16) / 32768.0
    assert first_loud(pcm, media.SAMPLE_RATE) == pytest.approx(1.0, abs=0.05)
    assert first_loud(audio.decode(clip, channels=2)[:, 0], audio.RATE) == pytest.approx(
        1.0, abs=0.05)
    snippet = audio.decode(media.audio_bytes(clip, 0.5, 2.5))
    assert first_loud(snippet, audio.RATE) == pytest.approx(0.5, abs=0.1)


@real_tools
def test_a_dub_shorter_than_the_picture_keeps_the_whole_picture(tmp_path: Path) -> None:
    picture = tmp_path / "picture.mp4"
    make(*PICTURE, "-c:v", "mpeg4", str(picture))
    sound = audio.write_wav(tmp_path / "dub.wav", np.zeros(int(1.5 * audio.RATE), np.float32))
    dubbed = mix.mux(picture, sound, tmp_path / "clip.dub.mp4")
    assert float(told(dubbed, "v:0", "format=duration")) == pytest.approx(3.0, abs=0.15)
    assert float(told(dubbed, "a:0", "stream=duration")) == pytest.approx(3.0, abs=0.15)


@real_tools
@pytest.mark.parametrize("kind", ["yuv420p10le", "yuv422p"])
def test_a_burn_of_a_ten_bit_or_422_source_plays_on_phones(tmp_path: Path, kind: str) -> None:
    clip = tmp_path / "deep.mkv"
    make(*PICTURE, "-pix_fmt", kind, "-c:v", "ffv1", str(clip))
    out = burn.burn(clip, render_ass([], Canvas(64, 36)), tmp_path / "out.mp4")
    assert told(out, "v:0", "stream=pix_fmt") == "yuv420p"


@pytest.mark.parametrize("mark", [None, Mark(4, 4, 8)])
def test_every_burn_ends_in_the_picture_format_every_player_plays(mark: Mark | None) -> None:
    """x264 and the graphics cards would otherwise keep a 10-bit or 4:2:2 source as it is."""
    drawn = burn.drawing(mark)
    assert drawn[-1].endswith(",format=yuv420p") and drawn[-2] in ("-vf", "-filter_complex")


@real_tools
def test_a_sound_mp4_players_do_not_play_is_made_aac(tmp_path: Path) -> None:
    clip = tmp_path / "pcm.mkv"
    make(*PICTURE, *BEEP, "-c:v", "mpeg4", "-c:a", "pcm_s16le", str(clip))
    out = burn.burn(clip, render_ass([], Canvas(64, 36)), tmp_path / "out.mp4")
    assert told(out, "a", "stream=codec_name") == "aac"


def test_only_sound_every_mp4_player_plays_is_copied() -> None:
    for kept in (["aac"], ["mp3"], ["ac3", "eac3"], []):
        assert burn.sound(kept) == ["-c:a", "copy"]
    for redone in (["vorbis"], ["opus"], ["pcm_s16le"], ["aac", "flac"]):
        assert burn.sound(redone)[:2] == ["-c:a", "aac"]
