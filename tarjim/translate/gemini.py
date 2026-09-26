from tarjim.gemini_client import GeminiClient
from tarjim.models import Cue
from tarjim.translate.clean import map_results
from tarjim.translate.prompt import build_prompt, has_speakers

SCHEMA = {"type": "array", "items": {"type": "object", "properties": {
    "id": {"type": "integer"}, "ar": {"type": "string"}}, "required": ["id", "ar"]}}
SEPARATOR = "||"


def needs_retry(cue: Cue, strict_dialogue: bool) -> bool:
    if not cue.text.strip():
        return any(ch.isalpha() for ch in cue.source)
    return strict_dialogue and cue.is_dialogue and SEPARATOR not in cue.text


class GeminiTranslator:
    def __init__(self, client: GeminiClient | None = None) -> None:
        self.client = client or GeminiClient()

    def translate(self, cues: list[Cue], audio: bytes, dialect: str) -> list[Cue]:
        self.fill(cues, audio, dialect)
        strict = has_speakers(cues)
        retry = [cue for cue in cues if needs_retry(cue, strict)]
        if retry:
            self.fill(retry, audio, dialect)
        return cues

    def fill(self, cues: list[Cue], audio: bytes, dialect: str) -> None:
        answer = self.client.ask(build_prompt(cues, dialect), audio, SCHEMA)
        results = map_results(answer if isinstance(answer, list) else [], len(cues))
        for number, cue in enumerate(cues, start=1):
            cue.text = results.get(number, cue.text)
