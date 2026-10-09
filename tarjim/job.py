import json
import shutil
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path

from tarjim.languages import Language, language
from tarjim.rules import Rules, rules_for

CHECKPOINT: ContextVar[Callable[[], None]] = ContextVar("checkpoint", default=lambda: None)


def checkpoint() -> None:
    """Between long steps: where the person's pause or cancel takes effect."""
    CHECKPOINT.get()()


@dataclass(frozen=True)
class Job:
    video: Path
    target: str = "ar"
    dialect: str = "saudi"
    burn: bool = True
    font: str = ""
    dub: str = ""
    out_dir: Path | None = None

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
        folder = self.video.parent / ".tarjim" / self.video.stem
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
