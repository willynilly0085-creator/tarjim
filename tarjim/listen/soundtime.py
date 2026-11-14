"""A line's time taken from the sound when the listener's own is wrong (2026-11-14).

A cloud listener writes what was said far better than when. The same eight lines of a clean
90-second Arabic clip came back from three passes on three clocks: one right to its last second,
one ending at 73 s and one at 64 s. The vote takes the middle time of each line, so the lines
were put on the 73-second clock, up to 13 s before they are said. The aligner looks one second
either side of where a line is put (asr/groups.WINDOW_MARGIN), so it pressed three sentences
into the time of one; the coverage check then found speech with no words where they really are
and asked again, and the same sentences were written twice. A third of the words were wrong or
doubled and 58 of 133 sat outside their own sentence. Until now only the words of the listener
on this computer corrected a line's time (asr/anchor.py): it reads Arabic poorly, and a
computer too weak to run it had no correction at all.

The sound itself says where a line is. The lines of one request are searched once more in that
request's whole stretch of sound, bound by nothing but their order (the letters the aligner
already heard in the clip, asr/letters.py: no new listening). A line moves to where that search
hears it when it is heard there (agree.FOUND), further off than the aligner reaches by itself,
and either the search followed the whole request well (FOLLOWED) and the line is heard there no
worse than where it stood, or it is heard there clearly better (BETTER). A line with too few
letters to tell alone (LETTERS) goes with the line before it. A line the search finds within
the aligner's reach of where it stands never moves, so a clip whose times were right is left
exactly as it was.

Lines the listener was asked about again (a few seconds of sound, their times fresh) and lines
made of the local listener's words are not searched. A stretch too long to search at once
(CELLS) is left as it is, and said.
"""
from collections.abc import Callable
from dataclasses import dataclass, replace
from functools import cache
from itertools import groupby
from typing import Any

import numpy as np

from tarjim import guards
from tarjim.asr.agree import FOUND
from tarjim.asr.ctc import FRAME, token_spans
from tarjim.asr.groups import WINDOW_MARGIN
from tarjim.asr.numbers import said
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.placed import Placed
from tarjim.scripts import split_words

BETTER = 0.2  # how much better a line must be heard elsewhere than where it stands
LETTERS = 8  # letters a line needs to be told alone (as asr/confirm.LETTERS)
FOLLOWED = 0.6  # how well a request's letters are heard on the whole when its search is trusted
CELLS = 150_000_000  # frames times letters searched at once: about 300 MB while it runs
PAD = 2.0  # seconds of sound either side of a request's stretch (as asr/align.PAD)
APART = 1.0  # seconds from the rest of the line that put a letter or two astray
STRAY = 2  # letters apart from the rest at a line's end that are not counted its own

Found = tuple[float, float, float]  # where a line's letters are heard, and how well


@dataclass(frozen=True)
class Ears:
    logp: np.ndarray  # the clip's letters, frame by frame
    tokens: Callable[[str], list[int]]
    language: str

    def letters(self, line: Utterance) -> list[int]:
        words = split_words(line.text)
        return [token for sound in said(words, self.language) for token in self.tokens(sound)]

    def frames(self, low: float, high: float) -> tuple[int, int]:
        return max(0, int(low / FRAME)), min(len(self.logp), int(high / FRAME) + 1)

    def here(self, line: Utterance) -> float:
        """How well the line is heard where it stands, as far as the aligner reaches."""
        low, high = self.frames(line.start - WINDOW_MARGIN, line.end + WINDOW_MARGIN)
        spans = token_spans(self.logp[low:high], self.letters(line))
        return float(np.mean([score for *_, score in spans])) if spans else 0.0

    def freely(self, lines: list[Utterance]) -> list[Found | None]:
        """Each line where one search of the lines' whole stretch hears it, in their order."""
        owners = [k for k, line in enumerate(lines) for _ in self.letters(line)]
        letters = [token for line in lines for token in self.letters(line)]
        span = min(u.piece[0] for u in lines if u.piece), max(u.piece[1] for u in lines if u.piece)
        low, high = self.frames(span[0] - PAD, span[1] + PAD)
        if (high - low) * (2 * len(letters) + 1) > CELLS:
            print(f"timing: {span[1] - span[0]:.0f} s heard in one request is too long to "
                  "search for its lines at once; their times stay the listener's", flush=True)
            return [None] * len(lines)
        spans = token_spans(self.logp[low:high], letters) or []
        return [heard([s for owner, s in zip(owners, spans, strict=False) if owner == k], low)
                for k in range(len(lines))]


def heard(spans: list[Found], low: int) -> Found | None:
    """A line's letters as one stretch, less a letter or two astray at either end: one search
    over a whole request lets a line's first letter sit on a like sound in speech no line says,
    seconds before the rest of it (seen in the tests: "e" of a line said at 55 s taken at
    30 s). A pause inside the line parts nothing: its words after the pause are its own (a
    reader who stopped for a second mid-sentence left the rest of it with no line, and it was
    filled in a second time, 2026-11-14)."""
    runs: list[list[Found]] = []
    for span in spans:
        if runs and span[0] - runs[-1][-1][1] <= APART:
            runs[-1].append(span)
        else:
            runs.append([span])
    while len(runs) > 1 and len(runs[0]) <= STRAY:
        runs = runs[1:]
    while len(runs) > 1 and len(runs[-1]) <= STRAY:
        runs = runs[:-1]
    body = [span for run in runs for span in run]
    if not body:
        return None
    return (body[0][0] + low * FRAME, body[-1][1] + low * FRAME,
            float(np.mean([score for *_, score in body])))


def request(line: Utterance) -> str:
    """The request that heard the line ("k3" for the vote or a pass of piece 3); "" for one
    asked about again or made of the local listener's words, which are not searched."""
    name = line.request.split(".")[0]
    return name if name[:1] == "k" and line.piece is not None else ""


def out_of_reach(line: Utterance, found: Found) -> bool:
    return max(abs(found[0] - line.start), abs(found[1] - line.end)) > WINDOW_MARGIN


def followed(ears: Ears, lines: list[Utterance], frees: list[Found | None]) -> bool:
    """Whether the free search followed the request's text through the sound: its letters are
    heard well on the whole (FOLLOWED). Then where it puts a line is pinned by the lines around
    it, and the line need not be heard better there than where it stood. On the clip this was
    made for, the last line scored 0.46 where the listener put it, on another sentence, and
    0.49 where it is said, between seven lines found at 0.67 to 0.96."""
    weighed = [(len(ears.letters(line)), found[2]) for line, found in zip(lines, frees, strict=True)
               if found is not None]
    letters = sum(count for count, _score in weighed)
    return bool(letters) and sum(count * score for count, score in weighed) >= FOLLOWED * letters


def moves(ears: Ears, line: Utterance, found: Found | None, trust: tuple[bool, bool]) -> bool:
    """Whether the line goes where the free search heard it. `trust`: whether the search
    followed its request, and whether the line before this one moved (one too short to tell
    alone goes with it)."""
    whole, before = trust
    if found is None or not out_of_reach(line, found):
        return False
    if len(ears.letters(line)) < LETTERS:
        return before
    return found[2] >= FOUND and found[2] >= ears.here(line) + (0.0 if whole else BETTER)


def stretch(ears: Ears, lines: list[Utterance]) -> list[Utterance]:
    """One request's lines, each where the sound holds it."""
    frees = ears.freely(lines)
    whole, placed, moved = followed(ears, lines, frees), [], False
    for line, found in zip(lines, frees, strict=True):
        moved = moves(ears, line, found, (whole, moved))
        placed.append(replace(line, start=found[0], end=found[1]) if moved and found else line)
    return placed


def on_the_sound(lines: list[Utterance], ears: Ears) -> list[Utterance]:
    """The lines, those not heard where the listener put them moved to where they are heard."""
    ordered = sorted(lines, key=lambda u: (request(u), u.start))
    placed = [line for name, group in groupby(ordered, key=request)
              for line in (stretch(ears, list(group)) if name else group)]
    shifts = [abs(new.start - old.start) for old, new in zip(ordered, placed, strict=True)
              if new.start != old.start or new.end != old.end]
    guards.fired("sound.moved", len(shifts))
    if shifts:
        print(f"timing: {len(shifts)} line(s) were not heard where the listener put them and "
              f"are heard elsewhere in the sound: moved there, by up to {max(shifts):.1f} s",
              flush=True)
    return sorted(placed, key=lambda u: u.start)


def ears_for(wav: Any, language: str) -> Ears | None:
    """The clip's letters as the aligner heard them for the speech map; None when no aligner
    is in memory (it is never loaded for this alone) or it is a stand-in with no ears."""
    from tarjim.asr import align
    from tarjim.memory import heavy

    info = getattr(align.shared_aligner, "cache_info", None)
    if info is not None and not info().currsize:
        return None
    with heavy():
        engine = align.shared_aligner()
        emitter = getattr(engine, "emitter", None)
        if emitter is None:
            return None
        return Ears(emitter.emissions(wav), cache(engine.tokens), language)


def where_heard(found: Placed, wav: Any, language: str) -> Placed:
    """The lines to be timed, at the listener's own times and at those the local words back,
    each moved to where the sound holds it."""
    ears = ears_for(wav, language)
    if ears is None:
        return found
    own = on_the_sound(found.own, ears)
    moved = own if found.moved == found.own else on_the_sound(found.moved, ears)
    return replace(found, own=own, moved=moved)
