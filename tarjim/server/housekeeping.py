"""Copies of videos that tarjim keeps to work on (uploads, downloads from links) and the work
kept for them (sound, transcript, cues) are cleared a week after their last use. The results in
the person's downloads folder are never touched."""
import shutil
import time
from collections.abc import Callable
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


def remove(entry: Path) -> None:
    try:
        shutil.rmtree(entry) if entry.is_dir() else entry.unlink(missing_ok=True)
    except OSError:  # still held open by a job left behind; it tries again when it ends
        return


def everything(_name: str) -> bool:
    return True


def nothing() -> Path | None:
    return None


class Undo:
    """What one job adds to a folder, so a cancel can take it back. Only entries that were not
    there when the job began are removed: never what was there before, never what is kept."""

    def __init__(self, folder: Path, chosen: Callable[[str], bool] = everything,
                 keep: Callable[[], Path | None] = nothing) -> None:
        self.folder, self.chosen, self.keep = folder, chosen, keep
        self.before = self.entries()

    def entries(self) -> set[Path]:
        try:
            return {p for p in self.folder.iterdir() if self.chosen(p.name)}
        except OSError:
            return set()

    def __call__(self) -> None:
        kept = self.keep()
        for entry in self.entries() - self.before:
            if entry != kept:
                remove(entry)
