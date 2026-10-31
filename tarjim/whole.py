"""A result is written beside its final name and moved there only once it is whole, so a cancel
or a failed run never leaves a broken video, nor removes the good one an earlier run made.

Windows refuses to replace a file another program holds open: a player showing the earlier
result, an antivirus scan, an upload of it (on 2026-10-31 a translation failed with "Access is
denied" while the earlier video was being sent to the phone). A scan or an upload lets go within
seconds, so the move is tried again for a while; a file still held after that is reported as
open in another program, which the person can close."""
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

PATIENCE = 30.0  # seconds
STEP = 0.5
IN_USE = "is open in another program"


def move(part: Path, target: Path, patience: float = PATIENCE) -> None:
    waited = 0.0
    while True:
        try:
            os.replace(part, target)
            return
        except PermissionError as error:
            if waited >= patience:
                raise PermissionError(f"{target.name} {IN_USE}; close it and try again") from error
        time.sleep(STEP)
        waited += STEP


@contextmanager
def whole(target: Path) -> Iterator[Path]:
    """Gives the name to write; the part keeps the extension, which tells ffmpeg the format."""
    part = target.with_name(f"{target.stem}.part{target.suffix}")
    try:
        yield part
        if not part.is_file():
            raise RuntimeError(f"{target.name} was not written")
        move(part, target)
    finally:
        part.unlink(missing_ok=True)
