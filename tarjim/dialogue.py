from dataclasses import dataclass, field

from tarjim.models import Cue, Word, join_words
from tarjim.rules import Rules

MAX_SPEAKERS = 2


@dataclass
class Piece:
    words: list[Word] = field(default_factory=list)
    new_speaker: bool = False

    @property
    def span(self) -> float:
        return self.words[-1].end - self.words[0].start


def merge_short(pieces: list[Piece], rules: Rules) -> list[Cue]:
    cues: list[Cue] = []
    for piece in pieces:
        if cues and should_join(cues[-1], piece, rules):
            join(cues[-1], piece)
        else:
            cues.append(new_cue(piece))
    return cues


def new_cue(piece: Piece) -> Cue:
    words = list(piece.words)
    return Cue(words[0].start, words[-1].end, words, parts=[list(words)])


def should_join(cue: Cue, piece: Piece, rules: Rules) -> bool:
    cue_span = cue.words[-1].end - cue.start
    if min(cue_span, piece.span) >= rules.min_readable:
        return False
    gap = piece.words[0].start - cue.words[-1].end
    combined = piece.words[-1].end - cue.start
    chars = len(cue.source) + len(join_words(piece.words))
    within = gap <= rules.join_gap and combined <= rules.max_duration
    return within and chars <= rules.max_source_chars and room_for(cue, piece)


def room_for(cue: Cue, piece: Piece) -> bool:
    return not piece.new_speaker or len(cue.parts) < MAX_SPEAKERS


def join(cue: Cue, piece: Piece) -> None:
    if piece.new_speaker:
        cue.parts.append(list(piece.words))
    else:
        cue.parts[-1].extend(piece.words)
    cue.words.extend(piece.words)
    cue.end = piece.words[-1].end
