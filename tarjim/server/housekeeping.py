"""Copies of videos that tarjim keeps to work on (uploads, downloads from links) are cleared a
week after their last use. The results in the person's downloads folder are never touched."""
import shutil
import time
from pathlib import Path

KEEP_DAYS = 7
DAY = 24 * 3600


def newest(entry: Path) -> float:
    inside = [p.stat().st_mtime for p in entry.rglob("*")] if entry.is_dir() else []
    return max([entry.stat().st_mtime, *inside])


def sweep(folders: list[Path], days: int = KEEP_DAYS) -> None:
    limit = time.time() - days * DAY
    for folder in folders:
        for entry in folder.iterdir() if folder.is_dir() else []:
            try:
                if newest(entry) < limit:
                    shutil.rmtree(entry) if entry.is_dir() else entry.unlink()
            except OSError:
                continue
