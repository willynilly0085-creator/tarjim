import json
import shutil
from collections.abc import Callable
from contextvars import ContextVar, copy_context
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from tarjim.languages import Language, language
from tarjim.rules import Rules, rules_for

CHECKPOINT: ContextVar[Callable[[], None]] = ContextVar("checkpoint", default=lambda: None)


PROGRESS: ContextVar[Callable[[int, int], None]] = ContextVar(
    "progress", default=lambda _done, _total: None)


def progress(done: int, total: int) -> None:
    """How far a download is, in bytes, for whoever is showing the job."""
    PROGRESS.get()(done, total)


def checkpoint() -> None:
    """Between long steps: where the person's pause or cancel takes effect."""
    CHECKPOINT.get()()


Item = TypeVar("Item")
Made = TypeVar("Made")


def per_line(work: Callable[[Item], Made]) -> Callable[[Item], Made]:
    """For a pool thread working through lines: each line runs as part of the job, so a cancel
    stops the lines not yet started. Before this, a cancelled dub kept asking the paid voice
    service for every remaining line (a pool thread does not carry the job's context)."""
    job = copy_context()

    def one(item: Item) -> Made:
        def inside() -> Made:
            checkpoint()
            return work(item)

        return job.copy().run(inside)

    return one


@dataclass(frozen=True)
class Job:
    video: Path
    target: str = "ar"
    dialect: str = "saudi"
    burn: bool = True
    font: str = ""
    dub: str = ""
    out_dir: Path | None = None
    cache_dir: Path | None = None
    relisten: bool = False  # forget the kept hearing: listen to the clip again

    @property
    def language(self) -> Language:
        return language(self.target)

    @property
    def rules(self) -> Rules:
        return rules_for(self.language)

    @property
    def font_name(self) -> str:
        return self.font or self.language.font

    @property
    def cache(self) -> Path:
        """The kept work: beside the video for the command line, where a re-run finds it; in
        the folder the server gives, so a file named in chat gets nothing written beside it."""
        folder = (self.cache_dir or self.video.parent / ".tarjim") / self.video.stem
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def claim_cache(self) -> None:
        """The kept work belongs to one recording. Another file with the same name (a new take,
        or the same title in another format) starts clean."""
        facts = self.video.stat()
        stamp, now = self.cache / "source.json", json.dumps(
            [self.video.suffix, facts.st_size, int(facts.st_mtime)])
        if stamp.exists() and stamp.read_text(encoding="utf-8") != now:
            shutil.rmtree(self.cache, ignore_errors=True)
        (self.cache / "source.json").write_text(now, encoding="utf-8")

    def output(self, suffix: str) -> Path:
        folder = self.out_dir or self.video.parent
        return folder / f"{self.video.stem}.{self.target}{suffix}"
