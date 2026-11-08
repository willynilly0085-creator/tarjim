"""Each translated slot checked before it is kept (2026-11-08).

Before this any non-empty reply was kept as it came: a dialogue answered with three parts, or
with a part missing, showed half a line in one speaker's colour, and a slot the model dropped
stayed empty, so the speech went without a subtitle. A slot that fails is cleared, so it is asked
again and then given to the next engine (translate/rounds.py).
"""
import unicodedata

from tarjim.models import Cue, Word, join_words

SEPARATOR = "||"
NEIGHBOURS = 3  # lines each side shown, read only, beside a slot asked again
NEAR_SECONDS = 30.0
# The sounds the prompt asks to leave empty, written with each run of one letter once (Mmm is
# Mm, Mm-hmm is mhm). Until 2026-11-08 any one word of up to 5 letters, 3 of them different, was
# taken for a sound, which also took No, Yes, Hi, نعم, Да and most short lines of Chinese or
# Japanese; an empty answer for those left speech with no subtitle and no note. Only these may be
# left empty; any other line with letters answered empty is a failure and goes to the backup.
# A word that is also a sound in some language (er is German for he) is left out.
FILLERS = frozenset({
    "m", "hm", "mhm", "uh", "um", "uhm", "uhuh", "ah", "eh", "ehm", "erm", "oh", "huh",
    "euh", "ha", "haha", "hahaha",
    "اه", "آه", "اوه", "م", "ه",  # Arabic and Urdu: آه, ممم, ههه (not ام, which can be أم)
    "м", "хм", "э", "эм",  # Cyrillic
    "हम्म", "उम्म",  # Devanagari
    "嗯", "呃", "啊", "哦", "唔", "哈",  # Chinese
    "えー", "あー", "うーん", "んー", "ん",  # Japanese
    "음", "흠",  # Korean
})


def has_letters(text: str) -> bool:
    return any(ch.isalpha() for ch in text)


def only_a_sound(source: str) -> bool:
    """A filler, in any script, however long it is drawn out; never decided by length."""
    kept = [ch.casefold() for ch in source if ch.isalpha() or unicodedata.category(ch)[0] == "M"]
    drawn = "".join(ch for n, ch in enumerate(kept) if not n or ch != kept[n - 1])
    return drawn in FILLERS


def speakers_of(cue: Cue) -> list[list[Word]]:
    return cue.parts if cue.is_dialogue else [cue.words]


def accepted(cue: Cue, text: str) -> str:
    """The answer for one slot, or "" when it fails. One sentence for an exchange is the model
    saying it is one person (prompt.GUESSED_SPEAKERS), so it is kept and the parts merged later
    (one_speaker); a line of one speaker split in two is joined back. Any other count of parts,
    or a part left empty where words were said, fails."""
    parts = [part.strip() for part in text.split(SEPARATOR)]
    wanted = speakers_of(cue)
    if not text.strip() or len(parts) == 1:
        return text.strip()
    if len(wanted) == 1:
        return " ".join(part for part in parts if part)
    if len(parts) != len(wanted):
        return ""
    said = [has_letters(join_words(words)) for words in wanted]
    return "" if any(is_said and not part for part, is_said in zip(parts, said, strict=True)) \
        else text.strip()


def one_speaker(cues: list[Cue]) -> None:
    """An exchange translated as one sentence is one speaker's line: one colour, shown at once."""
    for cue in cues:
        if cue.is_dialogue and cue.text.strip() and SEPARATOR not in cue.text:
            cue.parts = [list(cue.words)]


def as_said(cue: Cue) -> str:
    """The last resort for a line no engine translated: the words as they were said."""
    return f" {SEPARATOR} ".join(join_words(words) for words in speakers_of(cue))


def context_for(whole: list[Cue], asked: list[Cue]) -> tuple[Cue, ...]:
    """The translated lines next to the asked ones, in order, for meaning only: a line long
    before or after is another conversation."""
    chosen = {id(cue) for cue in asked}
    near: set[int] = set()
    for place, cue in enumerate(whole):
        if id(cue) in chosen:
            near |= {n for n in range(max(0, place - NEIGHBOURS), place + NEIGHBOURS + 1)
                     if n < len(whole) and abs(whole[n].start - cue.start) <= NEAR_SECONDS}
    return tuple(whole[n] for n in sorted(near)
                 if id(whole[n]) not in chosen and whole[n].text.strip())
