from collections.abc import Callable
from dataclasses import replace

from tarjim.engines.choice import Asker
from tarjim.engines.web import TimedOut
from tarjim.gemini_client import GeminiClient, QuotaExhausted
from tarjim.job import checkpoint
from tarjim.models import Cue
from tarjim.translate.clean import map_results
from tarjim.translate.drift import fit, slid
from tarjim.translate.prompt import Brief, build_prompt, has_speakers
from tarjim.translate.slots import (
    SEPARATOR,
    accepted,
    context_for,
    has_letters,
    one_speaker,
    only_a_sound,
)

SCHEMA = {"type": "array", "items": {"type": "object", "properties": {
    "id": {"type": "integer"}, "text": {"type": "string"}}, "required": ["id", "text"]}}
BATCH_SECONDS = 300.0
PAD = 1.0
BAD_REPLY = (RuntimeError, ValueError, LookupError, TypeError)
# Asking again would only wait as long once more, or meet the same used-up quota.
FINAL = (TimedOut, QuotaExhausted)
# An engine that failed this many batches in a row (its server gone, its key refused) is asked
# no more, so the backup gets the rest (2026-11-08).
IN_A_ROW = 2

AudioSlice = Callable[[float, float], bytes]


def needs_retry(cue: Cue, strict_dialogue: bool) -> bool:
    if not cue.text.strip():
        return has_letters(cue.source)
    return strict_dialogue and cue.is_dialogue and SEPARATOR not in cue.text


def fit_of(cues: list[Cue], texts: list[str]) -> float:
    return fit([replace(cue, text=text) for cue, text in zip(cues, texts, strict=True)])


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
    def __init__(self, client: Asker | None = None, whole: list[Cue] | None = None) -> None:
        self.client: Asker = client or GeminiClient()
        # every line of the clip, when this engine fills only what another one left: the lines
        # it is asked for are shown beside their translated neighbours
        self.whole = whole
        self.sounds: set[int] = set()  # the lines (by id) answered empty as only a sound
        self.failures: list[Exception] = []  # the batches that failed twice, and why
        self.row = 0  # the batches that failed one after another, up to the last one asked

    def translate(self, cues: list[Cue], audio: AudioSlice, brief: Brief) -> list[Cue]:
        most = int(getattr(self.client, "most_cues", 0) or 0)
        for batch in batches(cues, most=most):
            checkpoint()  # each part is a step: pause and cancel take effect between them
            start = max(0.0, batch[0].start - PAD)
            sound = audio(start, batch[-1].end + PAD) if self.client.hears else None
            told = replace(brief, offset=start, hears=self.client.hears)
            if self.whole is not None:
                told = replace(told, context=context_for(self.whole, batch))
            self.batch(batch, sound, told)
            if self.row >= IN_A_ROW:
                print(f"translation: {self.row} batches failed in a row; next engine", flush=True)
                break
        return cues

    def batch(self, cues: list[Cue], sound: bytes | None, brief: Brief) -> None:
        """A batch that failed twice is noted and its lines go to the backup; the batches after
        it are still asked. Until 2026-11-08 one busy answer abandoned every later batch, so a
        single engine showed most of a long video in its source language. A used-up quota or a
        timed-out engine (FINAL) stops the engine, and so do IN_A_ROW failed batches."""
        try:
            self.fill_twice(cues, sound, brief)
        except FINAL:
            raise
        except BAD_REPLY as error:
            print(f"translation: a batch of {len(cues)} lines failed: {error}", flush=True)
            self.failures.append(error)
            self.row += 1
        else:
            self.row = 0

    def fill_twice(self, cues: list[Cue], sound: bytes | None, brief: Brief) -> None:
        """The lines that came back wrong are asked once more, alone, beside their neighbours
        (read only) and with the same sound; if that fails, the first answer stays. Since
        2026-11-08 one_speaker also runs when the engine stops while unsliding."""
        self.fill_again(cues, sound, brief)
        try:
            self.unslide(cues, sound, brief)
            strict = has_speakers(cues)
            retry = [cue for cue in cues
                     if needs_retry(cue, strict) and id(cue) not in self.sounds]
            if retry:
                self.once_more(retry, sound, replace(brief, context=context_for(self.whole or cues,
                                                                                retry)))
        finally:
            one_speaker(cues)

    def unslide(self, cues: list[Cue], sound: bytes | None, brief: Brief) -> None:
        """An answer that slid down the slots (drift.py) is asked for once more, told so; the
        better fitting of the two answers stays."""
        if not slid(cues):
            return
        print(f"translation slid down the slots ({len(cues)} lines); asking again", flush=True)
        first = [cue.text for cue in cues]
        checkpoint()
        self.once_more(cues, sound, replace(brief, slid=True))
        if fit(cues) < fit_of(cues, first):
            for cue, text in zip(cues, first, strict=True):
                cue.text = text

    def once_more(self, cues: list[Cue], sound: bytes | None, brief: Brief) -> None:
        """A second ask that fails keeps the first answer. A used-up quota or a timed-out engine
        is not swallowed here (2026-11-08): it stops the engine and is reported, where before the
        lines were shown as said with no reason and a timed-out engine was waited on again."""
        try:
            self.fill(cues, sound, brief)
        except FINAL:
            raise
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
        """An answer with none of the lines is a failure; a line it left out or got wrong is
        not, and is asked again (fill_twice)."""
        answer = self.client.ask(build_prompt(cues, brief), sound, SCHEMA)
        items = answer if isinstance(answer, list) else []
        results = map_results(items, len(cues), brief.arabic, brief.manner)
        if not results:
            raise RuntimeError(f"empty translation: none of {len(cues)} lines came back")
        for number, cue in enumerate(cues, start=1):
            self.keep(cue, results.get(number))

    def keep(self, cue: Cue, text: str | None) -> None:
        """A slot that fails its check (slots.accepted) never erases a line already there. An
        empty answer is kept only for a sound, which the prompt asks to leave empty; since
        2026-11-08 an empty answer for words is a failure, so speech is not left unsubtitled."""
        if text is None:
            return
        if not text.strip() and only_a_sound(cue.source):
            self.sounds.add(id(cue))
            return
        cue.text = accepted(cue, text) or cue.text


GeminiTranslator = Translator
