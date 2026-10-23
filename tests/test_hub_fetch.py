"""The large files of a pinned model continue where a dropped download stopped, and count only
when they match the SHA-256 tarjim pinned; a model whose checked files are not all there is not
ready, and removing one takes only the pinned version."""
import hashlib
from pathlib import Path
from typing import Any

import pytest

from tarjim import hub_fetch, model_pins

REPO = "Qwen/Qwen3-ASR-1.7B-hf"
REVISION = model_pins.PINS[REPO].revision
DATA = b"0123456789" * 1000
SHA = hashlib.sha256(DATA).hexdigest()


class Reply:
    def __init__(self, status: int, body: bytes) -> None:
        self.status_code, self.body = status, body

    def __enter__(self) -> "Reply":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, _size: int) -> list[bytes]:
        return [self.body[:5000], self.body[5000:]]


@pytest.fixture
def cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from huggingface_hub import constants

    monkeypatch.setattr(constants, "HF_HUB_CACHE", str(tmp_path))
    return tmp_path / "models--Qwen--Qwen3-ASR-1.7B-hf"


def serve(monkeypatch: pytest.MonkeyPatch, ranges: bool = True) -> list[dict[str, str]]:
    asked: list[dict[str, str]] = []

    def get(_url: str, headers: dict[str, str], **_options: Any) -> Reply:
        asked.append(headers)
        start = int(headers["Range"][6:-1]) if "Range" in headers else 0
        if start >= len(DATA):
            return Reply(416, b"")
        return Reply(206, DATA[start:]) if start and ranges else Reply(200, DATA)

    monkeypatch.setattr(hub_fetch.requests, "get", get)
    return asked


def test_a_download_that_dropped_asks_only_for_what_is_missing(
        cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    part = cache / "partial" / REVISION / "model.safetensors.part"
    part.parent.mkdir(parents=True)
    part.write_bytes(DATA[:3000])
    asked = serve(monkeypatch)
    target = hub_fetch.fetch(REPO, REVISION, "model.safetensors", SHA)
    assert asked == [{"Range": "bytes=3000-"}] and target.read_bytes() == DATA
    assert target == cache / "snapshots" / REVISION / "model.safetensors" and not part.exists()


def test_a_server_that_ignores_the_range_starts_the_file_over(
        cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    part = cache / "partial" / REVISION / "model.safetensors.part"
    part.parent.mkdir(parents=True)
    part.write_bytes(b"stale")
    serve(monkeypatch, ranges=False)
    assert hub_fetch.fetch(REPO, REVISION, "model.safetensors", SHA).read_bytes() == DATA


def test_a_part_file_that_is_already_whole_is_only_checked(
        cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    part = cache / "partial" / REVISION / "model.safetensors.part"
    part.parent.mkdir(parents=True)
    part.write_bytes(DATA)
    serve(monkeypatch)
    assert hub_fetch.fetch(REPO, REVISION, "model.safetensors", SHA).read_bytes() == DATA


def test_a_file_that_does_not_match_its_checksum_is_removed_and_refused(
        cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    serve(monkeypatch)
    with pytest.raises(RuntimeError, match="does not match"):
        hub_fetch.fetch(REPO, REVISION, "model.safetensors", "0" * 64)
    assert not (cache / "snapshots" / REVISION / "model.safetensors").exists()


def test_a_model_is_ready_only_when_every_checked_file_is_there(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import huggingface_hub

    monkeypatch.setattr(huggingface_hub, "snapshot_download", lambda *_a, **_k: str(tmp_path))
    (tmp_path / "model.safetensors").write_bytes(b"x")
    assert not model_pins.ready(REPO)
    (tmp_path / "tokenizer.json").write_text("{}")
    assert model_pins.ready(REPO)


def test_removing_a_model_takes_only_the_pinned_version_when_others_share_the_cache(
        cache: Path) -> None:
    mine = cache / "snapshots" / REVISION
    other = cache / "snapshots" / ("f" * 40)
    for folder in (mine, other):
        folder.mkdir(parents=True)
    assert model_pins.remove(REPO) and not mine.exists() and other.exists()
    other.rmdir()
    mine.mkdir()
    assert model_pins.remove(REPO) and not cache.exists()
    assert not model_pins.remove(REPO)
