from collections.abc import Callable
from dataclasses import replace

from tarjim.gemini_client import GeminiClient
from tarjim.models import Cue
from tarjim.translate.clean import map_results
from tarjim.translate.prompt import Brief, build_prompt, has_speakers

SCHEMA = {"type": "array", "items": {"type": "object", "properties": {
    "id": {"type": "integer"}, "text": {"type": "string"}}, "required": ["id", "text"]}}
SEPARATOR = "||"
BATCH_SECONDS = 300.0
PAD = 1.0

AudioSlice = Callable[[float, float], bytes]


def needs_retry(cue: Cue, strict_dialogue: bool) -> bool:
    if not cue.text.strip():
        return any(ch.isalpha() for ch in cue.source)
    return strict_dialogue and cue.is_dialogue and SEPARATOR not in cue.text


def batches(cues: list[Cue], span: float = BATCH_SECONDS) -> list[list[Cue]]:
    groups: list[list[Cue]] = []
    for cue in cues:
        if groups and cue.end - groups[-1][0].start <= span:
            groups[-1].append(cue)
        else:
            groups.append([cue])
    return groups


class GeminiTranslator:
    def __init__(self, client: GeminiClient | None = None) -> None:
        self.client = client or GeminiClient()

    def translate(self, cues: list[Cue], audio: AudioSlice, brief: Brief) -> list[Cue]:
        for batch in batches(cues):
            start = max(0.0, batch[0].start - PAD)
            sound = audio(start, batch[-1].end + PAD)
            self.fill_twice(batch, sound, replace(brief, offset=start))
        return cues

    def fill_twice(self, cues: list[Cue], sound: bytes, brief: Brief) -> None:
        self.fill(cues, sound, brief)
        strict = has_speakers(cues)
        retry = [cue for cue in cues if needs_retry(cue, strict)]
        if retry:
            self.fill(retry, sound, brief)

    def fill(self, cues: list[Cue], sound: bytes, brief: Brief) -> None:
        answer = self.client.ask(build_prompt(cues, brief), sound, SCHEMA)
        items = answer if isinstance(answer, list) else []
        results = map_results(items, len(cues), arabic=brief.arabic)
        for number, cue in enumerate(cues, start=1):
            cue.text = results.get(number, cue.text)
