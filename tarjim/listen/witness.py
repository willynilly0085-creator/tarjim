"""Who else wrote each word that is shown (2026-11-14).

A word carried how it got its time (its source and its score) and nothing of how sure its text
is. The vote keeps a line whose words two passes wrote, with the words only its own pass wrote;
when the passes agree on how much was said the fullest one stands whole (merge.settled), and the
pass the audio backs most can replace the vote (recover.best_heard). So a name one pass of three
wrote was shown, and translated, exactly like a word every listener agreed on, and nothing told
the person which lines to look at.

Each final word now carries how many hearings of the chosen listener wrote it near there
(`backed`: each pass, and a stretch asked about again) and whether the listener on this computer
did (`local`); both are kept with the transcript. A word stands on one hearing (`alone`) when
fewer than two of them wrote it: one pass of three, a line only the listener on this computer
filled in, a line only asking again brought.

A witness wrote a word when it has the same word (vote.norm) in the same order within NEAR
seconds: the passes carry their lines' own times and the local words may be timed seconds off
(asr/confirm.py measured up to 11 s), while the final words are timed on the sound. The words are
matched a stretch at a time, so an hour of speech costs what its minutes cost.

Nobody else to ask leaves None: a clip heard in one pass with no listener on this computer (the
local listener is no witness to its own hearing), and a mark with no letters.
"""
from dataclasses import replace
from difflib import SequenceMatcher

from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.vote import norm
from tarjim.models import Word
from tarjim.scripts import split_words

NEAR = 12.0  # seconds a witness's time may be from the word's and still be the same saying
STRETCH = 200  # words matched at once
TWO = 2  # hearings that wrote a word before it stands on more than one

Said = tuple[str, float, float]  # a word a witness wrote, and when: its line's time, or its own


def of_lines(run: list[Utterance]) -> list[Said]:
    return [(token, u.start, u.end) for u in sorted(run, key=lambda u: u.start)
            for w in split_words(u.text) if (token := norm(w))]


def of_words(words: list[Word]) -> list[Said]:
    return [(token, w.start, w.end) for w in sorted(words, key=lambda w: w.start)
            if (token := norm(w.text))]


def near(word: Word, said: Said) -> bool:
    return said[1] - NEAR <= word.start <= said[2] + NEAR


def stretch_said(part: list[Word], witness: list[Said]) -> list[bool]:
    """One stretch of words in time order: which of them the witness wrote near there."""
    low, high = part[0].start - NEAR, max(w.end for w in part) + NEAR
    theirs = [said for said in witness if said[2] >= low and said[1] <= high]
    mine = [norm(w.text) for w in part]
    found = [False] * len(part)
    matcher = SequenceMatcher(None, mine, [said[0] for said in theirs], autojunk=False)
    for block in matcher.get_matching_blocks():
        for step in range(block.size):
            k = block.a + step
            found[k] = bool(mine[k]) and near(part[k], theirs[block.b + step])
    return found


def says(words: list[Word], witness: list[Said]) -> list[bool]:
    """Each word, in the order given: whether the witness wrote it near there."""
    order = sorted(range(len(words)), key=lambda k: words[k].start)
    found = [False] * len(words)
    for first in range(0, len(order), STRETCH):
        part = order[first:first + STRETCH]
        for k, said in zip(part, stretch_said([words[k] for k in part], witness), strict=True):
            found[k] = said
    return found


def witnessed(words: list[Word], passes: list[list[Utterance]], local: list[Word],
              again: list[Utterance] | None = None) -> list[Word]:
    """The words with who wrote them: `passes` as the clip was heard, `again` the lines a
    stretch asked about again brought, `local` the words of the listener on this computer (none
    when it was the listener itself, or did not run)."""
    runs = [of_lines(run) for run in passes if run]
    if len(runs) + bool(local) < TWO:
        return [replace(w, backed=None, local=None) for w in words]
    votes = [says(words, run) for run in [*runs, of_lines(again or [])]]
    here = says(words, of_words(local)) if local else None
    return [seen(w, sum(vote[k] for vote in votes), None if here is None else here[k])
            for k, w in enumerate(words)]


def seen(word: Word, backed: int, here: bool | None) -> Word:
    """The word with its witnesses; a mark with no letters has nothing to hear."""
    told = bool(norm(word.text))
    return replace(word, backed=backed if told else None, local=here if told else None)


def alone(word: Word) -> bool | None:
    """Whether the word stands on one hearing: fewer than two of the chosen listener's
    hearings and the listener on this computer wrote it. None with nobody else to ask."""
    if word.backed is None and word.local is None:
        return None
    return (word.backed or 0) + bool(word.local) < TWO
