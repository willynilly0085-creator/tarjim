"""The diacritics model's two files, checked before they are loaded.

catt-tashkeel fetches them from its GitHub release on first use and loads whatever arrived.
tarjim fetches the same release itself, keeps only the two files it names (nothing else in the
archive is written anywhere), and loads them only when each one's SHA-256 matches the release
as it was checked on 2026-10-15.
"""
import hashlib
import io
import zipfile
from pathlib import Path
from typing import Any

URL = "https://github.com/abjadai/catt/releases/download/v2/eo_model_onnx.zip"
FILES = {
    "encoder.onnx": "437a99c032ec7de4249280efbc4dce2d0532f95c9fe8356debf24ce05a34ba6a",
    "decoder.onnx": "e6575bdba8623bf51a6d459fc4955e8a98aa3c6c2ffc5abffac26e883792bc80",
}
MOST = 200 << 20
WAIT = 120
CHECKED: set[tuple[str, int, int]] = set()


def folder() -> Path:
    """Where catt-tashkeel keeps them, so a copy it already fetched is used when it matches."""
    import catt_tashkeel

    return Path(catt_tashkeel.__file__).parent / "onnx_models" / "eo_model"


def matches(path: Path, digest: str) -> bool:
    if not path.is_file():
        return False
    seen = (str(path), path.stat().st_size, path.stat().st_mtime_ns)
    if seen not in CHECKED:
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            return False
        CHECKED.add(seen)
    return True


def complete(where: Path) -> bool:
    return all(matches(where / name, digest) for name, digest in FILES.items())


def fetch(where: Path) -> None:
    import requests

    with requests.get(URL, timeout=WAIT, stream=True) as reply:
        reply.raise_for_status()
        body = reply.raw.read(MOST + 1, decode_content=True)
    if len(body) > MOST:
        raise RuntimeError("the diacritics model is larger than its release")
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        found = {name: archive.read(name) for name in FILES}
    if any(hashlib.sha256(data).hexdigest() != FILES[name] for name, data in found.items()):
        raise RuntimeError("the diacritics model does not match its release")
    where.mkdir(parents=True, exist_ok=True)
    for name, data in found.items():
        (where / name).write_bytes(data)


def model() -> Any:
    where = folder()
    if not complete(where):
        fetch(where)
    if not complete(where):
        raise RuntimeError("the diacritics model does not match its release")
    from catt_tashkeel import CATTEncoderOnly

    return CATTEncoderOnly(encoder_path=str(where / "encoder.onnx"),
                           decoder_path=str(where / "decoder.onnx"))
