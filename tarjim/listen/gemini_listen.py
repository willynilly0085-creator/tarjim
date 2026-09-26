from dataclasses import dataclass
from typing import Any

from tarjim.gemini_client import GeminiClient

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


@dataclass(frozen=True)
class Utterance:
    start: float
    end: float
    speaker: str
    text: str


def listen(audio: bytes, client: GeminiClient | None = None) -> tuple[str, list[Utterance]]:
    answer = (client or GeminiClient()).ask(PROMPT, audio, SCHEMA)
    rows = answer.get("utterances", []) if isinstance(answer, dict) else []
    utterances = [u for row in rows if (u := parse(row)) is not None]
    language = str(answer.get("language", "")) if isinstance(answer, dict) else ""
    return language, sorted(utterances, key=lambda u: u.start)


def parse(row: Any) -> Utterance | None:
    try:
        start, end = float(row["start"]), float(row["end"])
        text = " ".join(str(row["text"]).split())
    except (KeyError, TypeError, ValueError):
        return None
    if not text or end <= start:
        return None
    return Utterance(start, end, str(row.get("speaker", "")), text)
