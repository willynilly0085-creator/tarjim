"""A build of tarjim's ffmpeg that a running job may use is never removed under it: installing
leaves the old build, which goes only once nothing runs, and installing a build that is already
in place keeps it as it is instead of removing and unpacking it again."""
from pathlib import Path

import pytest

from tarjim import config, ffmpeg_release, ffmpeg_setup, ffmpeg_update, update

BRANCH = ffmpeg_setup.ARCHIVE
OLD, NEW = "a" * 64, "b" * 64


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(config, "HOME", tmp_path)
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(config, "prepare_environment", lambda: None)
    monkeypatch.setattr(ffmpeg_update, "AVAILABLE", True)
    monkeypatch.setattr(update, "installed_by_uv", lambda: True)
    for name in ffmpeg_update.OVERRIDES:
        monkeypatch.delenv(name, raising=False)
    return tmp_path


def installed_build(home: Path, digest: str) -> Path:
    folder = home / "tools" / "ffmpeg" / digest[:16]
    (folder / "bin").mkdir(parents=True)
    for program in ("ffmpeg.exe", "ffprobe.exe"):
        (folder / "bin" / program).write_text("", encoding="utf-8")
    (folder / ffmpeg_release.RECORD).write_text(f"{digest}  {BRANCH}\n", encoding="utf-8")
    config.save("ffmpeg", str(folder / "bin" / "ffmpeg.exe"))
    config.save("ffprobe", str(folder / "bin" / "ffprobe.exe"))
    return folder


def test_installing_while_a_job_runs_leaves_the_build_it_uses(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    old = installed_build(home, OLD)
    monkeypatch.setattr(ffmpeg_release, "ask", lambda: {BRANCH: NEW})
    monkeypatch.setattr(ffmpeg_release, "build", lambda _name, digest: installed_build(
        home, digest) / "bin" / "ffmpeg.exe")
    monkeypatch.setattr(ffmpeg_setup.sys, "platform", "win32")
    ffmpeg_setup.install_ffmpeg()
    assert old.is_dir()  # a job started on it still finds its files
    config.save("auto_update", "no")  # removing an unused build is no update
    assert ffmpeg_update.refresh(idle=False, now=1e6) == "" and old.is_dir()
    assert ffmpeg_update.refresh(idle=True, now=1e6) == "" and not old.exists()
    assert (home / "tools" / "ffmpeg" / NEW[:16]).is_dir()


def test_a_build_already_in_place_is_used_as_it_is(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import requests

    folder = installed_build(home, OLD)
    monkeypatch.setattr(ffmpeg_release, "runs", lambda _program: True)
    monkeypatch.setattr(requests, "get", lambda *_a, **_k: pytest.fail("downloaded again"))
    assert ffmpeg_release.build(BRANCH, OLD) == folder / "bin" / "ffmpeg.exe"
    assert ffmpeg_release.installed(folder) == (OLD, BRANCH)


def test_a_broken_build_in_place_is_fetched_again(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    installed_build(home, OLD)
    monkeypatch.setattr(ffmpeg_release, "runs", lambda _program: False)
    fetched: list[str] = []
    monkeypatch.setattr(ffmpeg_release, "download", lambda name, *_a: fetched.append(name)
                        or (_ for _ in ()).throw(ffmpeg_release.Refused("offline")))
    with pytest.raises(ffmpeg_release.Refused):
        ffmpeg_release.build(BRANCH, OLD)
    assert fetched == [BRANCH]
