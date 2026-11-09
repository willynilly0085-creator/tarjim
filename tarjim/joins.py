"""Which two subtitles may become one, and what they become: one speaker's words one part, two
speakers an exchange (moved here from fit.py on 2026-11-08, when the solver also learnt to join
a short subtitle to part of a turn, crowded.handed)."""
from dataclasses import dataclass

from tarjim.dialogue import Reply, fits_one_line, last_end, like
from tarjim.models import Cue, Word, join_words
from tarjim.rules import Rules
from tarjim.speakers import who

TOLERANCE = 1e-9

Parts = list[list[Word]]


@dataclass(frozen=True)
class Frame:
    rules: Rules
    cuts: list[float]


def joinable(first: Cue, second: Cue, frame: Frame) -> bool:
    if not (first.words and second.words) or first.text or second.text:
        return False
    if replied_after(first, second):
        return False
    rules, parts = frame.rules, joined_parts(first, second, frame)
    span = max(spoken_end(first), spoken_end(second)) - first.start
    if len(parts) > rules.max_speakers or span > rules.max_duration + TOLERANCE:
        return False
    if cut_between(first, second, frame.cuts) and span > rules.cut_dialogue_span:
        return False
    if len(parts) == 1:
        return len(join_words(parts[0])) <= rules.max_source_chars
    return all(fits_one_line(part, rules) for part in parts)


def replied_after(first: Cue, second: Cue) -> bool:
    """A reply said after the first subtitle ended is not joined back onto it: before
    2026-11-08 the join stretched that subtitle over the silence, so the reply showed seconds
    before it was said and was gone before it finished. It goes through lead_in or hold."""
    head = second.parts[0] if second.parts else second.words
    return isinstance(head, Reply) and head[0].start > spoken_end(first)


def joined_parts(first: Cue, second: Cue, frame: Frame) -> Parts:
    head, tail = first.parts or [first.words], second.parts or [second.words]
    # a reply part keeps its own line: before 2026-11-08 an unlabelled reply took the next
    # subtitle's first words, which were then shown and translated as the replier's
    replied = isinstance(head[-1], Reply) or isinstance(tail[0], Reply)
    if not replied and same_voice(head[-1], tail[0], cut_between(first, second, frame.cuts)):
        return [*head[:-1], head[-1] + tail[0], *tail[1:]]
    return [*head, *tail]


def same_voice(before: list[Word], after: list[Word], at_cut: bool) -> bool:
    """Labelled words say who speaks; without labels a shot change marks a new speaker, as the
    cue builder reads them (segment.speaker_changed)."""
    if any(word.speaker for word in before + after):
        return who(before[0].speaker) == who(after[0].speaker)
    return not at_cut


def joined(first: Cue, second: Cue, frame: Frame) -> Cue:
    parts = joined_parts(first, second, frame)
    words = [word for part in parts for word in part]
    return Cue(first.start, last_end(words), words, parts=[like(part, part) for part in parts])


def cut_between(first: Cue, second: Cue, cuts: list[float]) -> bool:
    return any(spoken_end(first) <= cut <= second.words[0].start for cut in cuts)


def spoken_end(cue: Cue) -> float:
    return last_end(cue.words) if cue.words else cue.end
