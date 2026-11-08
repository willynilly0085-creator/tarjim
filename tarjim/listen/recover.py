"""The hearing the audio itself agrees with most: the vote, or one of the passes.

The vote keeps a line only when two passes heard it. Cloud listeners leave things out far more
often than they make things up: on 2026-10-31 one pass heard a whole Obama speech from 1:22 to
the end, two passes stopped before it, and the vote dropped every word of it, so the subtitles
ended at 1:36 while he spoke for another 30 seconds. The words this computer heard come from the
audio, so each candidate is scored by how many of them it says, in order, less half a point for
each of its own words they do not back (so a pass that makes lines up gains nothing). The vote
stays on a tie.
"""
from difflib import SequenceMatcher

from tarjim import guards
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import sane
from tarjim.listen.vote import norm, ordered
from tarjim.models import Word
from tarjim.scripts import split_words

RUN = 2  # backed words come in runs: one common word ("the") backs nothing
UNBACKED = 0.5
KEPT = 0.5  # a vote holding less of the middle pass's words than this lost speech


def tokens(run: list[Utterance]) -> list[str]:
    return [norm(w) for u in run for w in split_words(u.text) if norm(w)]


def support(run: list[Utterance], local: list[str]) -> float:
    mine = tokens(run)
    matcher = SequenceMatcher(None, mine, local, autojunk=False)
    backed = sum(size for _a, _b, size in matcher.get_matching_blocks() if size >= RUN)
    return backed - UNBACKED * (len(mine) - backed)


def cleaned(passes: list[list[Utterance]]) -> list[list[Utterance]]:
    """Each pass without its broken lines (merge.sane), in the vote's own order so a tie falls
    the same way whatever order the passes arrived in (2026-11-08)."""
    return ordered([run for whole in passes if (run := sane(whole))])


def fuller(voted: list[Utterance], passes: list[list[Utterance]]) -> list[Utterance]:
    """With no local words to judge by: the vote, unless it kept under half of what the middle
    pass heard. Passes that each heard a whole chant, spelled three ways, share few lines (a
    Somali chant on 2026-11-08: 47, 57 and 41 lines, a vote of 12), so the middle one stands:
    not the longest, which may have made lines up, nor the shortest, which left most out."""
    runs = sorted(cleaned(passes), key=lambda run: len(tokens(run)))
    if not runs:
        return voted
    middle = runs[(len(runs) - 1) // 2]
    lost = guards.when("recover.fuller", len(tokens(voted)) < KEPT * len(tokens(middle)))
    return middle if lost else voted


def best_heard(voted: list[Utterance], passes: list[list[Utterance]],
               heard: list[Word]) -> list[Utterance]:
    local = [norm(w.text) for w in heard if norm(w.text)]
    if not passes:
        return voted
    if not local:
        return fuller(voted, passes)
    candidates = [voted, *cleaned(passes)]
    chosen = max(candidates, key=lambda run: support(run, local))  # the first wins a tie
    guards.when("recover.not_vote", chosen is not voted)
    return chosen
