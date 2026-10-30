from dataclasses import dataclass

from tarjim.models import Cue, Word, join_words

SEPARATOR = "||"
TAIL = 1.5


@dataclass(frozen=True)
class Line:
    start: float
    until: float
    speaker: str
    text: str
    source: str = ""
    end: float = 0.0

    @property
    def room(self) -> float:
        return self.until - self.start

    @property
    def talk(self) -> float:
        """Seconds the speaker is heard: what the voice should fill, as the speaker is seen
        talking all that time."""
        return self.end - self.start if self.end > self.start else self.room


def split_text(text: str) -> list[str]:
    return [part.strip().removeprefix("-").strip() for part in text.split(SEPARATOR)]


def pieces(cue: Cue) -> list[tuple[list[Word], str]]:
    texts = split_text(cue.text)
    if cue.is_dialogue and len(cue.parts) == len(texts):
        return list(zip(cue.parts, texts, strict=True))
    return [(cue.words, " ".join(texts))]


def lines_from(cues: list[Cue], total: float) -> list[Line]:
    spoken = [(words[0].start, words[0].speaker, text, join_words(words), words[-1].end)
              for cue in cues for words, text in pieces(cue) if words and text.strip()]
    lines = []
    for index, (start, speaker, text, source, end) in enumerate(spoken):
        following = spoken[index + 1][0] if index + 1 < len(spoken) else min(total, start + 30)
        lines.append(Line(start, max(following, start + TAIL / 3), speaker, text, source, end))
    return lines
