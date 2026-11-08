from dataclasses import dataclass, field
from typing import Any, Protocol

from tarjim.gemini_client import GeminiClient

SECONDS_PER_LETTER = 0.07  # about 14 letters a second in ordinary speech
SHORTEST = 0.3

PROMPT = """Transcribe EVERY spoken word in this audio verbatim, from the first second to the \
very last second. Include the main speakers, the interviewer or host, and every short \
question or reaction even if it is a single word ("Never?", "Really?", "Nice.", "Perfect."), \
quiet background voices and overlapping speech. Split into utterances, one per speaker turn: \
when a different person speaks, start a new utterance. Label speakers consistently as S1, S2, \
... by voice (the same person always gets the same label). Give start and end in seconds. \
Keep punctuation and sentence endings. Do not summarise, translate, correct or skip anything. \
Before answering, listen again for any short turn you may have missed. Also give the main \
spoken language as an English name (e.g. English, French)."""

SCHEMA = {"type": "object", "properties": {
    "language": {"type": "string"},
    "utterances": {"type": "array", "items": {"type": "object", "properties": {
        "start": {"type": "number"}, "end": {"type": "number"},
        "speaker": {"type": "string"}, "text": {"type": "string"}},
        "required": ["start", "end", "speaker", "text"]}}},
    "required": ["language", "utterances"]}


class Hearer(Protocol):
    def ask(self, prompt: str, audio: bytes | None, schema: dict[str, Any]) -> Any: ...


@dataclass(frozen=True)
class Utterance:
    """A line heard. Since 2026-11-08 it carries where it came from, outside equality so a copy
    is still a copy: the piece of the clip it was heard in, the request that heard it ("k0.v" the
    vote of piece 0, "k0.p1" its pass 1, "local", "words") and how far its time is trusted (1
    as heard, 0.5 read back from an mm:ss misread, 0 put at its piece's edge)."""
    start: float
    end: float
    speaker: str
    text: str
    piece: tuple[float, float] | None = field(default=None, compare=False)
    request: str = field(default="", compare=False)
    prior: float = field(default=1.0, compare=False)


def listen(audio: bytes, client: Hearer | None = None) -> tuple[str, list[Utterance]]:
    answer = (client or GeminiClient(listening=True)).ask(PROMPT, audio, SCHEMA)
    if not isinstance(answer, dict):
        raise RuntimeError("listening returned nothing readable")
    utterances = [u for row in answer.get("utterances", []) if (u := parse(row)) is not None]
    return str(answer.get("language", "")), sorted(utterances, key=lambda u: u.start)


def parse(row: Any) -> Utterance | None:
    try:
        start, end = float(row["start"]), float(row["end"])
        text = " ".join(str(row["text"]).split())
    except (KeyError, TypeError, ValueError):
        return None
    if not text or end < start:
        return None
    if end == start:  # a short reply ("Yes.") is often given one moment, not a length
        end = start + max(SHORTEST, SECONDS_PER_LETTER * len(text))
    return Utterance(start, end, str(row.get("speaker", "")), text)
