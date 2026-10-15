"""The two dubbing models fetched outside the usual tool download are checked before they load:
the voice separation weights must name demucs' own model class, and the diacritics files must
match their published release byte for byte."""
import hashlib
import io
import zipfile
from pathlib import Path
from typing import Any

import pytest

from tarjim import model_pins
from tarjim.dub import catt_files, separate


def weights(path: Path, klass: str) -> Path:
    import torch
    from safetensors.torch import save_file

    save_file({"x": torch.zeros(1)}, str(path), metadata={"klass": klass, "args": "[]",
                                                          "kwargs": "{}"})
    return path


def test_a_weights_file_naming_any_other_class_is_refused(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="not the one tarjim checked"):
        separate.checked_part(weights(tmp_path / "1234abcd.safetensors", "os.system"))


@pytest.mark.parametrize("parts", ["['../../evil']", "[]", "['955717e8.safetensors']"])
def test_a_model_list_naming_other_files_is_refused(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, parts: str) -> None:
    (tmp_path / "htdemucs.yaml").write_text(f"models: {parts}\n", encoding="utf-8")
    monkeypatch.setattr(separate, "pinned_folder", lambda: tmp_path)
    with pytest.raises(RuntimeError, match="not the one tarjim checked"):
        separate.separation_model()


def test_the_separation_model_is_fetched_once_at_its_pinned_commit_while_online(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from huggingface_hub import constants

    online: list[bool] = []
    monkeypatch.setattr(model_pins, "ready", lambda _repo: False)
    monkeypatch.setattr(model_pins, "download",
                        lambda repo: online.append(not constants.HF_HUB_OFFLINE) or tmp_path)
    monkeypatch.setattr(model_pins, "folder", lambda repo: tmp_path)
    assert separate.pinned_folder() == tmp_path and online == [True]


def archive(files: dict[str, bytes]) -> bytes:
    body = io.BytesIO()
    with zipfile.ZipFile(body, "w") as out:
        for name, data in files.items():
            out.writestr(name, data)
    return body.getvalue()


@pytest.fixture
def release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, bytes]:
    files = {"encoder.onnx": b"encoder", "decoder.onnx": b"decoder"}
    monkeypatch.setattr(catt_files, "FILES", {name: hashlib.sha256(data).hexdigest()
                                              for name, data in files.items()})
    monkeypatch.setattr(catt_files, "folder", lambda: tmp_path / "eo_model")
    return files


def serve(monkeypatch: pytest.MonkeyPatch, body: bytes) -> None:
    import requests

    class Raw:
        def read(self, most: int, decode_content: bool = False) -> bytes:
            return body[:most]

    class Reply:
        raw = Raw()

        def __enter__(self) -> "Reply":
            return self

        def __exit__(self, *_: Any) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(requests, "get", lambda url, **_options: Reply())


def test_matching_diacritics_files_are_kept_and_nothing_else_is_written(
        release: dict[str, bytes], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    serve(monkeypatch, archive({**release, "../outside.txt": b"x", "extra.py": b"x"}))
    catt_files.fetch(tmp_path / "eo_model")
    assert sorted(p.name for p in tmp_path.rglob("*") if p.is_file()) == sorted(release)
    assert catt_files.complete(tmp_path / "eo_model")


def test_a_changed_diacritics_file_is_never_written_or_loaded(
        release: dict[str, bytes], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    serve(monkeypatch, archive({**release, "encoder.onnx": b"something else"}))
    with pytest.raises(RuntimeError, match="does not match"):
        catt_files.model()
    assert not (tmp_path / "eo_model").exists()


def test_a_tampered_copy_already_on_disk_is_replaced_by_the_checked_release(
        release: dict[str, bytes], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    where = tmp_path / "eo_model"
    where.mkdir()
    (where / "encoder.onnx").write_bytes(b"tampered")
    (where / "decoder.onnx").write_bytes(release["decoder.onnx"])
    assert not catt_files.complete(where)
    serve(monkeypatch, archive(release))
    catt_files.fetch(where)
    assert (where / "encoder.onnx").read_bytes() == release["encoder.onnx"]
