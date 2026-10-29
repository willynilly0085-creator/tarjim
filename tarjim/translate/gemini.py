from collections.abc import Callable
from dataclasses import replace

from tarjim.engines.choice import Asker
from tarjim.engines.web import TimedOut
from tarjim.gemini_client import GeminiClient, QuotaExhausted
from tarjim.job import checkpoint
from tarjim.models import Cue
from tarjim.translate.clean import map_results
from tarjim.translate.prompt import Brief, build_prompt, has_speakers

SCHEMA = {"type": "array", "items": {"type": "object", "properties": {
    "id": {"type": "integer"}, "text": {"type": "string"}}, "required": ["id", "text"]}}
SEPARATOR = "||"
BATCH_SECONDS = 300.0
PAD = 1.0
BAD_REPLY = (RuntimeError, ValueError, LookupError, TypeError)
# Asking again would only wait as long once more, or meet the same used-up quota.
FINAL = (TimedOut, QuotaExhausted)

AudioSlice = Callable[[float, float], bytes]


def needs_retry(cue: Cue, strict_dialogue: bool) -> bool:
    if not cue.text.strip():
        return any(ch.isalpha() for ch in cue.source)
    return strict_dialogue and cue.is_dialogue and SEPARATOR not in cue.text


def batches(cues: list[Cue], span: float = BATCH_SECONDS, most: int = 0) -> list[list[Cue]]:
    """Five minutes of lines at a time, and no more than `most` lines when an engine is slow."""
    groups: list[list[Cue]] = []
    for cue in cues:
        last = groups[-1] if groups else []
        if last and cue.end - last[0].start <= span and (not most or len(last) < most):
            last.append(cue)
        else:
            groups.append([cue])
    return groups


class Translator:
    def __init__(self, client: Asker | None = None) -> None:
        self.client: Asker = client or GeminiClient()

    def translate(self, cues: list[Cue], audio: AudioSlice, brief: Brief) -> list[Cue]:
        most = int(getattr(self.client, "most_cues", 0) or 0)
        for batch in batches(cues, most=most):
            checkpoint()  # each part is a step: pause and cancel take effect between them
            start = max(0.0, batch[0].start - PAD)
            sound = audio(start, batch[-1].end + PAD) if self.client.hears else None
            self.fill_twice(batch, sound, replace(brief, offset=start, hears=self.client.hears))
        return cues

    def fill_twice(self, cues: list[Cue], sound: bytes | None, brief: Brief) -> None:
        """The lines that came back wrong are asked once more; if that fails, the first answer
        stays."""
        self.fill_again(cues, sound, brief)
        strict = has_speakers(cues)
        retry = [cue for cue in cues if needs_retry(cue, strict)]
        if not retry:
            return
        try:
            self.fill(retry, sound, brief)
        except BAD_REPLY:
            return

    def fill_again(self, cues: list[Cue], sound: bytes | None, brief: Brief) -> None:
        """One failed answer (a busy service, a dropped stream) costs one more ask on the same
        engine, not the whole job."""
        try:
            self.fill(cues, sound, brief)
        except FINAL:
            raise
        except BAD_REPLY:
            checkpoint()  # a cancelled job is not asked again
            self.fill(cues, sound, brief)

    def fill(self, cues: list[Cue], sound: bytes | None, brief: Brief) -> None:
        """An answer with none of the lines is a failure; lines the model left empty are not,
        since a slot that is only a sound is meant to come back empty."""
        answer = self.client.ask(build_prompt(cues, brief), sound, SCHEMA)
        items = answer if isinstance(answer, list) else []
        results = map_results(items, len(cues), arabic=brief.arabic)
        if not results:
            raise RuntimeError(f"empty translation: none of {len(cues)} lines came back")
        for number, cue in enumerate(cues, start=1):
            cue.text = results.get(number) or cue.text  # an empty answer never erases a line


GeminiTranslator = Translator
