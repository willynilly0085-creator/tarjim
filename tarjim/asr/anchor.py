"""Utterance times corrected by the words this computer heard, before the words are aligned.

A cloud listener's times can drift. On 2026-10-29 all three Gemini passes placed the last 20
seconds of a 4-minute clip up to 9.5 seconds early; the aligner searches only near the times it
is given, so it squashed that speech before it was said and left the last 8 seconds of talk with
no subtitles. The local listener's word times come from the audio itself: each utterance moves to
where its own words were heard, when enough of them match. An utterance too short to match ("Mhm",
"Right") moves with its nearest matched neighbour, since drift builds up over a stretch.

An utterance moves by how far its first words were heard from where it puts them, not by all of
them: a listener that hears in pieces stretches a piece's last line to the piece's end, and the
words of a line that runs 131-164 s but is said in 133-147 s were all heard earlier than its
even spread puts them. Their median moved it 8 s early (2026-11-08), ahead of the turn said
before it, and the aligner, which keeps the lines' order, then showed that turn 22 s late. The
start of a stretched line is right; a drifted line's first words drift with it. Its end is
brought back to where its last words were heard, so the stretch no longer hides the speech after
it from the coverage check.

A line with no known time (one kept at its piece's edge, listen/chunks.CLAMPED) is left where it
is and out of the matching (2026-11-09): its words matched where it was said, 9 s before the
edge, and the lines between, borrowing that 9 s, were shown over the turn before them.
"""
from dataclasses import replace
from difflib import SequenceMatcher
from statistics import median

from tarjim import guards
from tarjim.asr.align import proportional
from tarjim.asr.groups import WINDOW_MARGIN
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.vote import norm
from tarjim.models import Word
from tarjim.scripts import split_words

# A line moves when its words were heard further from it than the aligner reaches by itself: the
# aligner looks WINDOW_MARGIN either side of a line and its words do not leave that. Until
# 2026-11-11 this was 2 s against the aligner's 1 s, so a line between one and two seconds late
# was moved by nobody: with every line of a made-up clip 2 s late, the lines measured at 1.9 s
# stayed late (en_panel_noise 11 words more than 0.5 s off, en_debate_overlap 6 more than 1.5 s).
DRIFT = WINDOW_MARGIN
SHARE = 0.5  # of an utterance's words, heard in the same order by the local listener
LEAST = 2
RUN = 2  # matched words must come in runs: a lone "okay" can match the wrong one
FIRST = 3  # matched words at an utterance's start that say how far it drifted
REACH = 15.0  # a short utterance follows a matched neighbour this close
EDGE = 0.5  # seconds kept after the last word heard
TAIL = 0.6  # seconds kept for each word after it that the local listener did not match
UNKNOWN = 0.0  # the prior of a line whose time is not known (listen/chunks.CLAMPED)

Match = tuple[float, float, int]  # how far a word moved, where it was heard to end, its place


def shifts(utterances: list[Utterance], heard: list[Word]) -> dict[int, list[Match]]:
    mine = [(k, i, w) for k, u in enumerate(utterances) for i, w in enumerate(proportional(u))]
    matcher = SequenceMatcher(None, [norm(w.text) for *_, w in mine],
                              [norm(w.text) for w in heard], autojunk=False)
    found: dict[int, list[Match]] = {}
    for a, b, size in matcher.get_matching_blocks():
        for step in range(size if size >= RUN else 0):
            owner, place, word = mine[a + step]
            said = heard[b + step]
            found.setdefault(owner, []).append((said.start - word.start, said.end, place))
    return found


def own_delta(utterance: Utterance, found: list[Match]) -> float | None:
    if len(found) < max(LEAST, SHARE * len(split_words(utterance.text))):
        return None
    return median(delta for delta, *_ in found[:FIRST])  # in the utterance's word order


def heard_end(utterance: Utterance, found: list[Match]) -> float | None:
    """Where the utterance's words were heard to end, or None when too few matched."""
    if own_delta(utterance, found) is None:
        return None
    _, end, place = found[-1]
    return end + EDGE + TAIL * (len(split_words(utterance.text)) - 1 - place)


def borrowed(index: int, utterances: list[Utterance], deltas: list[float | None]) -> float:
    known = [(abs(utterances[k].start - utterances[index].start), d)
             for k, d in enumerate(deltas) if d is not None]
    near = [(gap, d) for gap, d in known if gap <= REACH]
    return min(near)[1] if near else 0.0


def moved(utterance: Utterance, delta: float, duration: float, ends: float | None) -> Utterance:
    """The utterance moved when it drifted, its end brought back to where its words end."""
    shift = delta if abs(delta) >= DRIFT else 0.0
    start = min(max(0.0, utterance.start + shift), duration)
    end = min(max(start, utterance.end + shift), duration)
    end = max(start, min(end, ends)) if ends is not None else end
    if (start, end) == (utterance.start, utterance.end):
        return utterance
    guards.fired("anchor.moved")
    return replace(utterance, start=start, end=end)  # with its piece and request (2026-11-08)


def anchor(utterances: list[Utterance], heard: list[Word], duration: float) -> list[Utterance]:
    """The lines moved to where their words were heard; one whose time is not known stays as
    it is and neither takes local words nor lends its move to a neighbour (2026-11-09)."""
    known = [u for u in utterances if u.prior > UNKNOWN]
    if not heard or not known:
        return utterances
    found = shifts(known, heard)
    deltas = [own_delta(u, found.get(k, [])) for k, u in enumerate(known)]
    placed = iter([moved(u, d if d is not None else borrowed(k, known, deltas), duration,
                         heard_end(u, found.get(k, [])))
                   for k, (u, d) in enumerate(zip(known, deltas, strict=True))])
    return [next(placed) if u.prior > UNKNOWN else u for u in utterances]
