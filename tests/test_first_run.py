from pathlib import Path
from typing import Any

import pytest

from tarjim import ffmpeg_release, ffmpeg_setup, system, tools


def test_the_ffmpeg_checksum_is_read_from_the_release_listing() -> None:
    digest = "f" * 64
    listing = "\n".join([f"{'a' * 64}  other.zip", f"{digest}  {ffmpeg_setup.ARCHIVE}", ""])
    assert ffmpeg_release.builds(listing) == {ffmpeg_setup.ARCHIVE: digest}
    assert ffmpeg_release.builds(f"{'a' * 64}  other.zip") == {}


def test_a_tampered_ffmpeg_download_is_refused(tmp_path: Path,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
    import requests

    class Reply:
        def __enter__(self) -> "Reply":
            return self

        def __exit__(self, *_: Any) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

        def iter_content(self, _size: int) -> list[bytes]:
            return [b"not really ffmpeg"]

    monkeypatch.setattr(requests, "get", lambda *_a, **_k: Reply())
    with pytest.raises(RuntimeError, match="checksum"):
        ffmpeg_release.download(ffmpeg_setup.ARCHIVE, "0" * 64, tmp_path / "ffmpeg.zip")
    assert not (tmp_path / "ffmpeg.zip").exists()


def test_a_card_torch_cannot_use_is_reported_with_the_fix(monkeypatch: pytest.MonkeyPatch) -> None:
    import torch

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(system, "nvidia_card", lambda: {"name": "RTX", "memory_gb": 16.0})
    system.graphics.cache_clear()
    try:
        card = system.graphics()
    finally:
        system.graphics.cache_clear()
    assert card is not None and card["usable"] is False
    assert "download.pytorch.org/whl/cu128" in str(card["fix"])


def test_local_listening_makes_its_model_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tools, "installed", lambda _tool: False)
    monkeypatch.setattr(tools, "listening_locally", lambda: True)
    required = {v["id"]: v["required"] for v in tools.Shelf().view()}
    assert required["accuracy"] and required["ffmpeg"]
    monkeypatch.setattr(tools, "listening_locally", lambda: False)
    assert not {v["id"]: v["required"] for v in tools.Shelf().view()}["accuracy"]


def test_models_fall_back_to_the_processor_without_a_usable_card(
        monkeypatch: pytest.MonkeyPatch) -> None:
    import torch

    from tarjim.device import best_device, precision

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert best_device() == "cpu"
    assert precision("cpu", torch.float16) is torch.float32
    assert precision("cuda:0", torch.float16) is torch.float16
