"""A voice that runs far past the time its speaker is seen talking has its line rewritten to the
words that voice fits and is said again (2026-11-25). Every repeat, stutter and filler stays, on
the owner's word: they make it sound spoken, not read; a rewrite that lost any of them, or more
than 40% of the words, is not used (keep.py). A line is never made longer: added words would be
words the speaker did not say, so a short voice is slowed a little instead (mix.place)."""
from collections.abc import Callable
from dataclasses import replace
from typing import NamedTuple

import numpy as np

from tarjim.dub.audio import RATE, trim
from tarjim.dub.keep import fewest, keeps, listed
from tarjim.dub.lines import Line
from tarjim.dub.script import asked
from tarjim.job import Job, checkpoint

LONGEST = 1.15
ROUNDS = 2
Speaker = Callable[[list[Line]], list[np.ndarray]]
Said = tuple[list[Line], list[np.ndarray]]


class Round(NamedTuple):
    """What every round works from: the voice, the job, and the lines as first written, which
    each rewrite is held to (keep.py) so two rounds of 60% cannot leave 36% of a line."""
    speak: Speaker
    job: Job
    first: list[Line]

RULES = """You fit lines of a dubbed video's {language}{dialect} script to the time each
speaker is seen talking. For every numbered line you get the original speech, the line the voice
said, about how many words it must become, and the words it must keep.
- Keep its meaning and everything the speaker said: every repetition, stutter and filler stays
  ("yes, yes, yes" stays three times), and every word listed to keep, as often as listed.
  Never add what the speaker did not say.
- Reach the number of words by the wording alone: shorter words and phrasings.
- Keep names and numbers as the line writes them, and put diacritics on a new word the way the
  line puts them on its own words.
- Only the words to say: no quotes, no notes, no stage directions.
"""


def seconds(wav: np.ndarray) -> float:
    """How long the voice is heard, as mix.place lays it: without the silence around it."""
    return trim(wav).size / RATE


def off(line: Line, wav: np.ndarray) -> bool:
    took = seconds(wav)
    return took > line.talk * LONGEST


def words_to_fit(first: Line, line: Line, wav: np.ndarray) -> int:
    """As many words as this voice says in the time its speaker talks, at the pace it just
    spoke; never fewer than keep.py lets the line as first written lose."""
    return max(fewest(first.text), round(len(line.text.split()) * line.talk / seconds(wav)))


def prompt(lines: list[Line], words: list[int], language: str, dialect: str) -> str:
    from tarjim.translate.glossary import current, instructions

    head = RULES.format(language=language,
                        dialect=f" ({dialect} dialect)" if language == "Arabic" and dialect else "")
    body = "\n".join(f"{n}. original: {line.source}\n   said: {line.text}\n"
                     f"   about {count} words; keep: {listed(line.text) or '-'}"
                     for n, (line, count) in enumerate(zip(lines, words, strict=True), start=1))
    return f"{head}{instructions(current(language))}\n{body}"


def rewrite(lines: list[Line], words: list[int], language: str, dialect: str) -> list[str] | None:
    return asked(prompt(lines, words, language, dialect), len(lines))


def closer(line: Line, new: np.ndarray, old: np.ndarray) -> bool:
    took = seconds(new)
    return took > 0 and abs(took - line.talk) < abs(seconds(old) - line.talk)


def spoken_again(speak: Speaker, tried: list[Line]) -> list[np.ndarray] | None:
    """The first takes stand when the voice fails now, whatever it raised; a cancel still stops
    the job, as checkpoint raises it again."""
    try:
        return speak(tried)
    except Exception:
        checkpoint()
        return None


def again(turn: Round, wrong: list[int], said: Said) -> bool:
    lines, speech = said
    texts = rewrite([lines[at] for at in wrong],
                    [words_to_fit(turn.first[at], lines[at], speech[at]) for at in wrong],
                    turn.job.language.name, turn.job.dialect)
    if texts is None:
        return False
    tried = [(at, replace(lines[at], text=text)) for at, text in zip(wrong, texts, strict=True)
             if keeps(turn.first[at].text, text)]
    takes = spoken_again(turn.speak, [line for _, line in tried]) if tried else None
    if takes is None:
        return False
    for (at, line), wav in zip(tried, takes, strict=True):
        if closer(line, wav, speech[at]):
            lines[at], speech[at] = line, wav
    return True


def refit(speak: Speaker, lines: list[Line], speech: list[np.ndarray], job: Job) -> Said:
    said = (list(lines), list(speech))
    turn = Round(speak, job, list(lines))
    for _ in range(ROUNDS):
        checkpoint()
        wrong = [at for at, (line, wav) in enumerate(zip(*said, strict=True)) if off(line, wav)]
        if not wrong or not again(turn, wrong, said):
            break
    return said
