import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from tarjim.models import Word


@dataclass
class Transcript:
    language: str
    text: str
    words: list[Word] = field(default_factory=list)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Transcript":
        data = json.loads(path.read_text(encoding="utf-8"))
        words = [Word(**w) for w in data.pop("words")]
        return cls(words=words, **data)
