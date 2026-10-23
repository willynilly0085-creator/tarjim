"""tarjim's own ffmpeg keeps itself current: once a day, with automatic updates on and nothing
running, checked against BtbN's published SHA-256, and never an ffmpeg the person chose."""
import hashlib
import zipfile
from pathlib import Path
from typing import Any

import pytest

from tarjim import config, ffmpeg_release, ffmpeg_setup, ffmpeg_update, update

BRANCH = "ffmpeg-n8.1-latest-win64-lgpl-shared-8.1.zip"
NEXT = "ffmpeg-n9.0-latest-win64-lgpl-shared-9.0.zip"
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


def installed_build(home: Path, digest: str = OLD, name: str = BRANCH) -> Path:
    folder = home / "tools" / "ffmpeg" / digest[:16]
    (folder / "bin").mkdir(parents=True)
    for program in ("ffmpeg.exe", "ffprobe.exe"):
        (folder / "bin" / program).write_text("", encoding="utf-8")
    (folder / ffmpeg_release.RECORD).write_text(f"{digest}  {name}\n", encoding="utf-8")
    config.save("ffmpeg", str(folder / "bin" / "ffmpeg.exe"))
    config.save("ffprobe", str(folder / "bin" / "ffprobe.exe"))
    return folder


def published(monkeypatch: pytest.MonkeyPatch, listed: dict[str, str]) -> list[str]:
    asked: list[str] = []
    monkeypatch.setattr(ffmpeg_release, "ask", lambda: asked.append("checksums") or dict(listed))
    return asked


def builds(monkeypatch: pytest.MonkeyPatch, home: Path,
           error: Exception | None = None) -> list[tuple[str, str]]:
    made: list[tuple[str, str]] = []

    def build(name: str, digest: str) -> Path:
        made.append((name, digest))
        if error:
            raise error
        return installed_build(home, digest, name) / "bin" / "ffmpeg.exe"

    monkeypatch.setattr(ffmpeg_release, "build", build)
    return made


def test_only_release_branch_builds_with_a_plain_digest_are_read() -> None:
    listing = "\n".join([f"{OLD}  {BRANCH}", f"{NEW}  {NEXT}",
                         f"{OLD}  ffmpeg-master-latest-win64-lgpl-shared.zip",
                         f"{OLD}  ffmpeg-n8.1-latest-win64-gpl-shared-8.1.zip",
                         f"{OLD}  ffmpeg-n8.1-latest-win64-lgpl-shared-9.0.zip",
                         f"{OLD}  ffmpeg-n٨.1-latest-win64-lgpl-shared-٨.1.zip",
                         f"{'A' * 64}  ffmpeg-n7.1-latest-win64-lgpl-shared-7.1.zip",
                         f"{OLD}  {BRANCH} extra", f"{OLD[:63]}  {BRANCH}"])
    assert ffmpeg_release.builds(listing) == {BRANCH: OLD, NEXT: NEW}
    assert ffmpeg_release.branch(NEXT) == (9, 0) and ffmpeg_release.branch("../x.zip") == ()


def test_the_branch_in_use_is_kept_until_it_is_no_longer_built() -> None:
    later = "ffmpeg-n10.0-latest-win64-lgpl-shared-10.0.zip"
    assert ffmpeg_release.choose({BRANCH: OLD, NEXT: NEW}, BRANCH) == BRANCH
    assert ffmpeg_release.choose({NEXT: NEW, later: OLD}, BRANCH) == later
    assert ffmpeg_release.choose({}, BRANCH) == ""


class Reply:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> "Reply":
        return self

    def __exit__(self, *_: Any) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, _size: int) -> list[bytes]:
        return [self.body]


def a_build(tmp_path: Path, programs: tuple[str, ...] = ("ffmpeg.exe", "ffprobe.exe")) -> bytes:
    archive = tmp_path / "made.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        for program in programs:
            bundle.writestr(f"ffmpeg-n8.1-latest-win64-lgpl-shared-8.1/bin/{program}", "exe")
    return archive.read_bytes()


def test_a_build_is_used_only_when_its_checksum_matches(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import requests

    body = a_build(home)
    monkeypatch.setattr(requests, "get", lambda *_a, **_k: Reply(body))
    monkeypatch.setattr(ffmpeg_release, "runs", lambda _program: True)
    with pytest.raises(ffmpeg_release.Refused, match="checksum"):
        ffmpeg_release.build(BRANCH, NEW)
    assert not (home / "tools" / "ffmpeg" / NEW[:16]).exists()
    digest = hashlib.sha256(body).hexdigest()
    binary = ffmpeg_release.build(BRANCH, digest)
    folder = home / "tools" / "ffmpeg" / digest[:16]
    assert binary == folder / "ffmpeg-n8.1-latest-win64-lgpl-shared-8.1" / "bin" / "ffmpeg.exe"
    assert ffmpeg_release.installed(folder) == (digest, BRANCH)
    assert sorted(p.name for p in (home / "tools" / "ffmpeg").iterdir()) == [digest[:16]]
    with pytest.raises(ffmpeg_release.Refused):
        ffmpeg_release.download("../../evil.zip", digest, home / "x.zip")


def test_a_build_without_a_working_ffprobe_is_refused(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import requests

    body = a_build(home, ("ffmpeg.exe",))
    monkeypatch.setattr(requests, "get", lambda *_a, **_k: Reply(body))
    monkeypatch.setattr(ffmpeg_release, "runs", lambda program: program.is_file())
    with pytest.raises(ffmpeg_release.Refused, match="ffprobe"):
        ffmpeg_release.build(BRANCH, hashlib.sha256(body).hexdigest())
    assert list((home / "tools" / "ffmpeg").iterdir()) == []


def test_a_changed_build_moves_ffmpeg_and_ffprobe_and_the_old_goes_the_next_day(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    old = installed_build(home)
    asked = published(monkeypatch, {BRANCH: NEW, NEXT: OLD})
    made = builds(monkeypatch, home)
    assert ffmpeg_update.refresh(idle=True, now=1e6) == BRANCH and made == [(BRANCH, NEW)]
    new = home / "tools" / "ffmpeg" / NEW[:16]
    assert config.setting("ffmpeg") == str(new / "bin" / "ffmpeg.exe")
    assert config.setting("ffprobe") == str(new / "bin" / "ffprobe.exe")
    assert old.is_dir()  # a job started just before still finds its files
    state = update.view()["ffmpeg"]
    assert state["own"] and state["state"] == "done" and state["sha256"] == NEW
    assert ffmpeg_update.refresh(idle=True, now=1e6 + 3600) == ""  # once a day
    assert ffmpeg_update.refresh(idle=True, now=1e6 + 25 * 3600) == "" and len(made) == 1
    assert not old.exists() and new.is_dir() and len(asked) == 2  # same checksum: nothing


def test_a_failed_build_keeps_the_old_one_in_use(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    old = installed_build(home)
    published(monkeypatch, {BRANCH: NEW})
    builds(monkeypatch, home, ffmpeg_release.Refused(f"{BRANCH} does not match its checksum"))
    assert ffmpeg_update.refresh(idle=True, now=1e6) == ""
    assert config.setting("ffmpeg") == str(old / "bin" / "ffmpeg.exe") and old.is_dir()
    state = ffmpeg_update.view()
    assert state["state"] == "failed" and "checksum" in state["detail"]


def test_a_build_from_before_the_record_and_a_dropped_branch_are_renewed(
        home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    legacy = home / "tools" / "ffmpeg" / BRANCH.removesuffix(".zip")
    installed_build(home)
    (home / "tools" / "ffmpeg" / OLD[:16]).rename(legacy)
    config.save("ffmpeg", str(legacy / "bin" / "ffmpeg.exe"))
    config.save("ffprobe", str(legacy / "bin" / "ffprobe.exe"))
    (legacy / ffmpeg_release.RECORD).unlink()
    published(monkeypatch, {NEXT: NEW})
    made = builds(monkeypatch, home)
    assert ffmpeg_update.refresh(idle=True, now=1e6) == NEXT and made == [(NEXT, NEW)]
    assert legacy.is_dir() and ffmpeg_update.view()["build"] == NEXT


@pytest.mark.parametrize("why", ["theirs", "pointed to", "busy", "automatic off", "source copy",
                                 "installing"])
def test_never_an_ffmpeg_the_person_chose_nor_while_anything_runs(
        home: Path, monkeypatch: pytest.MonkeyPatch, why: str) -> None:
    installed_build(home)
    if why == "theirs":
        config.save("ffmpeg", str(home / "elsewhere" / "ffmpeg.exe"))
    if why == "pointed to":
        monkeypatch.setenv("TARJIM_FFMPEG", "C:/ffmpeg/bin/ffmpeg.exe")
    if why == "automatic off":
        config.save("auto_update", "no")
    if why == "source copy":
        monkeypatch.setattr(update, "installed_by_uv", lambda: False)
    asked = published(monkeypatch, {BRANCH: NEW})
    made = builds(monkeypatch, home)
    if why == "installing":
        with ffmpeg_setup.PLACING:
            assert ffmpeg_update.refresh(idle=True, now=1e6) == ""
    else:
        assert ffmpeg_update.refresh(idle=why != "busy", now=1e6) == ""
    assert asked == [] and made == []
    assert ffmpeg_update.view()["own"] is (why not in ("theirs", "pointed to"))
