"""An update installs only what the owner signed: a changed zip, a changed description, another
key, another release's signature or a missing one is refused; the signed one installs."""
import base64
import json
import zipfile
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from tarjim import config, installer, release_pins, signed_release, update

COMMIT = "a" * 40
Published = dict[tuple[str, str], bytes]


def public(key: Ed25519PrivateKey) -> str:
    return base64.b64encode(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()


def code(folder: Path) -> bytes:
    """A release's zip as git archive makes it, with its tested versions inside."""
    path = folder / "made.zip"
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr("tarjim/pyproject.toml", "[project]\nname = 'tarjim'\n")
        bundle.writestr("tarjim/tarjim/constraints.txt", "numpy==2.5.4\n")
        bundle.writestr("tarjim/tarjim/python.txt", "3.12\n")
    return path.read_bytes()


def publish(found: Published, tag: str, archive: bytes, key: Ed25519PrivateKey) -> None:
    manifest = signed_release.describe(tag, COMMIT, archive)
    found[(tag, signed_release.ARCHIVE)] = archive
    found[(tag, signed_release.MANIFEST)] = manifest
    found[(tag, signed_release.SIGNATURE)] = base64.b64encode(
        key.sign(signed_release.message(manifest)))


@pytest.fixture
def github(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Published, Any, bytes]:
    """The release files GitHub serves, and the owner's key, the one tarjim carries."""
    owner, served = Ed25519PrivateKey.generate(), {}
    monkeypatch.setattr(signed_release, "KEYS", (public(owner),))
    monkeypatch.setattr(config, "HOME", tmp_path)
    monkeypatch.setattr(installer, "HOME", tmp_path)
    monkeypatch.setattr(installer, "UPDATE_STATE", tmp_path / "update.json")

    def fetch(tag: str, name: str, most: int) -> bytes:
        if (tag, name) not in served:
            raise signed_release.Refused(f"{name} of {tag} could not be downloaded (404)")
        data = served[(tag, name)]
        if len(data) > most:
            raise signed_release.Refused(f"{name} of {tag} is larger than its release says")
        return data

    monkeypatch.setattr(signed_release, "fetch", fetch)
    archive = code(tmp_path)
    publish(served, "v1.3.0", archive, owner)
    return served, owner, archive


def test_the_signed_release_is_saved_as_it_was_signed(github: Any, tmp_path: Path) -> None:
    _served, _owner, archive = github
    saved = signed_release.archive("v1.3.0", tmp_path / "updates")
    assert saved.read_bytes() == archive
    assert signed_release.release("v1.3.0")["commit"] == COMMIT


def changed_code(served: Published, _owner: Any) -> None:
    data = bytearray(served[("v1.3.0", signed_release.ARCHIVE)])
    data[-30] ^= 1
    served[("v1.3.0", signed_release.ARCHIVE)] = bytes(data)


def changed_description(served: Published, _owner: Any) -> None:
    found = json.loads(served[("v1.3.0", signed_release.MANIFEST)])
    found["sha256"] = "0" * 64
    served[("v1.3.0", signed_release.MANIFEST)] = json.dumps(found, sort_keys=True).encode()


def another_key(served: Published, _owner: Any) -> None:
    publish(served, "v1.3.0", served[("v1.3.0", signed_release.ARCHIVE)] + b"x",
            Ed25519PrivateKey.generate())


def an_older_release_under_the_new_tag(served: Published, owner: Any) -> None:
    publish(served, "v1.2.9", b"older code", owner)
    for name in (signed_release.ARCHIVE, signed_release.MANIFEST, signed_release.SIGNATURE):
        served[("v1.3.0", name)] = served[("v1.2.9", name)]


def no_signature(served: Published, _owner: Any) -> None:
    del served[("v1.3.0", signed_release.SIGNATURE)]


@pytest.mark.parametrize("tamper", [changed_code, changed_description, another_key,
                                    an_older_release_under_the_new_tag, no_signature])
def test_anything_but_the_signed_release_is_refused(github: Any, tmp_path: Path,
                                                    tamper: Any) -> None:
    served, owner, _archive = github
    tamper(served, owner)
    with pytest.raises(signed_release.Refused):
        signed_release.archive("v1.3.0", tmp_path / "updates")
    assert not list((tmp_path / "updates").glob("*.zip"))


def installed(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    started: list[list[str]] = []
    monkeypatch.setattr(installer, "start_detached", lambda c, _log: started.append(c) or True)
    monkeypatch.setattr(update, "installed_by_uv", lambda: True)
    monkeypatch.setattr(update.shutil, "which", lambda _name: "uv")
    return started


def test_the_installer_is_handed_the_checked_zip(
        github: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    started = installed(monkeypatch)
    assert update.start("v1.3.0", 17700)
    source = started[0][started[0].index("--after") - 1]
    assert source == (tmp_path / "updates" / "tarjim-v1.3.0.zip").as_uri()
    assert release_pins.python_for(source, tmp_path) == "3.12"  # read inside the checked zip
    pins = release_pins.tested_versions(source, tmp_path)
    assert pins and pins.read_text(encoding="utf-8") == "numpy==2.5.4\n"
    assert release_pins.install_command("uv", source)[-1] == f"tarjim[dub] @ {source}"


def test_a_changed_release_is_not_installed_and_the_page_says_why(
        github: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    served, owner, _archive = github
    changed_code(served, owner)
    started = installed(monkeypatch)
    assert not update.start("v1.3.0", 17700) and started == []
    said = json.loads((tmp_path / "update.json").read_text(encoding="utf-8"))
    assert said["state"] == "failed" and "not the code its release was signed for" in said[
        "detail"]
    assert update.failed_lately()  # not tried again by itself for a day


def test_a_clone_is_handed_the_signed_commit_and_nothing_without_one(
        github: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    served, _owner, _archive = github
    started = installed(monkeypatch)
    monkeypatch.setattr(update, "installed_by_uv", lambda: False)
    monkeypatch.setattr(update, "from_source", lambda: True)
    assert update.start("v1.3.0", 17700)
    command = started[0]
    assert command[command.index("--commit") + 1] == COMMIT
    del served[("v1.3.0", signed_release.SIGNATURE)]
    assert not update.start("v1.3.0", 17700) and len(started) == 1


def test_the_key_tarjim_carries_is_a_real_ed25519_key() -> None:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    for key in signed_release.KEYS:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(key, validate=True))
