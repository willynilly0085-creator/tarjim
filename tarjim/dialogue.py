from bisect import bisect_right
from dataclasses import dataclass, field

from tarjim.models import Cue, Word, join_words
from tarjim.rules import Rules

MAX_SPEAKERS = 2
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
    longer than a line would wrap onto a third (2026-11-08)."""
    if not piece.new_speaker:
        return True
    parts = [*cue.parts, piece.words]
    return len(parts) <= MAX_SPEAKERS and all(fits_one_line(part, rules) for part in parts)


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
    if not cues:
        return [new_cue(Piece(list(reply)))]
    index = max(0, bisect_right([cue.start for cue in cues], reply[0].start) - 1)
    host = cues[index]
    parts = [*host.parts, reply]
    if len(parts) <= MAX_SPEAKERS and all(fits_one_line(part, rules) for part in parts):
        host.parts.append(list(reply))
        host.words.extend(reply)
        host.end = max(host.end, last_end(reply))
        return cues
    return [*cues[:index], *split_at(host, reply, rules), *cues[index + 1:]]


def split_at(host: Cue, reply: list[Word], rules: Rules) -> list[Cue]:
    """A reply with no room in its turn's subtitle (a third voice, or a part too long to share
    the screen) starts a subtitle of its own, and the turn's words after it go with it. A word
    of the turn begun while the reply is still said stays with the turn: before 2026-11-08 it
    was torn from its sentence and shown after the reply."""
    at = max(reply[0].start + EDGE, last_end(reply))
    before = [kept for part in host.parts if (kept := [w for w in part if w.start < at])]
    after = [rest for part in host.parts if (rest := [w for w in part if w.start >= at])]
    head = [list(reply)]
    if after and fits_one_line(after[0], rules):
        head.append(after.pop(0))
    return [cue_of(parts) for parts in (before, head, after) if parts]


def cue_of(parts: list[list[Word]]) -> Cue:
    words = [word for part in parts for word in part]
    return Cue(min(w.start for w in words), last_end(words), words, parts=parts)
