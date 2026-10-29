"""A result is written beside its final name and moved there only once it is whole, so a cancel
or a failed run never leaves a broken video, nor removes the good one an earlier run made."""
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def whole(target: Path) -> Iterator[Path]:
    """Gives the name to write; the part keeps the extension, which tells ffmpeg the format."""
    part = target.with_name(f"{target.stem}.part{target.suffix}")
    try:
        yield part
        if not part.is_file():
            raise RuntimeError(f"{target.name} was not written")
        os.replace(part, target)
    finally:
        part.unlink(missing_ok=True)
