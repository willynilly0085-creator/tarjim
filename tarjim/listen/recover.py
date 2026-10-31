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

from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import sane
from tarjim.listen.vote import norm
from tarjim.models import Word
from tarjim.scripts import split_words

RUN = 2  # backed words come in runs: one common word ("the") backs nothing
UNBACKED = 0.5


def tokens(run: list[Utterance]) -> list[str]:
    return [norm(w) for u in run for w in split_words(u.text) if norm(w)]


def support(run: list[Utterance], local: list[str]) -> float:
    mine = tokens(run)
    matcher = SequenceMatcher(None, mine, local, autojunk=False)
    backed = sum(size for _a, _b, size in matcher.get_matching_blocks() if size >= RUN)
    return backed - UNBACKED * (len(mine) - backed)


def best_heard(voted: list[Utterance], passes: list[list[Utterance]],
               heard: list[Word]) -> list[Utterance]:
    local = [norm(w.text) for w in heard if norm(w.text)]
    if not local or not passes:
        return voted
    candidates = [voted, *[run for run in passes if run and sane(run)]]
    return max(candidates, key=lambda run: support(run, local))  # the first wins a tie
