from dataclasses import dataclass, field

from tarjim.models import Cue, Word, join_words
from tarjim.rules import Rules

MAX_SPEAKERS = 2  # the default of rules.max_speakers, a setting since 2026-11-09
EDGE = 0.05


@dataclass
class Piece:
    words: list[Word] = field(default_factory=list)
    new_speaker: bool = False
    after_cut: bool = False

    @property
    def span(self) -> float:
        return self.words[-1].end - self.words[0].start


def merge_short(pieces: list[Piece], rules: Rules) -> list[Cue]:
    cues: list[Cue] = []
    for index, piece in enumerate(pieces):
        following = pieces[index + 1] if index + 1 < len(pieces) else None
        if cues and should_join(cues[-1], piece, rules) and not closer_ahead(
                cues[-1], piece, following, rules):
            join(cues[-1], piece)
        else:
            cues.append(new_cue(piece))
    return cues


def closer_ahead(cue: Cue, piece: Piece, following: Piece | None, rules: Rules) -> bool:
    if following is None or following.after_cut or piece.span >= rules.min_readable:
        return False
    if cue.words[-1].end - cue.start < rules.min_readable:
        return False
    behind = piece.words[0].start - cue.words[-1].end
    ahead = following.words[0].start - piece.words[-1].end
    return ahead < behind and ahead <= rules.join_gap


def new_cue(piece: Piece) -> Cue:
    words = list(piece.words)
    return Cue(words[0].start, last_end(words), words, parts=[list(words)])


def last_end(words: list[Word]) -> float:
    """Where the words stop: a long word can end after a short one said inside it."""
    return max(word.end for word in words)


def should_join(cue: Cue, piece: Piece, rules: Rules) -> bool:
    if piece.after_cut and piece.words[-1].end - cue.start > rules.cut_dialogue_span:
        return False
    cue_span = cue.words[-1].end - cue.start
    if min(cue_span, piece.span) >= rules.min_readable:
        return False
    gap = piece.words[0].start - cue.words[-1].end
    combined = piece.words[-1].end - cue.start
    chars = len(cue.source) + len(join_words(piece.words))
    within = gap <= rules.join_gap and combined <= rules.max_duration
    return within and chars <= rules.max_source_chars and room_for(cue, piece, rules)


def room_for(cue: Cue, piece: Piece, rules: Rules) -> bool:
    """A new speaker becomes a part of the exchange, and each part is drawn on one line: a part
    longer than a line would wrap onto a third (2026-11-08). The same speaker's words go on the
    exchange's last part, which must still fit its line: before 2026-11-08 they were never
    measured, and a long answer wrapped onto a third line."""
    if not piece.new_speaker:
        return not cue.is_dialogue or fits_one_line(cue.parts[-1] + piece.words, rules)
    parts = [*cue.parts, piece.words]
    return len(parts) <= rules.max_speakers and all(fits_one_line(part, rules) for part in parts)


def fits_one_line(words: list[Word], rules: Rules) -> bool:
    return len(join_words(words)) <= rules.part_chars


def join(cue: Cue, piece: Piece) -> None:
    if piece.new_speaker:
        cue.parts.append(list(piece.words))
    else:
        cue.parts[-1].extend(piece.words)
    cue.words.extend(piece.words)
    # a reply joined inside a longer word used to end the subtitle before its own words
    # (2026-11-08)
    cue.end = max(cue.end, last_end(piece.words))


def with_replies(cues: list[Cue], replies: list[list[Word]], rules: Rules) -> list[Cue]:
    """Each short reply said over a turn becomes a part of the subtitle that holds its time,
    never words mixed into the host's sentence (2026-11-08)."""
    placed = sorted(cues, key=lambda cue: cue.start)
    for reply in replies:
        placed = sorted(take_reply(placed, reply, rules), key=lambda cue: cue.start)
    return placed


def take_reply(cues: list[Cue], reply: list[Word], rules: Rules) -> list[Cue]:
    """The host is the subtitle whose time holds the reply's start, else the one its time
    overlaps most; with neither, the reply is a subtitle of its own. Before 2026-11-08 the host
    was the last subtitle begun before the reply, even one that had ended: it was stretched over
    the silence and the reply was shown seconds before it was said."""
    index = host_of(cues, reply)
    if index is None:
        return [*cues, cue_of([Reply(reply)])]
    host = cues[index]
    parts = in_time(host.parts, Reply(reply))
    if len(parts) <= rules.max_speakers and all(fits_one_line(part, rules) for part in parts):
        cues[index] = cue_of(parts)
        return cues
    if reply[0].start < host.start:  # said before the turn: nothing of it to cut away
        return [*cues, cue_of([Reply(reply)])]
    split = handed_over(host, reply, rules) or split_at(host, reply, rules)
    return [*cues[:index], *split, *cues[index + 1:]]


def handed_over(host: Cue, reply: list[Word], rules: Rules) -> list[Cue] | None:
    """A reply said over the end of its turn takes the turn over: the turn's words still said
    when it starts share an exchange with it, and the words before keep their own subtitle
    (2026-11-08). Before, the turn's subtitle ended as the reply's began, so its last words
    were never shown. A reply said inside a turn that goes on is cut out of it (split_at)."""
    if last_end(host.words) > last_end(reply) + rules.join_gap:
        return None
    at = reply[0].start + EDGE
    before = [like(part, kept) for part in host.parts if (kept := [w for w in part
                                                                     if w.end <= at])]
    during = [like(part, rest) for part in host.parts if (rest := [w for w in part
                                                                    if w.end > at])]
    parts = [*during, Reply(reply)]
    shared = len(parts) <= rules.max_speakers and all(fits_one_line(p, rules) for p in parts)
    return [cue_of(before), cue_of(parts)] if before and shared else None


def host_of(cues: list[Cue], reply: list[Word]) -> int | None:
    said = reply[0].start
    holding = [k for k, cue in enumerate(cues) if cue.words and cue.start <= said < last_end(
        cue.words)]
    if holding:
        return holding[-1]
    shared = {k: overlap(cue, reply) for k, cue in enumerate(cues) if cue.words}
    best = max(shared, key=lambda k: shared[k], default=None)
    return best if best is not None and shared[best] > 0 else None


def overlap(cue: Cue, reply: list[Word]) -> float:
    return min(last_end(cue.words), last_end(reply)) - max(cue.start, reply[0].start)


def in_time(parts: list[list[Word]], reply: list[Word]) -> list[list[Word]]:
    """A reply said before the turn begins comes first, as it is heard."""
    at = sum(1 for part in parts if part and part[0].start <= reply[0].start)
    return [*parts[:at], reply, *parts[at:]]


class Reply(list[Word]):
    """A part made of a reply said over a turn: its own line, never joined to the first words
    of the subtitle next to it (fit.joined_parts, 2026-11-08)."""


def like(part: list[Word], words: list[Word]) -> list[Word]:
    """The words as a part of the same kind: a reply part stays a reply part."""
    return Reply(words) if isinstance(part, Reply) else list(words)


def split_at(host: Cue, reply: list[Word], rules: Rules) -> list[Cue]:
    """A reply with no room in its turn's subtitle (a third voice, or a part too long to share
    the screen) starts a subtitle of its own, and the turn's words after it go with it. A word
    of the turn begun while the reply is still said stays with the turn: before 2026-11-08 it
    was torn from its sentence and shown after the reply."""
    at = max(reply[0].start + EDGE, last_end(reply))
    before = [like(part, kept) for part in host.parts if (kept := [w for w in part
                                                                     if w.start < at])]
    after = [like(part, rest) for part in host.parts if (rest := [w for w in part
                                                                   if w.start >= at])]
    head: list[list[Word]] = [Reply(reply)]
    # an exchange only when both parts fit their lines (2026-11-08: a long reply wrapped)
    if after and fits_one_line(after[0], rules) and fits_one_line(reply, rules):
        head.append(after.pop(0))
    return [cue_of(parts) for parts in (before, head, after) if parts]


def cue_of(parts: list[list[Word]]) -> Cue:
    words = [word for part in parts for word in part]
    return Cue(min(w.start for w in words), last_end(words), words, parts=parts)
