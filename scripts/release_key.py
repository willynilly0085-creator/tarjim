"""The key tarjim's releases are signed with, kept in this computer's Keychain (2026-11-25).

Its private half never leaves the Keychain of the owner's Mac: not the repository, not GitHub's
secrets, not a file. Its public half is in tarjim/signed_release.py, and every engine checks an
update against it (scripts/release_files.py signs each release). A session over ssh cannot read
the Keychain: sign from the Mac's own session.

    python scripts/release_key.py create   # once: makes the key and prints its public half
    python scripts/release_key.py public   # the public half again
"""
import base64
import sys

SERVICE, ACCOUNT = "tarjim-release-signing", "ed25519"


def saved() -> str:
    import keyring

    return keyring.get_password(SERVICE, ACCOUNT) or ""


def private():  # type: ignore[no-untyped-def]
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    raw = saved()
    if not raw:
        raise SystemExit("no release key in this computer's Keychain: releases are signed on the "
                         "owner's Mac, from its own session (not over ssh)")
    return Ed25519PrivateKey.from_private_bytes(base64.b64decode(raw))


def public() -> str:
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    raw = private().public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return base64.b64encode(raw).decode()


def create() -> str:
    """A new key, only when there is none: replacing it would lock every engine out of updates."""
    import keyring
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
    )

    if saved():
        raise SystemExit("a release key is already in the Keychain; it is kept")
    if keyring.get_keyring().priority < 1:
        raise SystemExit(f"no safe keyring here ({keyring.get_keyring()}); the key is not made")
    raw = Ed25519PrivateKey.generate().private_bytes(Encoding.Raw, PrivateFormat.Raw,
                                                     NoEncryption())
    keyring.set_password(SERVICE, ACCOUNT, base64.b64encode(raw).decode())
    return public()


def sign(text: bytes) -> bytes:
    return base64.b64encode(private().sign(text)) + b"\n"


if __name__ == "__main__":
    chosen = sys.argv[1] if len(sys.argv) > 1 else ""
    if chosen not in ("create", "public"):
        raise SystemExit(__doc__)
    print(create() if chosen == "create" else public())
