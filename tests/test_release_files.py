"""A release carries the Mac and Linux installer, the Windows folder, so GitHub counts them, and
the signed update engines take (signed_release.py)."""
import base64
import importlib.util
import subprocess
import zipfile
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from tarjim import signed_release

ROOT = Path(__file__).resolve().parents[1]


def script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("release_files",
                                                  ROOT / "scripts" / "release_files.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def owner(monkeypatch: pytest.MonkeyPatch) -> Ed25519PrivateKey:
    """A key in place of the one in the owner's Keychain, carried by tarjim for this test."""
    key = Ed25519PrivateKey.generate()
    raw = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    monkeypatch.setattr(signed_release, "KEYS", (base64.b64encode(raw).decode(),))
    return key


def made(tmp_path: Path, sign: Any) -> list[Path]:
    try:
        return list(script().make("HEAD", tmp_path, sign))
    except (OSError, subprocess.CalledProcessError) as error:  # a copy without its history
        pytest.skip(f"no git history here: {error}")


def test_the_release_files_are_made_from_the_tag_and_signed(
        tmp_path: Path, owner: Ed25519PrivateKey, monkeypatch: pytest.MonkeyPatch) -> None:
    files = made(tmp_path, lambda text: base64.b64encode(owner.sign(text)))
    script_file, archive = files[0], files[1]
    text = script_file.read_bytes()
    assert text.startswith(b"#!/usr/bin/env bash") and b"\r" not in text
    names = zipfile.ZipFile(archive).namelist()
    assert "tarjim/install.cmd" in names and "tarjim/scripts/windows/install.ps1" in names
    assert [path.name for path in files[2:]] == [signed_release.ARCHIVE, signed_release.MANIFEST,
                                                 signed_release.SIGNATURE]
    monkeypatch.setattr(signed_release, "fetch",
                        lambda _tag, name, _most: (tmp_path / name).read_bytes())
    saved = signed_release.archive("HEAD", tmp_path / "updates")  # what an engine would take
    assert saved.read_bytes() == archive.read_bytes()


def test_a_release_signed_with_a_key_engines_do_not_carry_is_not_made(
        tmp_path: Path, owner: Ed25519PrivateKey) -> None:
    stranger = Ed25519PrivateKey.generate()
    with pytest.raises(SystemExit):
        made(tmp_path, lambda text: base64.b64encode(stranger.sign(text)))
