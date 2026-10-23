"""The large files of a pinned model, fetched so that a dropped download continues where it stopped.

huggingface_hub 1.x and later start a file over on every attempt (its partial file is unique to
the attempt and deleted when it fails), which a 4 GB model over a weak line may never get
through. Each file whose SHA-256 tarjim pinned is fetched here instead, from the same address
at the same commit, into a part file kept beside the model; the next attempt asks only for what
is missing. Once the whole file is in and matches its SHA-256 it is moved into the model's
folder at that commit, where the hub finds it and fetches only the small files around it.
"""
from contextlib import suppress
from pathlib import Path

import requests

BLOCK = 1 << 20
WAIT = 60
PARTIAL = 206
OK = 200
COMPLETE = 416  # asked for bytes past the end: the part file already holds the whole file


def address(repo: str, revision: str, name: str) -> str:
    from huggingface_hub import constants

    return f"{constants.ENDPOINT}/{repo}/resolve/{revision}/{name}"


def continue_into(url: str, part: Path) -> None:
    have = part.stat().st_size if part.exists() else 0
    headers = {"Range": f"bytes={have}-"} if have else {}
    with requests.get(url, headers=headers, stream=True, timeout=WAIT) as reply:
        if have and reply.status_code == COMPLETE:
            return
        if reply.status_code not in (OK, PARTIAL):
            reply.raise_for_status()
            raise OSError(f"the model server answered {reply.status_code}")
        resumed = reply.status_code == PARTIAL
        with part.open("ab" if resumed else "wb") as out:
            for block in reply.iter_content(BLOCK):
                out.write(block)


def fetch(repo: str, revision: str, name: str, sha256: str) -> Path:
    """The file in the model's folder at that commit, checked against its SHA-256."""
    from tarjim.model_pins import cache_of, check

    target = cache_of(repo) / "snapshots" / revision / name
    if not target.is_file():
        part = cache_of(repo) / "partial" / revision / f"{name}.part"
        part.parent.mkdir(parents=True, exist_ok=True)
        continue_into(address(repo, revision, name), part)
        target.parent.mkdir(parents=True, exist_ok=True)
        part.replace(target)
        with suppress(OSError):  # another part file of the same commit may still be there
            part.parent.rmdir()
    check(target, sha256)
    return target
