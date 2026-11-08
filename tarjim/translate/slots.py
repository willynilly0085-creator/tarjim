"""Each translated slot checked before it is kept (2026-11-08).

Before this any non-empty reply was kept as it came: a dialogue answered with three parts, or
with a part missing, showed half a line in one speaker's colour, and a slot the model dropped
stayed empty, so the speech went without a subtitle. A slot that fails is cleared, so it is asked
again and then given to the next engine (translate/rounds.py).
"""
from tarjim.models import Cue, Word, join_words

SEPARATOR = "||"
NEIGHBOURS = 3  # lines each side shown, read only, beside a slot asked again
NEAR_SECONDS = 30.0
# A sound such as Mm, Uh, Hmm or Mm-hmm: one word of a few letters, mostly the same ones. The
# prompt asks for an empty text there, so an empty answer for it is that, not a dropped line.
SOUND_LETTERS = 5
SOUND_KINDS = 3


def has_letters(text: str) -> bool:
    return any(ch.isalpha() for ch in text)


def only_a_sound(source: str) -> bool:
    letters = [ch.casefold() for ch in source if ch.isalpha()]
    one_word = len(source.split()) <= 1
    return one_word and len(letters) <= SOUND_LETTERS and len(set(letters)) <= SOUND_KINDS


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
