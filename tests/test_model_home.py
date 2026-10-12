"""When the shared model cache cannot be written, tarjim keeps its models in its own folder."""
from pathlib import Path

import pytest

from tarjim import model_home


def test_the_usual_cache_is_kept_when_it_can_be_written(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("HF_HOME", raising=False)
    monkeypatch.setattr(model_home, "usual", lambda: tmp_path / "cache")
    assert model_home.fallback("", tmp_path / "own") == ""


def test_a_cache_that_refuses_writes_moves_the_models_to_tarjims_folder(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("HF_HOME", raising=False)
    blocked = tmp_path / "cache"
    blocked.write_text("a file where the folder should be", encoding="utf-8")
    monkeypatch.setattr(model_home, "usual", lambda: blocked / "huggingface")
    assert model_home.fallback("", tmp_path / "own") == str(tmp_path / "own")
    assert model_home.fallback("D:/models", tmp_path / "own") == ""
