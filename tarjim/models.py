from dataclasses import dataclass, field


@dataclass(frozen=True)
class Word:
    text: str
    start: float
    end: float
    speaker: str = ""


DIALOGUE_SEPARATOR = " || "


def join_words(words: list[Word]) -> str:
    return " ".join(w.text for w in words).strip()


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
