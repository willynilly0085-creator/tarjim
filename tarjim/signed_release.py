"""An update takes only code that was signed on the owner's computer (2026-11-25).

A tag on GitHub can be moved, and anyone who takes over the GitHub account could publish a release
and its checksum alike, so neither is trusted. Each release carries three files, made and signed
by scripts/release_files.py with the key in the owner's Keychain (scripts/release_key.py):

- tarjim-update.zip, the release's code (git archive of its tag);
- tarjim-release.json, its tag, commit, and the zip's SHA-256 and size;
- tarjim-release.sig, an Ed25519 signature of that description.

The engine checks the signature against the public keys below before anything is installed: an
installed copy gets the checked zip saved on this computer, and a clone moves only to the signed
commit (source_updater.py). A release without them, or with anything changed, is refused, and
the reason is shown with the update. The updaters themselves stay standard library only: the
engine, which has cryptography, does the checking before it hands over.
"""
import base64
import hashlib
import hmac
import json
import re
from pathlib import Path
from typing import Any

from tarjim.release_pins import REPO

# The public halves of the keys releases are signed with. A new key is added here, in a release
# the old key signs, before the old one is dropped.
KEYS = ("qzfN2JyOJs0Rc/DhnveGd3gfTaTXWpwKq5D0YmGhLw8=",)  # made 2026-11-25, owner's Mac
DOWNLOADS = f"https://github.com/{REPO}/releases/download/{{tag}}/{{name}}"
ARCHIVE, MANIFEST, SIGNATURE = "tarjim-update.zip", "tarjim-release.json", "tarjim-release.sig"
PREFIX = b"tarjim release v1\n"  # what is signed is this, then the description
COMMIT, DIGEST = re.compile(r"[0-9a-f]{40}"), re.compile(r"[0-9a-f]{64}")
SMALL, LARGEST = 1 << 16, 64 << 20
WAIT, CHUNK = (15, 120), 1 << 20


class Refused(RuntimeError):
    """What GitHub gave for a release is not what the owner signed."""


def message(manifest: bytes) -> bytes:
    return PREFIX + manifest


def describe(tag: str, commit: str, archive: bytes) -> bytes:
    """The description release_files.py signs."""
    return json.dumps({"tag": tag, "commit": commit, "archive": ARCHIVE, "size": len(archive),
                       "sha256": hashlib.sha256(archive).hexdigest()}, sort_keys=True).encode()


def verify(manifest: bytes, signature: bytes) -> bool:
    """Signed with one of KEYS."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    try:
        raw = base64.b64decode(signature.strip(), validate=True)
    except ValueError:
        return False
    for key in KEYS:
        try:
            Ed25519PublicKey.from_public_bytes(base64.b64decode(key)).verify(raw, message(manifest))
        except (InvalidSignature, ValueError):
            continue
        return True
    return False


def fetch(tag: str, name: str, most: int) -> bytes:
    """One of the release's files, refused once it passes `most` bytes."""
    import requests

    data = bytearray()
    try:
        with requests.get(DOWNLOADS.format(tag=tag, name=name), stream=True,
                          timeout=WAIT) as reply:
            reply.raise_for_status()
            for chunk in reply.iter_content(CHUNK):
                data += chunk
                if len(data) > most:
                    raise Refused(f"{name} of {tag} is larger than its release says")
    except requests.RequestException as error:
        raise Refused(f"{name} of {tag} could not be downloaded ({error})") from error
    return bytes(data)


def checked(manifest: bytes, tag: str) -> dict[str, Any]:
    try:
        found = json.loads(manifest)
    except ValueError as error:
        raise Refused(f"the description of {tag} cannot be read") from error
    size = found.get("size") if isinstance(found, dict) else None
    fits = isinstance(size, int) and 0 < size <= LARGEST
    if not fits or found.get("tag") != tag or found.get("archive") != ARCHIVE:
        raise Refused(f"the signed description is not the one of {tag}")
    if not COMMIT.fullmatch(str(found.get("commit"))) or not DIGEST.fullmatch(
            str(found.get("sha256"))):
        raise Refused(f"the signed description of {tag} is incomplete")
    return dict(found)


def release(tag: str) -> dict[str, Any]:
    """The release's signed description: refused unless one of KEYS signed it for this tag."""
    manifest, signature = fetch(tag, MANIFEST, SMALL), fetch(tag, SIGNATURE, SMALL)
    if not verify(manifest, signature):
        raise Refused(f"{tag} is not signed with tarjim's release key")
    return checked(manifest, tag)


def archive(tag: str, folder: Path) -> Path:
    """The release's zip, saved in `folder` only when it is the one signed."""
    signed = release(tag)
    data = fetch(tag, ARCHIVE, signed["size"])
    if not hmac.compare_digest(hashlib.sha256(data).hexdigest(), signed["sha256"]):
        raise Refused(f"the code of {tag} is not the code its release was signed for")
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("tarjim-*.zip"):
        old.unlink(missing_ok=True)
    target = folder / f"tarjim-{tag}.zip"
    target.write_bytes(data)
    return target


def refused(why: Refused) -> str:
    from tarjim import installer

    installer.record("failed", f"update refused: {why}", installer.UPDATE_STATE)
    return ""


def saved_archive(tag: str, folder: Path) -> str:
    """The checked zip's address for the installer, or nothing (the reason goes to update.json)."""
    try:
        return archive(tag, folder).as_uri()
    except Refused as why:
        return refused(why)


def signed_commit(tag: str) -> str:
    """The commit the release was signed for, or nothing (the reason goes to update.json)."""
    try:
        return str(release(tag)["commit"])
    except Refused as why:
        return refused(why)
