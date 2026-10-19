"""A file handed to tarjim is opened as itself and nothing else: a playlist or manifest named like
a video must not make ffmpeg read the files it names, here or on a network share."""
import contextlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tarjim import media, pipeline
from tarjim.job import Job
from tarjim.render import mark
from tarjim.render.ass import Canvas, render_ass
from tarjim.server.guard import safe_name
from tarjim.server.jobs import classify

FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")
real_tools = pytest.mark.skipif(not FFMPEG, reason="needs ffmpeg and ffprobe")
SHARE = "tarjim-nohost.invalid"
DEVICES = ["CON", "PRN", "AUX", "NUL", "COM1", "COM9", "LPT1", "LPT9", "COM0", "COM¹", "LPT³"]


def private_clip(folder: Path) -> Path:
    clip = folder / "Videos" / "private.mp4"
    clip.parent.mkdir()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "testsrc=size=96x54:rate=10", "-t", "1", "-c:v", "mpeg4", "-movflags",
                    "+frag_keyframe+empty_moov+default_base_moof", str(clip)], check=True)
    return clip


def dash(segment: str) -> str:
    return ('<?xml version="1.0"?><MPD xmlns="urn:mpeg:dash:schema:mpd:2011" type="static" '
            'mediaPresentationDuration="PT1S" profiles="urn:mpeg:dash:profile:isoff-on-demand:'
            '2011"><Period><AdaptationSet mimeType="video/mp4"><Representation id="v" '
            f'bandwidth="1"><BaseURL>{segment}</BaseURL></Representation></AdaptationSet>'
            '</Period></MPD>')


def hls(segment: str) -> str:
    return f"#EXTM3U\n#EXT-X-TARGETDURATION:1\n#EXTINF:1,\n{segment}\n#EXT-X-ENDLIST\n"


def upload(folder: Path, text: str, name: str = "clip.mp4") -> Path:
    path = folder / "uploads" / name
    path.parent.mkdir(exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@real_tools
@pytest.mark.parametrize("manifest", [dash, hls])
def test_a_manifest_named_like_a_video_never_reads_the_file_it_names(
        tmp_path: Path, manifest: Any) -> None:
    fake = upload(tmp_path, manifest(private_clip(tmp_path).as_posix()))
    assert not media.probe(fake).has_picture
    with pytest.raises(RuntimeError, match="not a video or sound file"):
        media.check_readable(fake)
    with pytest.raises(RuntimeError):
        media.extract_audio(fake, tmp_path / "heard.wav")
    assert media.audio_bytes(fake, 0, 1) == b""


@real_tools
def test_a_job_on_a_manifest_stops_before_anything_is_heard(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = upload(tmp_path, dash(private_clip(tmp_path).as_posix()))
    heard: list[Path] = []
    monkeypatch.setattr(pipeline, "transcript_for", lambda job, _r: heard.append(job.video))
    with pytest.raises(RuntimeError, match="not a video or sound file") as stopped:
        pipeline.run(Job(fake, out_dir=tmp_path / "out"))
    assert heard == [] and classify(stopped.value) == "media"


@real_tools
@pytest.mark.parametrize("name", ["clip.mp4", "clip.m3u8"])
@pytest.mark.parametrize("text", [dash(f"//{SHARE}/share/x.mp4"), hls(f"\\\\{SHARE}\\share\\x.ts"),
                                  hls(f"//{SHARE}/share/x.ts"), dash(f"file:////{SHARE}/s/x.mp4")])
def test_a_manifest_naming_a_network_share_is_refused_before_ffmpeg_opens_it(
        tmp_path: Path, text: str, name: str) -> None:
    fake = upload(tmp_path, text, name)
    with pytest.raises(RuntimeError, match="not a video or sound file"):
        media.check_readable(fake)
    seen = subprocess.run(["ffprobe", "-v", "debug", *media.source(fake)], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", check=False)
    assert seen.returncode != 0 and SHARE not in seen.stderr
    detected = name.endswith(".m3u8") or text.startswith("<?xml")
    assert "Format not on whitelist" in seen.stderr or not detected


@real_tools
@pytest.mark.parametrize("kind", [".mp4", ".mkv", ".webm", ".mp3", ".wav", ".m4a", ".ogg"])
def test_ordinary_videos_and_sounds_still_open(tmp_path: Path, kind: str) -> None:
    sound = ["-f", "lavfi", "-i", "sine=frequency=440", "-t", "1"]
    picture = [] if kind in (".mp3", ".wav", ".m4a", ".ogg") else [
        "-f", "lavfi", "-i", "testsrc=size=96x54:rate=10", "-t", "1"]
    clip = tmp_path / f"clip{kind}"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *picture, *sound, str(clip)], check=True)
    media.check_readable(clip)
    assert media.probe(clip).duration > 0.5
    assert media.probe(clip).has_picture == bool(picture)
    assert media.extract_audio(clip, tmp_path / "heard.wav").stat().st_size > 1000
    assert len(media.audio_bytes(clip, 0, 1)) > 100


def inputs_of(argv: list[str]) -> list[tuple[str, list[str]]]:
    return [(argv[i + 1], argv[max(0, i - 4):i]) for i, arg in enumerate(argv) if arg == "-i"]


def test_every_ffmpeg_call_on_a_file_opens_only_that_file(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **options: Any) -> subprocess.CompletedProcess[Any]:
        calls.append(argv)
        empty = "" if options.get("text") else b""
        return subprocess.CompletedProcess(argv, 0, empty, empty)

    from tarjim.phone import delivery

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(shutil, "which", lambda name, *_a, **_k: name)
    monkeypatch.setattr(delivery, "DIRECT", 0)
    run_every_ffmpeg_call(tmp_path / "clip.mp4")
    opened = [entry for argv in calls for entry in inputs_of(argv) if entry[0] != "-"]
    assert len(opened) >= 12
    logo = str(mark.LOGO)
    logos = [before for name, before in opened if name == logo]
    assert logos and all(before == media.OWN_PICTURE for before in logos)
    assert all(before == media.OWN_FILE_ONLY for name, before in opened if name != logo), opened


def run_every_ffmpeg_call(clip: Path) -> None:
    from tarjim.dub import audio, mix
    from tarjim.phone import delivery
    from tarjim.render import burn, frames

    clip.write_bytes(b"video")
    ass, on_top = render_ass([], Canvas(96, 54)), mark.place_mark(Canvas(96, 54))
    for call in (lambda: media.check_readable(clip), lambda: media.extract_audio(clip, clip),
                 lambda: burn.burn(clip, ass, clip.with_suffix(".ar.mp4"), on_top),
                 lambda: mix.mux(clip, clip, clip), lambda: audio.decode(clip),
                 lambda: delivery.phone_copy(clip), lambda: media.probe(clip),
                 lambda: media.audio_bytes(clip), lambda: media.scene_cuts(clip),
                 lambda: media.bright_bottom(clip), lambda: frames.grab(clip, 1.0)):
        with contextlib.suppress(RuntimeError, ValueError):
            call()


@pytest.mark.parametrize("device", DEVICES)
@pytest.mark.parametrize("shape", ["{}.mp4", "{} .mp4", "{}..mp4", "{}.backup.mp4", "{} . .mkv"])
def test_a_windows_device_name_is_never_kept(device: str, shape: str) -> None:
    for spelled in (device, device.lower(), device.title()):
        name = safe_name(shape.format(spelled))
        assert name is not None
        first = name.split(".")[0].rstrip(" ").upper()
        assert first not in DEVICES and first != device, name


def test_ordinary_names_that_only_start_like_a_device_are_kept() -> None:
    assert safe_name("CONCERT.mp4") == "CONCERT.mp4"
    assert safe_name("nullify.mkv") == "nullify.mkv"
    assert safe_name("COM10.mp4") == "COM10.mp4"
    assert safe_name("aux files.mp3") == "aux files.mp3"


@pytest.mark.skipif(sys.platform != "win32", reason="device names exist only on Windows")
def test_on_windows_an_upload_named_like_a_device_lands_in_its_folder(tmp_path: Path) -> None:
    for device in ("NUL", "CON", "aux ", "Com1.x", "lpt¹"):
        name = safe_name(f"{device}.mp4")
        assert name is not None
        (tmp_path / name).write_bytes(b"video")
        assert name in os.listdir(tmp_path)
