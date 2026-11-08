from dataclasses import dataclass, field

from tarjim.scripts import joined

# how a word got its time (2026-11-08): the aligner heard its letters; a listener heard it;
# spread over its line by its length; placed between the words around it; not said
SOURCES = ("aligned", "heard", "estimated", "unplaced", "unknown")


@dataclass(frozen=True)
class Word:
    text: str
    start: float
    end: float
    speaker: str = ""
    # outside equality, so two words alike in text and time are still one (2026-11-08)
    score: float | None = field(default=None, compare=False)  # the aligner's, for its letters
    source: str = field(default="unknown", compare=False)  # one of SOURCES


DIALOGUE_SEPARATOR = " || "


def join_words(words: list[Word]) -> str:
    return joined([w.text for w in words])


@dataclass
class Cue:
    start: float
    end: float
    words: list[Word] = field(default_factory=list)
    text: str = ""
    parts: list[list[Word]] = field(default_factory=list)

    @property
    def is_dialogue(self) -> bool:
        return len(self.parts) > 1

    @property
    def source(self) -> str:
        if self.is_dialogue:
            return DIALOGUE_SEPARATOR.join(f"- {join_words(p)}" for p in self.parts)
        return join_words(self.words)

    @property
    def duration(self) -> float:
        return self.end - self.start
