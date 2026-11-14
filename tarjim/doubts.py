"""What a finished job is not sure of, line by line (2026-11-14).

A subtitle owes the person three things: what was said was heard right, the translation means
what was said, and the line is on screen while it is said. Until now a job checked the shape of
its lines (lengths, overlaps, one share for the whole clip of words found where they are timed)
and showed every line with the same confidence. Each line is now asked the three, from what the
job already has in hand: no new listening, no request, the same on every computer.

- hearing: its words stand on one hearing (listen/witness.alone), a third of the line or more,
  or a name or a number among them: there a wrong word costs the meaning whatever the
  translation does. A line with nobody to ask is counted apart, never as sure.
- meaning: what can be read off the two texts (translate/faithful.py).
- timing: the line comes up or goes more than LATE from its own first or last word, one of
  those two was given a guessed time, or a third of its words are not found in the sound where
  they are timed (the clip's own floor, asr/agree.clip_baseline).

These say where to look, not what is wrong. How often a listed line is really wrong, and how
many wrong lines are not listed, has not been measured, so the job lists them quietly
(findings.py) and the rules here are a first setting, not a tuned one.
"""
import json
from dataclasses import dataclass
from pathlib import Path

from tarjim.breaks import SENTENCE_END
from tarjim.listen.witness import alone
from tarjim.models import Cue, Word
from tarjim.translate.faithful import unfaithful
from tarjim.translate.glossary import Glossary

SHARE = 3  # a line is doubted when one word in this many is
LATE = 0.5  # seconds a line may come up or go from its own first or last word
GUESSED = ("estimated", "unplaced")  # a time no listener and no letter gave (models.SOURCES)
OPENING = "\"'“‘«([¿¡-"
CLOSING = "\"'”’»)]"
KINDS = ("hearing", "meaning", "timing")


def weighty(words: list[Word], k: int) -> bool:
    """A number, or a name: a capital that opens neither the line nor a sentence, and is not
    the English "I"."""
    text = words[k].text.lstrip(OPENING)
    if any(ch.isdigit() for ch in text):
        return True
    opens = k == 0 or words[k - 1].text.rstrip(CLOSING).endswith(SENTENCE_END)
    myself = text == "I" or text[:2] in ("I'", "I’")
    return text[:1].isupper() and not opens and not myself


def hearing_of(cue: Cue) -> bool | None:
    """Whether the line stands on one hearing; None with nobody to ask."""
    told = [(k, single) for k, word in enumerate(cue.words)
            if (single := alone(word)) is not None]
    if not told:
        return None
    lone = [k for k, single in told if single]
    much = bool(lone) and len(lone) * SHARE >= len(told)
    return much or any(weighty(cue.words, k) for k in lone)


def weak(word: Word, floor: float) -> bool:
    return word.source in GUESSED or (word.score is not None and word.score < floor)


def off_the_voice(cue: Cue, floor: float) -> bool:
    """Whether the line may not be on screen while it is said."""
    words = cue.words
    if not words:
        return False
    first, last = min(words, key=lambda w: w.start), max(words, key=lambda w: w.end)
    apart = abs(cue.start - first.start) > LATE or cue.end < last.end - LATE
    guessed = first.source in GUESSED or last.source in GUESSED
    return apart or guessed or sum(weak(w, floor) for w in words) * SHARE >= len(words)


@dataclass(frozen=True)
class Doubts:
    """The numbers (from 1) of the lines doubted for each of the three."""
    lines: int = 0
    hearing: tuple[int, ...] = ()
    unheard: int = 0  # lines with nobody to ask about their hearing
    meaning: tuple[int, ...] = ()
    timing: tuple[int, ...] = ()

    def of(self, number: int) -> list[str]:
        return [kind for kind in KINDS if number in getattr(self, kind)]

    def said(self) -> str:
        return (f"report: of {self.lines} line(s), {len(self.hearing)} stand on one hearing "
                f"({self.unheard} with nobody to ask), {len(self.meaning)} translation(s) to "
                f"check, {len(self.timing)} not surely on the voice")


def found(cues: list[Cue], glossary: Glossary) -> Doubts:
    from tarjim.asr.agree import clip_baseline

    heard = [hearing_of(cue) for cue in cues]
    floor = clip_baseline([w.score for cue in cues for w in cue.words if w.score is not None])
    return Doubts(len(cues), tuple(n for n, lone in enumerate(heard, start=1) if lone),
                  sum(lone is None for lone in heard), tuple(unfaithful(cues, glossary)),
                  tuple(n for n, cue in enumerate(cues, start=1) if off_the_voice(cue, floor)))


def reviewed(path: Path, cues: list[Cue], glossary: Glossary) -> Doubts:
    """The lines kept for review beside the job's other work, each with what it is doubted
    for, and the three said once in the log."""
    doubts = found(cues, glossary)
    rows = [{"start": round(c.start, 2), "end": round(c.end, 2), "source": c.source,
             "text": c.text, "doubts": doubts.of(number)} for number, c in enumerate(cues, start=1)]
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(doubts.said(), flush=True)
    return doubts
